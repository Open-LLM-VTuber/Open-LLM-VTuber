from __future__ import annotations

import json
from ..agent.output_types import DisplayText, Actions
from ..service_context import ServiceContext
from .tts_manager import TTSTaskManager
from .conversation_utils import (
    send_conversation_start_signals,
    finalize_conversation_turn,
)


async def speak_text(
    context: ServiceContext,
    websocket_send,
    text: str,
) -> None:
    display_text = DisplayText(
        text=text,
        name=context.character_config.character_name,
        avatar=context.character_config.avatar,
    )

    actions = None
    if context.live2d_model:
        try:
            expr = context.live2d_model.extract_emotion(text)
            if expr:
                actions = Actions(expressions=expr)
        except Exception:
            pass

    tts_text = (
        context.live2d_model.remove_emotion_keywords(text)
        if context.live2d_model
        else text
    )

    tts_manager = TTSTaskManager()

    await websocket_send(json.dumps({"type": "full-text", "text": display_text.text}))
    await send_conversation_start_signals(websocket_send)

    await tts_manager.speak(
        tts_text=tts_text,
        display_text=display_text,
        actions=actions,
        live2d_model=context.live2d_model,
        tts_engine=context.tts_engine,
        websocket_send=websocket_send,
    )
    await finalize_conversation_turn(
        tts_manager=tts_manager,
        websocket_send=websocket_send,
        client_uid=context.client_uid,
    )
