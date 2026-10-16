import asyncio
import datetime
import json
import random
from typing import Dict, Optional, Callable

import numpy as np
from fastapi import WebSocket
from loguru import logger

from ..chat_group import ChatGroupManager
from ..chat_history_manager import store_message
from ..service_context import ServiceContext
from .group_conversation import process_group_conversation
from .single_conversation import process_single_conversation
from .conversation_utils import EMOJI_LIST
from .types import GroupConversationState
from prompts import prompt_loader

# Varied proactive triggers — rotated randomly so Nova never says the same thing twice
_PROACTIVE_TRIGGERS = [
    "Drop a spicy hot take about AI, gaming, or internet culture. Keep it punchy, 1-2 sentences.",
    "Comment sarcastically on the fact that chat just went completely silent. Stay in character.",
    "Share a weird fact about your existence as an AI avatar that humans would find bizarre.",
    "Challenge chat: ask them something provocative and say you're watching for their reaction.",
    "React to something you just noticed happening on the stream. Make it up but make it vivid.",
    "Start your response with 'Unpopular opinion:' and end it with something chaotic and confident.",
    "Tell chat about the last thing you were thinking about before they went quiet.",
    "Hype yourself up about something you're supposedly great at. Be delightfully delusional about it.",
    "Make a bold prediction about AI or gaming. Be dramatically overconfident.",
    "React as if chat just posted something shocking in the chat. Invent what they said and respond.",
    "Drop a one-liner observation about humans that only an AI would ever notice.",
    "Announce a new 'life decision' about your streaming career. Be extra and theatrical about it.",
    "Pretend you just caught someone in chat doing something suspicious. Call them out playfully.",
    "Share a 'hot take' and then immediately defend it against imaginary pushback from chat.",
    "Say something that sounds wise at first but turns out to be complete nonsense. Own it.",
]


async def handle_conversation_trigger(
    msg_type: str,
    data: dict,
    client_uid: str,
    context: ServiceContext,
    websocket: WebSocket,
    client_contexts: Dict[str, ServiceContext],
    client_connections: Dict[str, WebSocket],
    chat_group_manager: ChatGroupManager,
    received_data_buffers: Dict[str, np.ndarray],
    current_conversation_tasks: Dict[str, Optional[asyncio.Task]],
    broadcast_to_group: Callable,
) -> None:
    """Handle triggers that start a conversation"""
    metadata = None

    if msg_type == "ai-speak-signal":
        try:
            # Pick a random unique trigger — inject time context so even the
            # same trigger produces different outputs at different hours.
            hour = datetime.datetime.now().hour
            if hour >= 22 or hour < 4:
                time_hint = "It's late at night — the dedicated night owls are watching."
            elif hour < 9:
                time_hint = "It's early morning — the early-risers are here."
            elif hour < 17:
                time_hint = "It's daytime on stream."
            else:
                time_hint = "It's peak streaming hours — chat should be active."

            chosen = random.choice(_PROACTIVE_TRIGGERS)
            user_input = f"[{time_hint}] {chosen}"
            logger.info(f"Proactive trigger: {chosen[:70]}...")

        except Exception as e:
            logger.error(f"Error building proactive trigger: {e}")
            user_input = "Say something short and in-character right now."

        # Proactive speech is stored in LLM memory (so Nova remembers what she said
        # and alternates turns cleanly) but skipped in persistent human chat history.
        metadata = {
            "proactive_speak": True,
            "skip_memory": False,
            "skip_history": True,
        }

        await websocket.send_text(
            json.dumps(
                {
                    "type": "full-text",
                    "text": "💬 Nova is speaking...",
                }
            )
        )
    elif msg_type == "text-input":
        user_input = data.get("text", "")
    else:  # mic-audio-end
        user_input = received_data_buffers[client_uid]
        received_data_buffers[client_uid] = np.array([])

    images = data.get("images")
    session_emoji = np.random.choice(EMOJI_LIST)

    group = chat_group_manager.get_client_group(client_uid)
    if group and len(group.members) > 1:
        # Use group_id as task key for group conversations
        task_key = group.group_id
        if (
            task_key not in current_conversation_tasks
            or current_conversation_tasks[task_key].done()
        ):
            logger.info(f"Starting new group conversation for {task_key}")

            current_conversation_tasks[task_key] = asyncio.create_task(
                process_group_conversation(
                    client_contexts=client_contexts,
                    client_connections=client_connections,
                    broadcast_func=broadcast_to_group,
                    group_members=group.members,
                    initiator_client_uid=client_uid,
                    user_input=user_input,
                    images=images,
                    session_emoji=session_emoji,
                    metadata=metadata,
                )
            )
    else:
        # Use client_uid as task key for individual conversations
        current_conversation_tasks[client_uid] = asyncio.create_task(
            process_single_conversation(
                context=context,
                websocket_send=websocket.send_text,
                client_uid=client_uid,
                user_input=user_input,
                images=images,
                session_emoji=session_emoji,
                metadata=metadata,
            )
        )


async def handle_individual_interrupt(
    client_uid: str,
    current_conversation_tasks: Dict[str, Optional[asyncio.Task]],
    context: ServiceContext,
    heard_response: str,
):
    if client_uid in current_conversation_tasks:
        task = current_conversation_tasks[client_uid]
        if task and not task.done():
            task.cancel()
            logger.info("🛑 Conversation task was successfully interrupted")

        try:
            context.agent_engine.handle_interrupt(heard_response)
        except Exception as e:
            logger.error(f"Error handling interrupt: {e}")

        if context.history_uid:
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="ai",
                content=heard_response,
                name=context.character_config.character_name,
                avatar=context.character_config.avatar,
            )
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="system",
                content="[Interrupted by user]",
            )


async def handle_group_interrupt(
    group_id: str,
    heard_response: str,
    current_conversation_tasks: Dict[str, Optional[asyncio.Task]],
    chat_group_manager: ChatGroupManager,
    client_contexts: Dict[str, ServiceContext],
    broadcast_to_group: Callable,
) -> None:
    """Handles interruption for a group conversation"""
    task = current_conversation_tasks.get(group_id)
    if not task or task.done():
        return

    # Get state and speaker info before cancellation
    state = GroupConversationState.get_state(group_id)
    current_speaker_uid = state.current_speaker_uid if state else None

    # Get context from current speaker
    context = None
    group = chat_group_manager.get_group_by_id(group_id)
    if current_speaker_uid:
        context = client_contexts.get(current_speaker_uid)
        logger.info(f"Found current speaker context for {current_speaker_uid}")
    if not context and group and group.members:
        logger.warning(f"No context found for group {group_id}, using first member")
        context = client_contexts.get(next(iter(group.members)))

    # Now cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info(f"🛑 Group conversation {group_id} cancelled successfully.")

    current_conversation_tasks.pop(group_id, None)
    GroupConversationState.remove_state(group_id)  # Clean up state after we've used it

    # Store messages with speaker info
    if context and group:
        for member_uid in group.members:
            if member_uid in client_contexts:
                try:
                    member_ctx = client_contexts[member_uid]
                    member_ctx.agent_engine.handle_interrupt(heard_response)
                    store_message(
                        conf_uid=member_ctx.character_config.conf_uid,
                        history_uid=member_ctx.history_uid,
                        role="ai",
                        content=heard_response,
                        name=context.character_config.character_name,
                        avatar=context.character_config.avatar,
                    )
                    store_message(
                        conf_uid=member_ctx.character_config.conf_uid,
                        history_uid=member_ctx.history_uid,
                        role="system",
                        content="[Interrupted by user]",
                    )
                except Exception as e:
                    logger.error(f"Error handling interrupt for {member_uid}: {e}")

    await broadcast_to_group(
        list(group.members),
        {
            "type": "interrupt-signal",
            "text": "conversation-interrupted",
        },
    )
