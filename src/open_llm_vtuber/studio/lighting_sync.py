"""
Smart Studio Physical Environment Sync for AI Influencers.
Synchronizes room/desk RGB lighting (OpenRGB, Elgato Key Lights) to avatar affective state.
"""
import asyncio
import time
from typing import Optional, Dict, Any
from loguru import logger

try:
    from openrgb import OpenRGBClient
    from openrgb.utils import RGBColor
    OPENRGB_AVAILABLE = True
except ImportError:
    OPENRGB_AVAILABLE = False


class StudioLightingManager:
    """
    Manages physical room lighting synced to avatar emotions.
    """
    def __init__(self, elgato_ip: Optional[str] = None, enable_openrgb: bool = True):
        self.elgato_ip = elgato_ip
        self.enable_openrgb = enable_openrgb
        self._rgb_client = None
        self._init_openrgb()

    def _init_openrgb(self):
        if not self.enable_openrgb or not OPENRGB_AVAILABLE:
            return
        try:
            self._rgb_client = OpenRGBClient()
            logger.info("Connected to OpenRGB SDK server.")
        except Exception:
            logger.debug("OpenRGB SDK server not detected on localhost:6742. Running in virtual/mock lighting mode.")
            self._rgb_client = None

    def sync_pad_emotion(self, valence: float, arousal: float, dominance: float):
        """
        Maps 3D PAD emotional vector to RGB color and brightness.
        """
        # Determine dominant color profile
        if valence < -0.3 and arousal > 0.4:
            # Tilted / Rage -> Crimson Red
            r, g, b = 255, 0, 15
            color_name = "Crimson Red (Tilted)"
        elif valence > 0.4 and dominance > 0.3:
            # Victory / Smug -> Golden Yellow
            r, g, b = 255, 190, 0
            color_name = "Golden Yellow (Triumphant)"
        elif arousal < -0.4:
            # Sleepy / ASMR -> Deep Lavender
            r, g, b = 70, 30, 120
            color_name = "Deep Lavender (Sleepy/Calm)"
        elif valence < -0.2:
            # Cynical / Gloomy -> Muted Steel Blue
            r, g, b = 40, 90, 160
            color_name = "Steel Blue (Cynical)"
        else:
            # Neutral / Calm -> Warm Studio White
            r, g, b = 255, 230, 200
            color_name = "Warm Studio White (Calm)"

        brightness = int(max(20, min(100, (arousal + 1.0) * 50)))
        logger.info(f"Studio Lighting Sync -> {color_name} (RGB: {r},{g},{b}, Brightness: {brightness}%)")

        if self._rgb_client:
            try:
                color = RGBColor(r, g, b)
                for device in self._rgb_client.devices:
                    device.set_color(color)
            except Exception as e:
                logger.warning(f"Error setting OpenRGB color: {e}")

    async def trigger_strobe_alert(self, r: int = 255, g: int = 215, b: int = 0, flashes: int = 3):
        """Flash studio lights for donations, raids, or victories."""
        logger.info(f"Studio Strobe Alert triggered ({flashes} flashes)!")
        for _ in range(flashes):
            if self._rgb_client:
                try:
                    for device in self._rgb_client.devices:
                        device.set_color(RGBColor(r, g, b))
                except Exception:
                    pass
            await asyncio.sleep(0.1)
            if self._rgb_client:
                try:
                    for device in self._rgb_client.devices:
                        device.set_color(RGBColor(0, 0, 0))
                except Exception:
                    pass
            await asyncio.sleep(0.1)
