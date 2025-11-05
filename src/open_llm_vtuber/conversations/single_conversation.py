from typing import Union, List, Dict, Any, Optional
import asyncio
import json
import random
from loguru import logger
import numpy as np

from .conversation_utils import (
    create_batch_input,
    process_agent_output,
    send_conversation_start_signals,
    process_user_input,
    finalize_conversation_turn,
    cleanup_conversation,
    EMOJI_LIST,
)
from .types import WebSocketSend
from .tts_manager import TTSTaskManager
from ..chat_history_manager import store_message
from ..service_context import ServiceContext

# Import necessary types from agent outputs
from ..agent.output_types import SentenceOutput, AudioOutput


async def process_single_conversation(
    context: ServiceContext,
    websocket_send: WebSocketSend,
    client_uid: str,
    user_input: Union[str, np.ndarray],
    images: Optional[List[Dict[str, Any]]] = None,
    session_emoji: str = np.random.choice(EMOJI_LIST),
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Process a single-user conversation turn

    Args:
        context: Service context containing all configurations and engines
        websocket_send: WebSocket send function
        client_uid: Client unique identifier
        user_input: Text or audio input from user
        images: Optional list of image data
        session_emoji: Emoji identifier for the conversation
        metadata: Optional metadata for special processing flags

    Returns:
        str: Complete response text
    """
    # Create TTSTaskManager for this conversation
    tts_manager = TTSTaskManager()
    full_response = ""  # Initialize full_response here

    try:
        # Send initial signals
        await send_conversation_start_signals(websocket_send)
        logger.info(f"New Conversation Chain {session_emoji} started!")

        # Process user input
        input_text = await process_user_input(
            user_input, context.asr_engine, websocket_send
        )
        
        # Check for rock-paper-scissors game
        if "猜拳" in input_text and context.game_state == "idle":
            logger.info("Starting rock-paper-scissors game")
            context.game_state = "playing"
            
            # Ask AI to choose a move
            game_prompt = "我们来玩猜拳游戏吧！请你在剪刀、石头、布中选择一个，只需要回答选择的内容，不要添加其他解释。"
            
            batch_input = create_batch_input(
                input_text=game_prompt,
                images=None,
                from_name=context.character_config.human_name,
                metadata={"skip_history": True}
            )
            
            # Get AI's move
            ai_move_response = ""
            agent_output_stream = context.agent_engine.chat(batch_input)
            async for output_item in agent_output_stream:
                if isinstance(output_item, (SentenceOutput, AudioOutput)):
                    response_part = await process_agent_output(
                        output=output_item,
                        character_config=context.character_config,
                        live2d_model=context.live2d_model,
                        tts_engine=context.tts_engine,
                        websocket_send=websocket_send,
                        tts_manager=tts_manager,
                        translate_engine=context.translate_engine,
                    )
                    ai_move_response += str(response_part) if response_part is not None else ""
            
            # Extract AI's move
            ai_move_response = ai_move_response.strip()
            if "剪刀" in ai_move_response:
                context.ai_move = "剪刀"
            elif "石头" in ai_move_response:
                context.ai_move = "石头"
            elif "布" in ai_move_response:
                context.ai_move = "布"
            else:
                # Fallback if AI response is unclear
                context.ai_move = random.choice(["剪刀", "石头", "布"])
            
            logger.info(f"AI chose move: {context.ai_move}")
            
            # Notify user to make their move
            prompt_user_move = "现在轮到你出了！请说剪刀、石头或布。"
            
            batch_input = create_batch_input(
                input_text=prompt_user_move,
                images=None,
                from_name=context.character_config.human_name,
                metadata={"skip_history": True}
            )
            
            await websocket_send(json.dumps({"type": "full-text", "text": "Thinking..."}))
            
            # Get AI's response to prompt user
            agent_output_stream = context.agent_engine.chat(batch_input)
            async for output_item in agent_output_stream:
                if isinstance(output_item, (SentenceOutput, AudioOutput)):
                    await process_agent_output(
                        output=output_item,
                        character_config=context.character_config,
                        live2d_model=context.live2d_model,
                        tts_engine=context.tts_engine,
                        websocket_send=websocket_send,
                        tts_manager=tts_manager,
                        translate_engine=context.translate_engine,
                    )
            
            logger.info("Waiting for user's move")
            context.game_state = "waiting_for_user"
            return ""
        
        # Handle user's move in rock-paper-scissors game
        elif context.game_state == "waiting_for_user":
            logger.info(f"User input for move: {input_text}")
            user_move = ""
            if "剪刀" in input_text:
                user_move = "剪刀"
            elif "石头" in input_text:
                user_move = "石头"
            elif "布" in input_text:
                user_move = "布"
            
            if user_move:
                logger.info(f"User chose move: {user_move}")
                # Determine the result
                result = ""
                if context.ai_move == user_move:
                    result = "平局"
                elif (context.ai_move == "剪刀" and user_move == "布") or \
                     (context.ai_move == "石头" and user_move == "剪刀") or \
                     (context.ai_move == "布" and user_move == "石头"):
                    result = "我赢了"
                else:
                    result = "你赢了"
                logger.info(f"Game result: {result} (AI: {context.ai_move}, User: {user_move})")
                
                # Create result prompt for AI
                result_prompt = f"我们玩猜拳，我出了{context.ai_move}，用户出了{user_move}，结果是{result}。请你说一句有趣的话来回应这个结果。"
                
                batch_input = create_batch_input(
                    input_text=result_prompt,
                    images=None,
                    from_name=context.character_config.human_name,
                    metadata={"skip_history": True}
                )
                
                await websocket_send(json.dumps({"type": "full-text", "text": "Thinking..."}))
                
                # Get AI's response
                agent_output_stream = context.agent_engine.chat(batch_input)
                async for output_item in agent_output_stream:
                    if isinstance(output_item, (SentenceOutput, AudioOutput)):
                        await process_agent_output(
                            output=output_item,
                            character_config=context.character_config,
                            live2d_model=context.live2d_model,
                            tts_engine=context.tts_engine,
                            websocket_send=websocket_send,
                            tts_manager=tts_manager,
                            translate_engine=context.translate_engine,
                        )
                
                # Reset game state
                context.game_state = "idle"
                context.ai_move = ""
                logger.info("Rock-paper-scissors game ended")
                return ""
            else:
                # Prompt user to make a valid move
                invalid_move_prompt = "请说剪刀、石头或布，这样我才能和你玩猜拳游戏哦！"
                
                batch_input = create_batch_input(
                    input_text=invalid_move_prompt,
                    images=None,
                    from_name=context.character_config.human_name,
                    metadata={"skip_history": True}
                )
                
                await websocket_send(json.dumps({"type": "full-text", "text": "Thinking..."}))
                
                # Get AI's response
                agent_output_stream = context.agent_engine.chat(batch_input)
                async for output_item in agent_output_stream:
                    if isinstance(output_item, (SentenceOutput, AudioOutput)):
                        await process_agent_output(
                            output=output_item,
                            character_config=context.character_config,
                            live2d_model=context.live2d_model,
                            tts_engine=context.tts_engine,
                            websocket_send=websocket_send,
                            tts_manager=tts_manager,
                            translate_engine=context.translate_engine,
                        )
                
                return ""

        # Create batch input
        batch_input = create_batch_input(
            input_text=input_text,
            images=images,
            from_name=context.character_config.human_name,
            metadata=metadata,
        )

        # Store user message (check if we should skip storing to history)
        skip_history = metadata and metadata.get("skip_history", False)
        if context.history_uid and not skip_history:
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="human",
                content=input_text,
                name=context.character_config.human_name,
            )

        if skip_history:
            logger.debug("Skipping storing user input to history (proactive speak)")

        logger.info(f"User input: {input_text}")
        if images:
            logger.info(f"With {len(images)} images")

        try:
            # agent.chat yields Union[SentenceOutput, Dict[str, Any]]
            agent_output_stream = context.agent_engine.chat(batch_input)

            async for output_item in agent_output_stream:
                if (
                    isinstance(output_item, dict)
                    and output_item.get("type") == "tool_call_status"
                ):
                    # Handle tool status event: send WebSocket message
                    output_item["name"] = context.character_config.character_name
                    logger.debug(f"Sending tool status update: {output_item}")

                    await websocket_send(json.dumps(output_item))

                elif isinstance(output_item, (SentenceOutput, AudioOutput)):
                    # Handle SentenceOutput or AudioOutput
                    response_part = await process_agent_output(
                        output=output_item,
                        character_config=context.character_config,
                        live2d_model=context.live2d_model,
                        tts_engine=context.tts_engine,
                        websocket_send=websocket_send,  # Pass websocket_send for audio/tts messages
                        tts_manager=tts_manager,
                        translate_engine=context.translate_engine,
                    )
                    # Ensure response_part is treated as a string before concatenation
                    response_part_str = (
                        str(response_part) if response_part is not None else ""
                    )
                    full_response += response_part_str  # Accumulate text response
                else:
                    logger.warning(
                        f"Received unexpected item type from agent chat stream: {type(output_item)}"
                    )
                    logger.debug(f"Unexpected item content: {output_item}")

        except Exception as e:
            logger.exception(
                f"Error processing agent response stream: {e}"
            )  # Log with stack trace
            await websocket_send(
                json.dumps(
                    {
                        "type": "error",
                        "message": f"Error processing agent response: {str(e)}",
                    }
                )
            )
            # full_response will contain partial response before error
        # --- End processing agent response ---

        # Wait for any pending TTS tasks
        if tts_manager.task_list:
            await asyncio.gather(*tts_manager.task_list)
            await websocket_send(json.dumps({"type": "backend-synth-complete"}))

        await finalize_conversation_turn(
            tts_manager=tts_manager,
            websocket_send=websocket_send,
            client_uid=client_uid,
        )

        if context.history_uid and full_response:  # Check full_response before storing
            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="ai",
                content=full_response,
                name=context.character_config.character_name,
                avatar=context.character_config.avatar,
            )
            logger.info(f"AI response: {full_response}")

        return full_response  # Return accumulated full_response

    except asyncio.CancelledError:
        logger.info(f"🤡👍 Conversation {session_emoji} cancelled because interrupted.")
        raise
    except Exception as e:
        logger.error(f"Error in conversation chain: {e}")
        await websocket_send(
            json.dumps({"type": "error", "message": f"Conversation error: {str(e)}"})
        )
        raise
    finally:
        cleanup_conversation(tts_manager, session_emoji)
