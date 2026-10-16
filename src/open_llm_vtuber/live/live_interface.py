from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from loguru import logger


class LivePlatformInterface(ABC):
    """
    Abstract base class for all live platform integrations.

    All live platform listeners (Twitch, YouTube, Kick, VRChat, etc.)
    must inherit from this class and implement connect/disconnect.
    """

    def __init__(self):
        self._running = False

    @abstractmethod
    async def connect(self, **kwargs) -> bool:
        """Connect to the live platform. Returns True on success."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the live platform."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    async def start_receiving(self):
        """Start listening for incoming messages. Override in subclass."""
        logger.warning(f"{self.__class__.__name__}: start_receiving not implemented")

    def register_message_handler(self, handler):
        """Register a callback for incoming messages."""
        logger.warning(f"{self.__class__.__name__}: register_message_handler not implemented")

    async def send_message(self, text: str) -> bool:
        """Send a message to the platform. Returns True on success."""
        logger.warning(f"{self.__class__.__name__}: send_message not implemented")
        return False

    async def run(self):
        """Connect and start receiving in a loop."""
        if await self.connect():
            await self.start_receiving()

    def stop(self):
        """Stop the platform listener."""
        self._running = False
