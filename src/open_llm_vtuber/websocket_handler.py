from typing import Dict, List, Optional, Callable, TypedDict
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from enum import Enum
import numpy as np
from loguru import logger

from .service_context import ServiceContext
from .chat_group import ChatGroupManager
from .message_handler import message_handler
from .utils.stream_audio import prepare_audio_payload
from .conversations import (
    SingleConversation,
    GroupConversation,
)
from .chat_history_manager import (
    create_new_history,
    store_message,
    modify_latest_message,
    get_history,
    delete_history,
    get_history_list,
)
from .config_manager.utils import scan_config_alts_directory, scan_bg_directory


class MessageType(Enum):
    """Enum for WebSocket message types"""

    GROUP = ["add-client-to-group", "remove-client-from-group"]
    HISTORY = [
        "fetch-history-list",
        "fetch-and-set-history",
        "create-new-history",
        "delete-history",
    ]
    CONVERSATION = ["mic-audio-end", "text-input", "ai-speak-signal"]
    CONFIG = ["fetch-configs", "switch-config"]
    CONTROL = ["interrupt-signal", "audio-play-start"]
    DATA = ["mic-audio-data"]


class WSMessage(TypedDict, total=False):
    """Type definition for WebSocket messages"""

    type: str
    text: Optional[str]
    audio: Optional[List[float]]
    images: Optional[List[str]]
    history_uid: Optional[str]
    file: Optional[str]
    display_text: Optional[dict]


class WebSocketHandler:
    """Handles WebSocket connections and message routing"""

    def __init__(self, default_context_cache: ServiceContext):
        """Initialize the WebSocket handler with default context"""
        self.client_connections: Dict[str, WebSocket] = {}
        self.client_contexts: Dict[str, ServiceContext] = {}
        self.chat_group_manager = ChatGroupManager()
        self.active_group_conversations: Dict[str, asyncio.Task] = {}
        self.default_context_cache = default_context_cache
        self.received_data_buffers: Dict[str, np.ndarray] = {}
        self.current_conversation_tasks: Dict[str, Optional[asyncio.Task]] = {}

        # Message handlers mapping
        self._message_handlers: Dict[str, Callable] = self._init_message_handlers()

    def _init_message_handlers(self) -> Dict[str, Callable]:
        """Initialize message type to handler mapping"""
        return {
            "add-client-to-group": self._handle_group_operation,
            "remove-client-from-group": self._handle_group_operation,
            "request-group-info": self._handle_group_info,
            "fetch-history-list": self._handle_history_list_request,
            "fetch-and-set-history": self._handle_fetch_history,
            "create-new-history": self._handle_create_history,
            "delete-history": self._handle_delete_history,
            "interrupt-signal": self._handle_interrupt,
            "mic-audio-data": self._handle_audio_data,
            "mic-audio-end": self._handle_conversation_trigger,
            "text-input": self._handle_conversation_trigger,
            "ai-speak-signal": self._handle_conversation_trigger,
            "fetch-configs": self._handle_fetch_configs,
            "switch-config": self._handle_config_switch,
            "fetch-backgrounds": self._handle_fetch_backgrounds,
            "audio-play-start": self._handle_audio_play_start,
        }

    async def handle_new_connection(
        self, websocket: WebSocket, client_uid: str
    ) -> None:
        """
        Handle new WebSocket connection setup

        Args:
            websocket: The WebSocket connection
            client_uid: Unique identifier for the client

        Raises:
            Exception: If initialization fails
        """
        try:
            # Initialize service context
            session_service_context = await self._init_service_context()

            # Store client data
            await self._store_client_data(
                websocket, client_uid, session_service_context
            )

            # Send initial messages
            await self._send_initial_messages(
                websocket, client_uid, session_service_context
            )

            logger.info(f"Connection established for client {client_uid}")

        except Exception as e:
            logger.error(
                f"Failed to initialize connection for client {client_uid}: {e}"
            )
            await self._cleanup_failed_connection(client_uid)
            raise

    async def handle_websocket_communication(
        self, websocket: WebSocket, client_uid: str
    ) -> None:
        """
        Handle ongoing WebSocket communication

        Args:
            websocket: The WebSocket connection
            client_uid: Unique identifier for the client
        """
        try:
            while True:
                try:
                    data = await websocket.receive_json()
                    message_handler.handle_message(client_uid, data)
                    await self._route_message(websocket, client_uid, data)
                except WebSocketDisconnect:
                    raise
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self._send_error(websocket, str(e))
                    continue

        except WebSocketDisconnect:
            logger.info(f"Client {client_uid} disconnected")
            raise
        except Exception as e:
            logger.error(f"Fatal error in WebSocket communication: {e}")
            raise

    async def _route_message(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """
        Route incoming message to appropriate handler

        Args:
            websocket: The WebSocket connection
            client_uid: Client identifier
            data: Message data
        """
        msg_type = data.get("type")
        if not msg_type:
            logger.warning("Message received without type")
            return

        handler = self._message_handlers.get(msg_type)
        if handler:
            await handler(websocket, client_uid, data)
        else:
            if msg_type != "frontend-playback-complete":
                logger.warning(f"Unknown message type: {msg_type}")

    async def _send_error(self, websocket: WebSocket, error_message: str) -> None:
        """Send error message to client"""
        await websocket.send_text(
            json.dumps({"type": "error", "message": error_message})
        )

    async def _init_service_context(self) -> ServiceContext:
        """Initialize service context for a new session"""
        session_service_context = ServiceContext()
        session_service_context.load_cache(
            config=self.default_context_cache.config,
            system_config=self.default_context_cache.system_config,
            character_config=self.default_context_cache.character_config,
            live2d_model=self.default_context_cache.live2d_model,
            asr_engine=self.default_context_cache.asr_engine,
            tts_engine=self.default_context_cache.tts_engine,
            agent_engine=self.default_context_cache.agent_engine,
            translate_engine=self.default_context_cache.translate_engine,
        )
        return session_service_context

    async def _store_client_data(
        self,
        websocket: WebSocket,
        client_uid: str,
        session_service_context: ServiceContext,
    ):
        """Store client data and initialize group status"""
        self.client_connections[client_uid] = websocket
        self.client_contexts[client_uid] = session_service_context
        self.received_data_buffers[client_uid] = np.array([])

        self.chat_group_manager.client_group_map[client_uid] = ""
        await self.send_group_update(websocket, client_uid)

    async def _send_initial_messages(
        self,
        websocket: WebSocket,
        client_uid: str,
        session_service_context: ServiceContext,
    ):
        """Send initial connection messages to the client"""
        await websocket.send_text(
            json.dumps({"type": "full-text", "text": "Connection established"})
        )

        await websocket.send_text(
            json.dumps(
                {
                    "type": "set-model-and-conf",
                    "model_info": session_service_context.live2d_model.model_info,
                    "conf_name": session_service_context.character_config.conf_name,
                    "conf_uid": session_service_context.character_config.conf_uid,
                    "client_uid": client_uid,
                }
            )
        )

        # Send initial group status
        await self.send_group_update(websocket, client_uid)

        # Start microphone
        await websocket.send_text(json.dumps({"type": "control", "text": "start-mic"}))

    async def _handle_group_operation(
        self, websocket: WebSocket, client_uid: str, data: dict
    ):
        """
        Handle group-related operations and ensure all group members are synchronized
        
        Args:
            websocket: The WebSocket connection
            client_uid: Client identifier
            data: Operation data containing type and target_uid
        """
        operation = data.get("type")
        target_uid = data.get(
            "invitee_uid" if operation == "add-client-to-group" else "target_uid"
        )

        if target_uid:
            # Get all affected members before operation
            old_members = self.chat_group_manager.get_group_members(client_uid)
            target_old_members = self.chat_group_manager.get_group_members(target_uid)
            all_affected_members = set(old_members + target_old_members)

            if operation == "add-client-to-group":
                success, message = self.chat_group_manager.add_client_to_group(
                    inviter_uid=client_uid, invitee_uid=target_uid
                )

                if success and target_uid in self.client_connections:
                    try:
                        # Send group update to the newly invited member
                        await self.send_group_update(
                            self.client_connections[target_uid], target_uid
                        )
                        # Notify the invited member
                        await self.client_connections[target_uid].send_text(
                            json.dumps(
                                {
                                    "type": "group-operation-result",
                                    "success": True,
                                    "message": f"You have been invited to the group by {client_uid}",
                                }
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to update invited member {target_uid}: {e}")

            else:  # remove operation
                success, message = self.chat_group_manager.remove_client_from_group(
                    remover_uid=client_uid, target_uid=target_uid
                )

            # Send operation result to the initiator
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "group-operation-result",
                        "success": success,
                        "message": message,
                    }
                )
            )

            if success:
                # For removal operation, we need to update the removed member as well
                if operation != "add-client-to-group" and target_uid in self.client_connections:
                    try:
                        # Send empty group update to removed member
                        await self.client_connections[target_uid].send_text(
                            json.dumps(
                                {
                                    "type": "group-update",
                                    "members": [],
                                    "is_owner": False,
                                }
                            )
                        )
                        # Notify the removed member
                        await self.client_connections[target_uid].send_text(
                            json.dumps(
                                {
                                    "type": "group-operation-result",
                                    "success": True,
                                    "message": "You have been removed from the group",
                                }
                            )
                        )
                    except Exception as e:
                        logger.error(f"Failed to update removed member {target_uid}: {e}")

                # Get new group members after operation
                new_members = self.chat_group_manager.get_group_members(client_uid)
                all_affected_members.update(new_members)

                # Update remaining group members
                for member_uid in all_affected_members:
                    if member_uid in self.client_connections and member_uid != target_uid:
                        try:
                            await self.send_group_update(
                                self.client_connections[member_uid], member_uid
                            )
                            # Send notification about the operation
                            if member_uid != client_uid:
                                await self.client_connections[member_uid].send_text(
                                    json.dumps(
                                        {
                                            "type": "group-operation-result",
                                            "success": True,
                                            "message": (
                                                f"Member {target_uid} was {'added to' if operation == 'add-client-to-group' else 'removed from'} the group"
                                            ),
                                        }
                                    )
                                )
                        except Exception as e:
                            logger.error(f"Failed to update member {member_uid}: {e}")

    async def broadcast_to_group(
        self, group_members: list[str], message: dict, exclude_uid: str = None
    ):
        """Broadcasts a message to all members in a group except the sender"""
        for member_uid in group_members:
            if member_uid != exclude_uid and member_uid in self.client_connections:
                try:
                    await self.client_connections[member_uid].send_text(
                        json.dumps(message)
                    )
                except Exception as e:
                    logger.error(f"Failed to broadcast to {member_uid}: {e}")

    async def send_group_update(self, websocket: WebSocket, client_uid: str):
        """Sends group information to a client"""
        group = self.chat_group_manager.get_client_group(client_uid)
        if group:
            current_members = self.chat_group_manager.get_group_members(client_uid)
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "group-update",
                        "members": current_members,
                        "is_owner": group.owner_uid == client_uid,
                    }
                )
            )
        else:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "group-update",
                        "members": [],
                        "is_owner": False,
                    }
                )
            )

    async def handle_group_interrupt(self, group_id: str, heard_response: str = ""):
        """Handles interruption for a group conversation"""
        if group_id not in self.active_group_conversations:
            return

        task = self.active_group_conversations[group_id]
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"🛑 Group conversation {group_id} cancelled successfully.")

        self.active_group_conversations.pop(group_id, None)

        group = self.chat_group_manager.get_group_by_id(group_id)
        if group:
            await self._handle_group_interrupt_cleanup(group, heard_response)

    async def _handle_group_interrupt_cleanup(self, group, heard_response: str):
        """Helper method to clean up after group interruption"""
        for member_uid in group.members:
            if member_uid in self.client_contexts:
                try:
                    context = self.client_contexts[member_uid]
                    await self._cleanup_member_context(context, heard_response)
                except Exception as e:
                    logger.error(
                        f"Error handling interrupt for member {member_uid}: {e}"
                    )

        await self.broadcast_to_group(
            list(group.members),
            {
                "type": "interrupt-signal",
                "text": "conversation-interrupted",
            },
        )

    async def handle_disconnect(self, client_uid: str):
        """Handle client disconnection"""
        # Clean up group conversation if client was in one
        group = self.chat_group_manager.get_client_group(client_uid)
        if group:
            await self.handle_group_interrupt(group.group_id)

        # Get group members before cleanup
        old_group_members = self.chat_group_manager.get_group_members(client_uid)

        # Cancel any ongoing conversation
        if client_uid in self.current_conversation_tasks:
            task = self.current_conversation_tasks[client_uid]
            if task:
                task.cancel()

        # Clean up client data
        self.chat_group_manager.remove_client(client_uid)
        self.client_connections.pop(client_uid, None)
        self.client_contexts.pop(client_uid, None)
        self.received_data_buffers.pop(client_uid, None)
        self.current_conversation_tasks.pop(client_uid, None)

        # Send updates to remaining group members
        for member_uid in old_group_members:
            if member_uid != client_uid and member_uid in self.client_connections:
                await self.send_group_update(
                    self.client_connections[member_uid], member_uid
                )
                await self.client_connections[member_uid].send_text(
                    json.dumps(
                        {
                            "type": "group-operation-result",
                            "success": True,
                            "message": f"Member {client_uid} disconnected",
                        }
                    )
                )

        logger.info(f"Client {client_uid} disconnected")
        message_handler.cleanup_client(client_uid)

    async def _handle_history_list_request(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle request for chat history list"""
        context = self.client_contexts[client_uid]
        histories = get_history_list(context.character_config.conf_uid)
        await websocket.send_text(
            json.dumps({"type": "history-list", "histories": histories})
        )

    async def _handle_fetch_history(
        self, websocket: WebSocket, client_uid: str, data: dict
    ):
        """Handle fetching and setting specific chat history"""
        history_uid = data.get("history_uid")
        if not history_uid:
            return

        context = self.client_contexts[client_uid]
        # Update history_uid in service context
        context.history_uid = history_uid
        context.agent_engine.set_memory_from_history(
            conf_uid=context.character_config.conf_uid,
            history_uid=history_uid,
        )

        messages = [
            msg
            for msg in get_history(
                context.character_config.conf_uid,
                history_uid,
            )
            if msg["role"] != "system"
        ]
        await websocket.send_text(
            json.dumps({"type": "history-data", "messages": messages})
        )

    async def _handle_create_history(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle creation of new chat history"""
        context = self.client_contexts[client_uid]
        history_uid = create_new_history(context.character_config.conf_uid)
        if history_uid:
            context.history_uid = history_uid
            context.agent_engine.set_memory_from_history(
                conf_uid=context.character_config.conf_uid,
                history_uid=history_uid,
            )
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "new-history-created",
                        "history_uid": history_uid,
                    }
                )
            )

    async def _handle_delete_history(
        self, websocket: WebSocket, client_uid: str, data: dict
    ):
        """Handle deletion of chat history"""
        history_uid = data.get("history_uid")
        if not history_uid:
            return

        context = self.client_contexts[client_uid]
        success = delete_history(
            context.character_config.conf_uid,
            history_uid,
        )
        await websocket.send_text(
            json.dumps(
                {
                    "type": "history-deleted",
                    "success": success,
                    "history_uid": history_uid,
                }
            )
        )
        if history_uid == context.history_uid:
            context.history_uid = None

    async def _handle_interrupt(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle conversation interruption"""
        heard_response = data.get("text", "")
        context = self.client_contexts[client_uid]
        group = self.chat_group_manager.get_client_group(client_uid)

        if group and len(group.members) > 1:
            await self.handle_group_interrupt(group.group_id, heard_response)
        else:
            if client_uid in self.current_conversation_tasks:
                task = self.current_conversation_tasks[client_uid]
                if task and not task.done():
                    task.cancel()
                    logger.info("🛑 Conversation task was successfully interrupted")

            try:
                context.agent_engine.handle_interrupt(heard_response)
            except Exception as e:
                logger.error(f"Error handling interrupt: {e}")

            if context.history_uid:
                if not modify_latest_message(
                    conf_uid=context.character_config.conf_uid,
                    history_uid=context.history_uid,
                    role="ai",
                    new_content=heard_response,
                ):
                    logger.warning("Failed to modify message")

                store_message(
                    conf_uid=context.character_config.conf_uid,
                    history_uid=context.history_uid,
                    role="system",
                    content="[Interrupted by user]",
                )

    async def _handle_audio_data(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle incoming audio data"""
        audio_data = data.get("audio", [])
        if audio_data:
            self.received_data_buffers[client_uid] = np.append(
                self.received_data_buffers[client_uid],
                np.array(audio_data, dtype=np.float32),
            )

    async def _handle_conversation_trigger(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle triggers that start a conversation"""
        context = self.client_contexts[client_uid]
        msg_type = data.get("type")

        if msg_type == "ai-speak-signal":
            user_input = ""
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "full-text",
                        "text": "AI wants to speak something...",
                    }
                )
            )
        elif msg_type == "text-input":
            user_input = data.get("text", "")
        else:  # mic-audio-end
            user_input = self.received_data_buffers[client_uid]
            self.received_data_buffers[client_uid] = np.array([])

        # Get images if present
        images = data.get("images")

        # Handle group vs individual conversation
        group = self.chat_group_manager.get_client_group(client_uid)
        if group and len(group.members) > 1:
            await self._handle_group_conversation(
                client_uid, user_input, images, group, websocket
            )
        else:
            await self._handle_individual_conversation(
                client_uid, user_input, images, websocket, context
            )

    async def _handle_group_conversation(
        self,
        client_uid: str,
        user_input: str,
        images: list,
        group,
        websocket: WebSocket,
    ):
        """Handle group conversation logic"""
        if (
            group.group_id not in self.active_group_conversations
            or self.active_group_conversations[group.group_id].done()
        ):

            logger.info(f"Starting new group conversation for {group.group_id}")

            conversation = GroupConversation(
                client_contexts=self.client_contexts,
                client_connections=self.client_connections,
                broadcast_func=self.broadcast_to_group,
                group_members=group.members,
                initiator_client_uid=client_uid,
            )

            self.active_group_conversations[group.group_id] = asyncio.create_task(
                conversation.process_conversation(
                    user_input=user_input,
                    images=images,
                )
            )

    async def _handle_individual_conversation(
        self,
        client_uid: str,
        user_input: str,
        images: list,
        websocket: WebSocket,
        context: ServiceContext,
    ) -> None:
        """Handle individual conversation logic"""
        conversation = SingleConversation(
            context=context,
            websocket_send=websocket.send_text,
            client_uid=client_uid,
        )

        self.current_conversation_tasks[client_uid] = asyncio.create_task(
            conversation.process_conversation(
                user_input=user_input,
                images=images,
            )
        )

    async def _handle_fetch_configs(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle fetching available configurations"""
        context = self.client_contexts[client_uid]
        config_files = scan_config_alts_directory(context.system_config.config_alts_dir)
        await websocket.send_text(
            json.dumps({"type": "config-files", "configs": config_files})
        )

    async def _handle_config_switch(
        self, websocket: WebSocket, client_uid: str, data: dict
    ):
        """Handle switching to a different configuration"""
        config_file_name = data.get("file")
        if config_file_name:
            context = self.client_contexts[client_uid]
            await context.handle_config_switch(websocket, config_file_name)

    async def _handle_fetch_backgrounds(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle fetching available background images"""
        bg_files = scan_bg_directory()
        await websocket.send_text(
            json.dumps({"type": "background-files", "files": bg_files})
        )

    async def _handle_audio_play_start(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """
        Handle audio playback start notification
        """
        group_members = self.chat_group_manager.get_group_members(client_uid)
        if len(group_members) > 1:
            display_text = data.get("display_text")
            if display_text:
                silent_payload = prepare_audio_payload(
                    audio_path=None,
                    display_text=display_text,
                    actions=None,
                    forwarded=True,
                )
                await self.broadcast_to_group(
                    group_members, silent_payload, exclude_uid=client_uid
                )

    async def _handle_group_info(
        self, websocket: WebSocket, client_uid: str, data: WSMessage
    ) -> None:
        """Handle group info request"""
        await self.send_group_update(websocket, client_uid)

    async def _cleanup_member_context(
        self, context: ServiceContext, heard_response: str
    ):
        """Clean up member context after interruption"""
        context.agent_engine.handle_interrupt(heard_response)

        if context.history_uid:
            if not modify_latest_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="ai",
                new_content=heard_response,
            ):
                logger.warning("Failed to modify message")

            store_message(
                conf_uid=context.character_config.conf_uid,
                history_uid=context.history_uid,
                role="system",
                content="[Interrupted by user]",
            )
