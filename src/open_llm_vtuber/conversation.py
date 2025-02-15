import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncIterator, List, Dict, Union, Any

import numpy as np
from fastapi import WebSocket
from loguru import logger

from .agent.agents.agent_interface import AgentInterface
from .agent.input_types import BatchInput, TextData, ImageData, TextSource, ImageSource
from .agent.output_types import BaseOutput, SentenceOutput, AudioOutput, Actions
from .asr.asr_interface import ASRInterface
from .chat_history_manager import store_message
from .live2d_model import Live2dModel
from .translate.translate_interface import TranslateInterface
from .tts.tts_interface import TTSInterface
from .utils.stream_audio import prepare_audio_payload


class TTSTaskManager:
    """Manages TTS tasks and their sequential execution"""

    def __init__(self):
        self.task_list: List[asyncio.Task] = []
        self.next_index_to_play: int = 0

    def clear(self):
        """Clear all tasks and reset counter"""
        self.task_list.clear()
        self.next_index_to_play = 0

    async def speak(
        self,
        tts_text: str,
        live2d_model: Live2dModel,
        tts_engine: TTSInterface,
        websocket_send: WebSocket.send,
        display_text: str | None = None,
        actions: Actions | None = None,
    ) -> None:
        """
        Generate and send audio for a sentence. If tts_text is empty,
        sends a silent display payload.

        Args:
            tts_text: Text to be spoken
            live2d_model: Live2D model instance
            tts_engine: TTS engine instance
            websocket_send: WebSocket send function
            display_text: Text to display (defaults to tts_text)
            actions: Actions object
        """
        if not display_text:
            display_text = tts_text

        if not tts_text or not tts_text.strip():
            logger.debug("Empty TTS text, sending silent display payload")
            audio_payload = prepare_audio_payload(
                audio_path=None,
                actions=actions,
                display_text=display_text,
            )
            await websocket_send(json.dumps(audio_payload))
            return

        logger.debug(f"🏃Generating audio for '''{tts_text}'''...")

        current_task_index = len(self.task_list)
        tts_task = asyncio.create_task(
            tts_engine.async_generate_audio(
                text=tts_text,
                file_name_no_ext=f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}",
            )
        )
        self.task_list.append(tts_task)

        try:
            while current_task_index != self.next_index_to_play:
                await asyncio.sleep(0.01)

            audio_file_path = await tts_task

            try:
                audio_payload = prepare_audio_payload(
                    audio_path=audio_file_path,
                    actions=actions,
                    display_text=display_text,
                )
                logger.debug("Sending Audio payload.")
                await websocket_send(json.dumps(audio_payload))

                tts_engine.remove_file(audio_file_path)
                logger.debug("Payload sent. Audio cache file cleaned.")

            except Exception as e:
                logger.error(f"Error preparing audio payload: {e}")
                tts_engine.remove_file(audio_file_path)

        except Exception as e:
            logger.error(f"Error in speak function: {e}")
        finally:
            self.next_index_to_play += 1

            if current_task_index == len(self.task_list) - 1:
                self.clear()


async def conversation_chain(
    user_input: Union[str, np.ndarray],
    asr_engine: ASRInterface,
    agent_engine: AgentInterface,
    tts_engine: TTSInterface,
    live2d_model: Live2dModel,
    websocket_send: WebSocket.send,
    translate_engine: TranslateInterface,
    conf_uid: str = "",
    history_uid: str = "",
    images: List[Dict[str, Any]] = None,
    command_handler=None,
) -> str:
    """
    One iteration of the main conversation chain.

    Args:
        user_input: User input (string or audio array)
        asr_engine: ASR engine instance
        agent_engine: Agent instance
        tts_engine: TTS engine instance
        live2d_model: Live2D model instance
        websocket_send: WebSocket send function
        conf_uid: Configuration ID
        history_uid: History ID
        images: Optional list of image data from frontend
        command_handler: Optional command handler function

    Returns:
        str: Complete response from the agent
    """
    tts_manager = TTSTaskManager()
    full_response: str = ""

    try:
        session_emoji = np.random.choice(EMOJI_LIST)

        await websocket_send(
            json.dumps(
                {
                    "type": "control",
                    "text": "conversation-chain-start",
                }
            )
        )

        logger.info(f"New Conversation Chain {session_emoji} started!")

        # Handle audio input
        input_text = user_input
        if isinstance(user_input, np.ndarray):
            logger.info("Transcribing audio input...")
            input_text = await asr_engine.async_transcribe_np(user_input)
            await websocket_send(
                json.dumps({"type": "user-input-transcription", "text": input_text})
            )

        # Prepare BatchInput
        batch_input = BatchInput(
            texts=[TextData(source=TextSource.INPUT, content=input_text)],
            images=(
                [
                    ImageData(
                        source=ImageSource(img["source"]),
                        data=img["data"],
                        mime_type=img["mime_type"],
                    )
                    for img in (images or [])
                ]
                if images
                else None
            ),
        )

        store_message(conf_uid, history_uid, "human", input_text)
        logger.info(f"User input: {input_text}")
        if images:
            logger.info(f"With {len(images)} images")

        # Process agent output
        agent_output: AsyncIterator[BaseOutput] = agent_engine.chat(batch_input)

        logger.debug(f"🏃 tts_engine.__dict__ '''{tts_engine.__dict__}'''...")

        async for output in agent_output:
            if isinstance(output, SentenceOutput):
                async for display_text, tts_text, actions in output:
                    logger.debug(f"🏃 output '''{output}'''...")

                    if translate_engine:
                        tts_text = translate_engine.translate(tts_text)
                        logger.info(f"🏃 Text after translation '''{tts_text}'''...")
                    else:
                        logger.info(
                            "🚫 No translation engine available. Skipping translation."
                        )
                    full_response += display_text
                    await tts_manager.speak(
                        tts_text=tts_text,
                        display_text=display_text,
                        actions=actions,
                        live2d_model=live2d_model,
                        tts_engine=tts_engine,
                        websocket_send=websocket_send,
                    )
            elif isinstance(output, AudioOutput):
                async for audio_path, display_text, transcript, actions in output:
                    full_response += display_text
                    audio_payload = prepare_audio_payload(
                        audio_path=audio_path,
                        display_text=display_text,
                        actions=actions,
                    )
                    await websocket_send(json.dumps(audio_payload))

        if tts_manager.task_list:
            await asyncio.gather(*tts_manager.task_list)

    except asyncio.CancelledError:
        logger.info(f"🤡👍 Conversation {session_emoji} cancelled because interrupted.")

    finally:
        logger.debug(f"🧹 Clearing up conversation {session_emoji}.")
        tts_manager.clear()

        # Check if the AI response is a web search command
        if "[web_search]" in full_response.strip().lower():
            if command_handler:
                # search_result = command_handler(full_response)
                # logger.info("Web search result via conversation chain: {}", search_result)
                # Extract the query and convert to the format expected by command_handler
                search_query = full_response.split("[web_search]")[1].strip()
                modified_response = f"web_search {search_query}"
                search_result = command_handler(modified_response)
                
                results = search_result.get("results", [])

                if results:
                    # Create a summary prompt with all results
                    search_summary = "Here are the search results:\n\n"
                    for i, result in enumerate(results, 1):
                        search_summary += f"{i}. {result.get('title', 'No title')}\n"
                        search_summary += f"   {result.get('body', 'No details available.')}\n\n"
                    
                    # Create a new prompt for the AI to summarize
                    summary_prompt = (
                        "Based on these search results, please provide a natural, conversational "
                        "summary of the most important and recent news. Focus on the key facts and "
                        "latest developments. Here are the search results:\n\n" + search_summary + "\n\n"
                        "Please synthesize this information into a clear, engaging summary that a person "
                        "would find interesting and informative. Start with the most recent or significant news."
                    )
                    
                    # Get AI to summarize the results
                    try:
                        # Create a batch input for the summary
                        summary_batch_input = BatchInput(
                            texts=[TextData(source=TextSource.INPUT, content=summary_prompt)]
                        )

                        # Get the summary using chat
                        summary_response = ""
                        async for output in agent_engine.chat(summary_batch_input):
                            if isinstance(output, SentenceOutput):
                                async for display_text, tts_text, actions in output:
                                    summary_response += display_text  # Accumulate the text
                        
                        if not summary_response.strip():  # Check if we got an empty response
                            raise Exception("No summary generated")
                            
                        logger.info(f"Generated summary response: {summary_response}")
                        
                        # Store the summary as the full response
                        full_response = summary_response
                        
                        # Have the assistant speak the summary
                        await tts_manager.speak(
                            tts_text=summary_response,
                            display_text=summary_response,
                            live2d_model=live2d_model,
                            tts_engine=tts_engine,
                            websocket_send=websocket_send,
                        )
                    except Exception as e:
                        logger.error(f"Error during summary generation: {str(e)}")
                        full_response = "I found some information but had trouble summarizing it."
                        await tts_manager.speak(
                            tts_text=full_response,
                            display_text=full_response,
                            live2d_model=live2d_model,
                            tts_engine=tts_engine,
                            websocket_send=websocket_send,
                        )
                
                # Store the message and send control message
                store_message(conf_uid, history_uid, "ai", full_response)
                logger.info(f"💾 Stored AI message (web search): '''{full_response}'''")
                await websocket_send(json.dumps({
                    "type": "control",
                    "text": "conversation-chain-end",
                }))
                logger.info(f"😎👍✅ Conversation Chain {session_emoji} completed!")
                return full_response

        if full_response:
            store_message(conf_uid, history_uid, "ai", full_response)
            logger.info(f"💾 Stored AI message: '''{full_response}'''")

        await websocket_send(
            json.dumps(
                {
                    "type": "control",
                    "text": "conversation-chain-end",
                }
            )
        )
        logger.info(f"😎👍✅ Conversation Chain {session_emoji} completed!")
        return full_response


EMOJI_LIST = [
    "🐶",
    "🐱",
    "🐭",
    "🐹",
    "🐰",
    "🦊",
    "🐻",
    "🐼",
    "🐨",
    "🐯",
    "🦁",
    "🐮",
    "🐷",
    "🐸",
    "🐵",
    "🐔",
    "🐧",
    "🐦",
    "🐤",
    "🐣",
    "🐥",
    "🦆",
    "🦅",
    "🦉",
    "🦇",
    "🐺",
    "🐗",
    "🐴",
    "🦄",
    "🐝",
    "🌵",
    "🎄",
    "🌲",
    "🌳",
    "🌴",
    "🌱",
    "🌿",
    "☘️",
    "🍀",
    "🍂",
    "🍁",
    "🍄",
    "🌾",
    "💐",
    "🌹",
    "🌸",
    "🌛",
    "🌍",
    "⭐️",
    "🔥",
    "🌈",
    "🌩",
    "⛄️",
    "🎃",
    "🎄",
    "🎉",
    "🎏",
    "🎗",
    "🀄️",
    "🎭",
    "🎨",
    "🧵",
    "🪡",
    "🧶",
    "🥽",
    "🥼",
    "🦺",
    "👔",
    "👕",
    "👜",
    "👑",
]
