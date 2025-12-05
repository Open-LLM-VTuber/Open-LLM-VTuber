import asyncio
from typing import Dict, Optional, Deque, Any, Callable
from collections import deque
from loguru import logger


class ProxyMessageQueue:
    """
    Manages message queuing and consumption for the proxy handler.
    Implements a producer-consumer pattern with conversation state awareness.
    """

    def __init__(self):
        """Initialize the message queue manager"""
        self.message_queue: Deque[Dict] = deque()
        self._conversation_active = False
        self.lock = asyncio.Lock()
        self._consumer_task = None
        self._forward_func = None
        self._running = False

    def initialize(self, forward_func: Callable[[Dict, Optional[str]], Any]):
        """
        Initialize the queue with a message forwarding function.

        Args:
            forward_func: Function to call when forwarding messages to the server
        """
        self._forward_func = forward_func
        logger.debug("Message queue initialized with forward function")

    def queue_message(self, message: Dict, sender_id: Optional[str] = None) -> None:
        """
        Add a message to the queue.

        Args:
            message: The message to queue
            sender_id: Optional ID of the client that sent the message
        """
        # Store the message along with its sender ID
        queue_item = {"message": message, "sender_id": sender_id}
        logger.info(
            f"Queuing message: {message.get('text', '')} (active conversation: {self._conversation_active})"
        )
        self.message_queue.append(queue_item)

        # Start consumer if needed
        self._ensure_consumer_running()

    @property
    def conversation_active(self) -> bool:
        """Get the conversation active state"""
        return self._conversation_active

    @conversation_active.setter
    def conversation_active(self, active: bool) -> None:
        """
        Set the conversation active state.

        Args:
            active: True if a conversation is active, False otherwise
        """
        if self._conversation_active != active:
            logger.debug(f"Setting conversation active state to: {active}")
            self._conversation_active = active

            # If conversation becomes inactive, make sure consumer is running to process any queued messages
            if not active and self.has_pending_messages():
                self._ensure_consumer_running()

    def has_pending_messages(self) -> bool:
        """
        Check if there are pending messages in the queue.

        Returns:
            bool: True if there are messages to process, False otherwise
        """
        return len(self.message_queue) > 0

    def _ensure_consumer_running(self):
        """Ensure the consumer task is running if needed"""
        if not self._forward_func:
            logger.warning("Cannot start consumer: no forward function provided")
            return

        if self._consumer_task is None or self._consumer_task.done():
            self._running = True
            self._consumer_task = asyncio.create_task(self._consume_loop())
            logger.debug("Started message consumer task")

    async def _consume_loop(self):
        """Background task that consumes messages based on conversation state"""
        try:
            while self._running:
                # Wait a short time to prevent CPU hogging
                await asyncio.sleep(0.1)

                # Try to consume a message if appropriate
                async with self.lock:
                    if not self._conversation_active and self.has_pending_messages():
                        # Get next message
                        queue_item = self.message_queue.popleft()
                        message = queue_item["message"]
                        sender_id = queue_item["sender_id"]

                        logger.info(
                            f"Consumer processing message: {message.get('text', '')}"
                        )

                        # Set active before forwarding to prevent race conditions
                        self._conversation_active = True

                        # Forward the message outside the lock to prevent deadlocks
                        asyncio.create_task(self._forward_message(message, sender_id))

                # If queue is empty and we've been idle for a while, we can pause the consumer
                if not self.has_pending_messages() and not self._conversation_active:
                    await asyncio.sleep(1)  # Wait a bit longer before deciding to stop
                    if (
                        not self.has_pending_messages()
                        and not self._conversation_active
                    ):
                        logger.debug(
                            "No more pending messages and no active conversation, pausing consumer"
                        )
                        break

        except Exception as e:
            logger.error(f"Error in message consumer loop: {e}")
        finally:
            self._running = False
            logger.debug("Message consumer task ended")

    async def _forward_message(self, message: Dict, sender_id: Optional[str] = None):
        """Forward a message using the provided forward function"""
        try:
            if self._forward_func:
                # If this is a text input, send transcription first
                if message.get("type") == "text-input":
                    # Create transcription message
                    transcription_message = message.copy()
                    transcription_message["type"] = "user-input-transcription"
                    # Forward transcription message
                    await self._forward_func(transcription_message, sender_id)

                # Forward the original message
                await self._forward_func(message, sender_id)
            else:
                logger.warning("No forward function available to process message")
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            # If forwarding fails, mark conversation as inactive to allow next message
            self._conversation_active = False

    def stop(self):
        """Stop the consumer task"""
        self._running = False
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()

    def clear(self):
        """Clear all pending messages"""
        self.message_queue.clear()
        logger.info("Message queue cleared")
