import json
import asyncio
import numpy as np
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from loguru import logger
from .conversation import conversation_chain
from .service_context import ServiceContext
from .config_manager.utils import (
    scan_config_alts_directory,
    scan_bg_directory,
)
from .chat_history_manager import (
    create_new_history,
    store_message,
    modify_latest_message,
    get_history,
    delete_history,
    get_history_list,
)


def create_routes(default_context_cache: ServiceContext):
    router = APIRouter()
    connected_clients = []

    @router.websocket("/client-ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        session_service_context: ServiceContext = ServiceContext()
        session_service_context.load_cache(
            config=default_context_cache.config,
            system_config=default_context_cache.system_config,
            character_config=default_context_cache.character_config,
            live2d_model=default_context_cache.live2d_model,
            asr_engine=default_context_cache.asr_engine,
            tts_engine=default_context_cache.tts_engine,
            agent_engine=default_context_cache.agent_engine,
            translate_engine=default_context_cache.translate_engine,
        )

        await websocket.send_text(
            json.dumps({"type": "full-text", "text": "Connection established"})
        )

        connected_clients.append(websocket)
        logger.info("Connection established")

        await websocket.send_text(
            json.dumps(
                {
                    "type": "set-model-and-conf",
                    "model_info": session_service_context.live2d_model.model_info,
                    "conf_name": session_service_context.character_config.conf_name,
                    "conf_uid": session_service_context.character_config.conf_uid,
                }
            )
        )
        received_data_buffer = np.array([])
        # start mic
        await websocket.send_text(json.dumps({"type": "control", "text": "start-mic"}))

        current_conversation_task: asyncio.Task | None = None

        try:
            while True:
                message = await websocket.receive_text()
                data = json.loads(message)

                # ==== chat history related ====

                if data.get("type") == "fetch-history-list":
                    histories = get_history_list(
                        session_service_context.character_config.conf_uid
                    )
                    await websocket.send_text(
                        json.dumps({"type": "history-list", "histories": histories})
                    )

                elif data.get("type") == "fetch-and-set-history":
                    history_uid = data.get("history_uid")
                    if history_uid:
                        current_history_uid = history_uid
                        session_service_context.agent_engine.set_memory_from_history(
                            conf_uid=session_service_context.character_config.conf_uid,
                            history_uid=history_uid,
                        )
                        messages = [
                            msg
                            for msg in get_history(
                                session_service_context.character_config.conf_uid,
                                history_uid,
                            )
                            if msg["role"] != "system"
                        ]
                        print(f"\033[33m messages: \n {messages} \033[0m")
                        await websocket.send_text(
                            json.dumps({"type": "history-data", "messages": messages})
                        )

                elif data.get("type") == "create-new-history":
                    current_history_uid = create_new_history(
                        session_service_context.character_config.conf_uid
                    )
                    session_service_context.agent_engine.set_memory_from_history(
                        conf_uid=session_service_context.character_config.conf_uid,
                        history_uid=current_history_uid,
                    )
                    print("\033[31m create-new-history \033[0m")
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "new-history-created",
                                "history_uid": current_history_uid,
                            }
                        )
                    )

                elif data.get("type") == "delete-history":
                    history_uid = data.get("history_uid")
                    if history_uid:
                        success = delete_history(
                            session_service_context.character_config.conf_uid,
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
                        if history_uid == current_history_uid:
                            current_history_uid = None

                # ==== conversation related ====

                elif data.get("type") == "interrupt-signal":
                    if current_conversation_task is None:
                        logger.warning(
                            "❌ Conversation task was NOT cancelled because there is no running conversation."
                        )
                    else:
                        # Cancelling the task... and see if it was a success
                        if not current_conversation_task.cancel():
                            logger.warning(
                                "❌ Conversation task was NOT cancelled for some reason."
                            )
                        else:
                            logger.info(
                                "🛑 Conversation task was succesfully interrupted."
                            )
                    # The part of the AI response heard by the user before interruption
                    # is sent back from the frontend as an interruption signal
                    # We'll store this in chat history instead of the full response
                    heard_ai_response = data.get("text", "")

                    try:
                        session_service_context.agent_engine.handle_interrupt(
                            heard_ai_response
                        )
                    except Exception as e:
                        logger.error(f"Error handling interrupt: {e}")

                    if not modify_latest_message(
                        conf_uid=session_service_context.character_config.conf_uid,
                        history_uid=current_history_uid,
                        role="ai",
                        new_content=heard_ai_response,
                    ):
                        logger.warning("Failed to modify message.")
                    logger.info(
                        f"💾 Stored Paritial AI message: '''{heard_ai_response}'''"
                    )

                    store_message(
                        conf_uid=session_service_context.character_config.conf_uid,
                        history_uid=current_history_uid,
                        role="system",
                        content="[Interrupted by user]",
                    )

                # Default sampleRate = 16000, frameSamples = 512, buffer window = 32ms
                elif data.get("type") == "mic-audio-data":
                    received_data_buffer = np.append(
                        received_data_buffer,
                        np.array(data.get("audio"), dtype=np.float32),
                    )

                elif data.get("type") in [
                    "mic-audio-end",
                    "text-input",
                    "ai-speak-signal",
                ]:
                    await websocket.send_text(
                        json.dumps({"type": "full-text", "text": "Thinking..."})
                    )

                    if data.get("type") == "ai-speak-signal":
                        user_input = ""
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "full-text",
                                    "text": "AI wants to speak something...",
                                }
                            )
                        )
                    elif data.get("type") == "text-input":
                        user_input = data.get("text")
                    else:
                        user_input = received_data_buffer

                    received_data_buffer = np.array([])

                    # Get images if present
                    images = data.get("images")
                    
                    logger.debug(f"data: {data}")

                    # Initiate conversation chain task asynchronously
                    # We'll store the task object so we can cancel it if needed
                    # We'll NOT await the task here, so we can continue to receive messages
                    current_conversation_task: asyncio.Task = asyncio.create_task(
                        conversation_chain(
                            user_input=user_input,
                            asr_engine=session_service_context.asr_engine,
                            tts_engine=session_service_context.tts_engine,
                            agent_engine=session_service_context.agent_engine,
                            live2d_model=session_service_context.live2d_model,
                            websocket_send=websocket.send_text,
                            conf_uid=session_service_context.character_config.conf_uid,
                            history_uid=current_history_uid,
                            images=images,
                        )
                    )

                elif data.get("type") == "fetch-configs":
                    config_files = scan_config_alts_directory(
                        session_service_context.system_config.config_alts_dir
                    )
                    # logger.info("Sending config files +++++")
                    # logger.debug({"type": "config-files", "configs": config_files})
                    await websocket.send_text(
                        json.dumps({"type": "config-files", "configs": config_files})
                    )
                elif data.get("type") == "switch-config":
                    config_file_name: str = data.get("file")
                    if config_file_name:
                        await session_service_context.handle_config_switch(
                            websocket, config_file_name
                        )
                elif data.get("type") == "fetch-backgrounds":
                    bg_files = scan_bg_directory()
                    await websocket.send_text(
                        json.dumps({"type": "background-files", "files": bg_files})
                    )
                else:
                    print(f"\033[32m {data.get('type')} \033[0m")
                    logger.info("Unknown data type received.")

        except WebSocketDisconnect:
            connected_clients.remove(websocket)

    return router
