import asyncio
import json
import uuid
from typing import Dict, Optional
from fastapi import WebSocket
from loguru import logger
import aiohttp
from starlette.websockets import WebSocketDisconnect

from .proxy_message_queue import ProxyMessageQueue


class ProxyHandler:
    """
    A proxy handler that allows multiple clients to connect through a single WebSocket connection to the server.
    This enables scenarios like having a web client and a live platform both connected to the same VTuber server.
    """

    def __init__(self, server_url: str = "ws://localhost:12393/client-ws"):
        """
        Initialize the proxy handler.

        Args:
            server_url: The WebSocket URL of the actual server
        """
        self.server_url = server_url
        self.server_ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.clients: Dict[str, WebSocket] = {}
        self.connected = False
        self.server_task: Optional[asyncio.Task] = None
        self.lock = asyncio.Lock()

        # Initialize message queue manager
        self.message_queue = ProxyMessageQueue()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = True
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect_to_server(self):
        """Establish a WebSocket connection to the actual server"""
        if self.connected:
            return

        async with self.lock:
            if self.connected:  # Double-check to prevent race conditions
                return

            try:
                # Create session if not exists
                if not self._session:
                    self._session = aiohttp.ClientSession()
                self.server_ws = await self._session.ws_connect(self.server_url)
                self.connected = True
                logger.info(f"Proxy connected to server at {self.server_url}")

                # Initialize message queue with our forward function
                self.message_queue.initialize(self.forward_with_broadcast)

                # Start heartbeat task
                self._heartbeat_task = asyncio.create_task(self._maintain_connection())

                # Start task to receive messages from server
                self.server_task = asyncio.create_task(self.forward_server_messages())
            except Exception as e:
                logger.error(f"Failed to connect to server: {e}")
                if self._session:
                    await self._session.close()
                    self._session = None
                raise

    async def _maintain_connection(self):
        """Maintain connection with heartbeat and automatic reconnection"""
        while self._running:
            try:
                if self.connected and self.server_ws and not self.server_ws.closed:
                    # Send heartbeat
                    await self.server_ws.send_json({"type": "heartbeat"})
                    await asyncio.sleep(30)  # Heartbeat interval
                else:
                    # Try to reconnect
                    logger.info("Connection lost, attempting to reconnect...")
                    try:
                        await self.connect_to_server()
                    except Exception as e:
                        logger.error(f"Reconnection failed: {e}")
                        await asyncio.sleep(5)  # Wait before retry
            except Exception as e:
                logger.error(f"Error in connection maintenance: {e}")
                self.connected = False
                await asyncio.sleep(5)

    async def handle_client_connection(self, websocket: WebSocket):
        """
        Handle a new client connection to the proxy.

        Args:
            websocket: The client's WebSocket connection
        """
        await websocket.accept()

        # Generate a unique client ID
        client_id = str(uuid.uuid4())
        self.clients[client_id] = websocket
        logger.info(
            f"Client {client_id} connected to proxy. Total clients: {len(self.clients)}"
        )

        # Ensure server connection is established
        if not self.connected:
            await self.connect_to_server()

        if self.connected:
            try:
                init_request = {"type": "request-init-config", "client_id": client_id}
                await self.forward_to_server(init_request, client_id)
            except Exception as e:
                logger.error(f"Failed to request initialization: {e}")

        try:
            # Handle messages from this client
            while True:
                message = await websocket.receive_json()

                # Process text-input messages through the queue
                if message.get("type") == "text-input":
                    # Queue the message with the sender's ID
                    self.message_queue.queue_message(message, client_id)
                # Handle interrupt signals
                elif message.get("type") == "interrupt-signal":
                    logger.info(
                        "Received interrupt signal, marking conversation as inactive"
                    )
                    # Mark conversation as inactive to allow processing of next message
                    self.message_queue.conversation_active = False
                    # Forward the interrupt signal directly
                    await self.forward_to_server(message, client_id)
                else:
                    # Forward other message types directly
                    await self.forward_to_server(message, client_id)

        except WebSocketDisconnect:
            await self.handle_client_disconnect(client_id)
        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
            await self.handle_client_disconnect(client_id)

    async def handle_client_disconnect(self, client_id: str):
        """
        Handle a client disconnection.

        Args:
            client_id: The ID of the disconnected client
        """
        self.clients.pop(client_id, None)
        logger.info(
            f"Client {client_id} removed. Remaining clients: {len(self.clients)}"
        )

        # If no clients are connected, disconnect from the server
        if not self.clients and self.connected:
            await self.disconnect()

    async def disconnect(self):
        """Disconnect from the server"""
        self._running = False

        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.server_ws and not self.server_ws.closed:
            await self.server_ws.close()

        if self.server_task:
            self.server_task.cancel()

        # Close session
        if self._session:
            await self._session.close()
            self._session = None

        self.connected = False
        # Stop and clear the message queue
        self.message_queue.stop()
        self.message_queue.clear()
        logger.info("Proxy disconnected from server")

    async def forward_to_server(self, message: dict, sender_id: Optional[str] = None):
        """
        Forward a message from a client to the server.

        Args:
            message: The message to forward
            sender_id: ID of the client sending the message, to exclude from broadcast
        """
        if not self.connected or not self.server_ws:
            await self.connect_to_server()

        if self.server_ws and not self.server_ws.closed:
            await self.server_ws.send_json(message)

    async def forward_server_messages(self):
        """Forward messages from server to all connected clients"""
        try:
            while self.connected and self.server_ws and not self.server_ws.closed:
                try:
                    msg = await self.server_ws.receive()

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            # Parse the message
                            if not msg.data:  # Check if data is empty
                                continue

                            data = json.loads(msg.data)
                            if not data:  # Check if parsed data is empty
                                continue

                            # Check for conversation end signal
                            if (
                                data.get("type") == "control"
                                and data.get("text") == "conversation-chain-end"
                            ):
                                logger.info("Received conversation end signal")
                                self.message_queue.conversation_active = False

                            # Broadcast the message to all clients
                            await self.broadcast_to_clients(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse message data: {e}")
                            continue
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {self.server_ws.exception()}")
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        break
                except Exception as e:
                    logger.error(f"Error processing server message: {e}")
                    await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error forwarding server messages: {e}")
        finally:
            self.connected = False
            self.message_queue.conversation_active = False
            logger.info("Server message forwarding ended")

    async def broadcast_to_clients(
        self, message: dict, exclude_client: Optional[str] = None
    ):
        """
        Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast
            exclude_client: Optional client ID to exclude from broadcast
        """
        if not message:  # Add null check
            return

        disconnected_clients = []

        # Log message, but handle audio data specially to avoid huge logs
        log_msg = (
            message.copy()
            if "audio" not in message
            else {
                **{k: v for k, v in message.items() if k != "audio"},
                "audio": f"[Audio data, {len(message.get('audio', ''))} bytes truncated]",
            }
        )

        if "volumes" in log_msg and len(log_msg.get("volumes", [])) > 10:
            log_msg["volumes"] = f"[{len(message.get('volumes', []))} volume values]"

        logger.debug(f"Broadcasting to clients (excluding {exclude_client}): {log_msg}")

        for client_id, websocket in self.clients.items():
            # Skip the excluded client
            if exclude_client and client_id == exclude_client:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.handle_client_disconnect(client_id)

    async def forward_with_broadcast(
        self, message: dict, sender_id: Optional[str] = None
    ):
        """
        Forward message to server and handle any necessary broadcasting

        Args:
            message: The message to forward
            sender_id: ID of the client sending the message
        """
        # Forward to server
        await self.forward_to_server(message, sender_id)

        # For transcription messages, broadcast to other clients
        if message.get("type") == "user-input-transcription":
            await self.broadcast_to_clients(message, exclude_client=sender_id)
