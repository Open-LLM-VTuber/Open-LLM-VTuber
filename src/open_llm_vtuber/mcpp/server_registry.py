"""MCP Server Manager for Open-LLM-Vtuber."""

import shutil
import json

from pathlib import Path
from typing import Dict, Optional, Union, Any
from loguru import logger

from .types import MCPServer
from .utils.path import validate_file

DEFAULT_CONFIG_PATH = "mcp_servers.json"


class ServerRegistry:
    """MCP Server Manager for managing server files."""

    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        """Initialize the MCP Server Manager."""
        try:
            config_path = validate_file(config_path, ".json")
        except ValueError:
            logger.error(
                f"MCPSR: File '{config_path}' does not exist, or is not a json file."
            )
            raise ValueError(
                f"MCPSR: File '{config_path}' does not exist, or is not a json file."
            )

        self.config: Dict[str, Union[str, dict]] = json.loads(
            config_path.read_text(encoding="utf-8")
        )

        self.servers: Dict[str, MCPServer] = {}

        self.npx_available = self._detect_runtime("npx")
        self.uvx_available = self._detect_runtime("uvx")
        self.node_available = self._detect_runtime("node")

        self.load_servers()

    def _detect_runtime(self, target: str) -> bool:
        """Check if a runtime is available in the system PATH."""
        founded = shutil.which(target)
        return True if founded else False

    def load_servers(self) -> None:
        """Load servers from the config file."""
        servers_config: Dict[str, Dict[str, Any]] = self.config.get("mcp_servers", {})
        if servers_config == {}:
            logger.warning("MCPSR: No servers found in the config file.")
            return

        for server_name, server_details in servers_config.items():
            if "command" not in server_details or "args" not in server_details:
                logger.warning(
                    f"MCPSR: Invalid server details for '{server_name}'. Ignoring."
                )
                continue

            command = server_details["command"]
            if command == "npx":
                if not self.npx_available:
                    logger.warning(
                        f"MCPSR: npx is not available. Cannot load server '{server_name}'."
                    )
                    continue
            elif command == "uvx":
                if not self.uvx_available:
                    logger.warning(
                        f"MCPSR: uvx is not available. Cannot load server '{server_name}'."
                    )
                    continue

            elif command == "node":
                if not self.node_available:
                    logger.warning(
                        f"MCPSR: node is not available. Cannot load server '{server_name}'."
                    )
                    continue

            self.servers[server_name] = MCPServer(
                name=server_name,
                command=command,
                args=server_details["args"],
                env=server_details.get("env", None),
                cwd=server_details.get("cwd", None),
                timeout=server_details.get("timeout", None),
            )
            logger.debug(f"MCPSR: Loaded server: '{server_name}'.")

    def remove_server(self, server_name: str) -> None:
        """Remove a server from the available servers."""
        try:
            self.servers.pop(server_name)
            logger.info(f"MCPSR: Removed server: {server_name}")
        except KeyError:
            logger.warning(f"MCPSR: Server '{server_name}' not found. Cannot remove.")

    def get_server(self, server_name: str) -> Optional[MCPServer]:
        """Get the server by name."""
        return self.servers.get(server_name, None)
