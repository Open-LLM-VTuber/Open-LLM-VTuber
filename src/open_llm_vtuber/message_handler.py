from typing import Dict, Optional, Tuple
import asyncio
from loguru import logger
from collections import defaultdict


class MessageHandler:
    def __init__(self):
        self._response_events: Dict[
            str, Dict[Tuple[str, Optional[str]], asyncio.Event]
        ] = defaultdict(dict)
        self._response_data: Dict[str, Dict[Tuple[str, Optional[str]], dict]] = (
            defaultdict(dict)
        )

    async def wait_for_response(
        self,
        client_uid: str,
        response_type: str,
        request_id: str | None = None,
        timeout: float | None = None,
    ) -> Optional[dict]:
        """
        Wait for a response of specific type and optional request_id from a client.

        Args:
            client_uid: Client identifier
            response_type: Type of response to wait for
            request_id: Optional identifier for the specific request
            timeout: Optional timeout in seconds. If None, wait indefinitely

        Returns:
            Optional[dict]: Response data if received, None if timeout
        """
        event = asyncio.Event()
        response_key = (response_type, request_id)
        self._response_events[client_uid][response_key] = event

        try:
            if timeout is not None:
                # Wait with timeout
                await asyncio.wait_for(event.wait(), timeout)
            else:
                # Wait indefinitely
                await event.wait()

            return self._response_data[client_uid].pop(response_key, None)
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout waiting for {response_type} (ID: {request_id}) from {client_uid}"
            )
            return None
        finally:
            self._response_events[client_uid].pop(response_key, None)

    def handle_message(self, client_uid: str, message: dict) -> None:
        """
        Process an incoming message, potentially matching a response event waiting.

        Args:
            client_uid: Client identifier
            message: Message data dictionary, expected to contain 'type' and optionally 'request_id'
        """
        msg_type = message.get("type")
        request_id = message.get("request_id")
        if not msg_type:
            return

        response_key = (msg_type, request_id)

        if (
            client_uid in self._response_events
            and response_key in self._response_events[client_uid]
        ):
            self._response_data[client_uid][response_key] = message
            self._response_events[client_uid][response_key].set()

    def cleanup_client(self, client_uid: str) -> None:
        """
        Cleanup all events and cached data for a given client.

        Args:
            client_uid: Client identifier
        """
        if client_uid in self._response_events:
            for event in self._response_events[client_uid].values():
                event.set()
            self._response_events.pop(client_uid)
            self._response_data.pop(client_uid, None)


message_handler = MessageHandler()
