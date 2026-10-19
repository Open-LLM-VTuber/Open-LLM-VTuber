import os
import sys
import time
import asyncio
from loguru import logger

# Add project root to path to enable imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.open_llm_vtuber.live.tiktok_live import TikTokLivePlatform
from src.open_llm_vtuber.config_manager.utils import read_yaml, validate_config
from src.open_llm_vtuber.security import with_token


def build_platform(config):
    """Create the connector from the validated configuration."""
    tiktok_config = config.live_config.tiktok_live

    unique_id = (tiktok_config.unique_id or "").strip().lstrip("@")
    if not unique_id:
        raise ValueError(
            "live_config.tiktok_live.unique_id is empty in conf.yaml "
            "(use the username of the account that is live, without @)"
        )

    proxy_url = (tiktok_config.proxy_url or "").strip()
    if not proxy_url:
        proxy_url = f"ws://127.0.0.1:{config.system_config.port}/proxy-ws"

    # A22: when VTUBER_WS_TOKEN is set the server rejects token-less
    # handshakes, so the connector has to carry it like any other client.
    proxy_url = with_token(proxy_url)

    return TikTokLivePlatform(
        unique_id=unique_id,
        proxy_url=proxy_url,
        max_queue=tiktok_config.max_queue,
        cooldown_seconds=tiktok_config.cooldown_seconds,
        min_gift_coins=tiktok_config.min_gift_coins,
        reply_to_gifts=tiktok_config.reply_to_gifts,
        reply_to_follows=tiktok_config.reply_to_follows,
    )


def main():
    """
    Run the TikTok Live platform client.

    The process itself is the supervisor: if the connector dies (TikTok or
    proxy connection lost, unexpected exception) it is restarted after 5 s.
    Ctrl+C stops it cleanly.
    """
    logger.info("Starting TikTok Live platform client")

    try:
        config_path = os.path.join(project_root, "conf.yaml")
        config_data = read_yaml(config_path)
        config = validate_config(config_data)
    except Exception as e:
        logger.error(f"Failed to load conf.yaml: {e}")
        return 1

    tiktok_config = config.live_config.tiktok_live
    if not tiktok_config.enabled:
        logger.warning(
            "live_config.tiktok_live.enabled is false in conf.yaml; nothing to do"
        )
        return 0

    while True:
        try:
            platform = build_platform(config)
            asyncio.run(platform.run())
            logger.info("TikTok connector finished; exiting")
            return 0
        except KeyboardInterrupt:
            logger.info("Shutting down TikTok Live platform")
            return 0
        except Exception as e:
            logger.opt(exception=True).error(f"Connector crashed: {e}; retrying in 5 s")
            time.sleep(5)


if __name__ == "__main__":
    sys.exit(main() or 0)

# Usage: uv run python scripts/run_tiktok_live.py
