import os
import sys
import asyncio
from loguru import logger

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.open_llm_vtuber.live.twitch_live import TwitchLivePlatform
import websockets
import json

async def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "shroud"
    logger.info(f"Starting Anonymous Twitch Live Chat listener for channel: #{channel}")

    twitch = TwitchLivePlatform(channel_name=channel, message_cooldown=3.0)

    # Bridge Twitch chat messages into the Open-LLM-VTuber WebSocket server
    ws_url = "ws://localhost:12393/client-ws"

    async def on_twitch_message(msg):
        text = msg["formatted_prompt"]
        try:
            async with websockets.connect(ws_url) as ws:
                payload = {
                    "type": "text-input",
                    "text": text
                }
                await ws.send(json.dumps(payload))
                logger.info(f"Forwarded to VTuber: {text}")
        except Exception as e:
            logger.warning(f"Could not forward to VTuber (is server running?): {e}")

    twitch.register_message_handler(on_twitch_message)
    await twitch.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopping Twitch listener.")
