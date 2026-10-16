import os
import sys
import time
import asyncio
import json
import websockets
from loguru import logger

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.open_llm_vtuber.vision.screen_watcher import ScreenWatcher

def main():
    logger.info("Starting AI VTuber Screen & Game Perception Watcher...")
    ws_url = "ws://localhost:12393/client-ws"

    def on_screen_event(event_name, payload):
        prompt = payload.get("prompt", f"Visual event: {event_name}")
        logger.info(f"Dispatching visual event to avatar: {prompt}")

        async def send_event():
            try:
                async with websockets.connect(ws_url) as ws:
                    msg = {
                        "type": "text-input",
                        "text": prompt
                    }
                    await ws.send(json.dumps(msg))
                    logger.info("Visual event forwarded to VTuber successfully!")
            except Exception as e:
                logger.warning(f"Could not forward event to VTuber (is server running?): {e}")

        try:
            asyncio.run(send_event())
        except Exception as e:
            logger.error(f"Asyncio error: {e}")

    watcher = ScreenWatcher(event_callback=on_screen_event, monitor_index=1, poll_interval=0.6)
    watcher.start()

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Stopping Screen Watcher.")
        watcher.stop()

if __name__ == "__main__":
    main()
