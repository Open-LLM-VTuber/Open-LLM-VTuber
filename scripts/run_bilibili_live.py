import os
import sys
import asyncio
from loguru import logger

# Add project root to path to enable imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.open_llm_vtuber.live.bilibili_live import BiliBiliLivePlatform
from src.open_llm_vtuber.config_manager.utils import read_yaml, validate_config


async def main():
    """
    Main function to run the BiliBili Live platform client.
    Connects to BiliBili Live room and forwards danmaku messages to the VTuber.
    """
    logger.info("Starting BiliBili Live platform client")

    try:
        # Load configuration
        config_path = os.path.join(project_root, "conf.yaml")
        config_data = read_yaml(config_path)
        config = validate_config(config_data)

        # Extract BiliBili Live configuration
        bilibili_config = config.live_config.bilibili_live

        # Check if room IDs are provided
        if not bilibili_config.room_ids:
            logger.error(
                "No BiliBili room IDs specified in configuration. Please add at least one room ID."
            )
            return

        logger.info(f"Connecting to BiliBili Live rooms: {bilibili_config.room_ids}")

        # Initialize and run the BiliBili Live platform
        platform = BiliBiliLivePlatform(
            room_ids=bilibili_config.room_ids, sessdata=bilibili_config.sessdata
        )

        await platform.run()

    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.error("Make sure you have installed blivedm with: pip install blivedm")
    except Exception as e:
        logger.error(f"Error starting BiliBili Live client: {e}")
        import traceback

        logger.debug(traceback.format_exc())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down BiliBili Live platform")

# Usage: uv run python -m src.open_llm_vtuber.live.run_bilibili_live
