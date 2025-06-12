"""Constructs prompts for servers and tools, formats tool information for OpenAI API."""

from typing import Dict, Optional, List, Tuple, Any
from loguru import logger

from .types import FormattedTool
from .mcp_client import MCPClient
from .server_registry import ServerRegistry


class ToolAdapter:
    """Dynamically fetches tool information from enabled MCP servers and formats it."""

    def __init__(self, server_registery: Optional[ServerRegistry] = None) -> None:
        """Initialize with an ServerRegistry."""
        self.server_registery = server_registery or ServerRegistry()

    async def get_server_and_tool_info(
        self, enabled_servers: List[str]
    ) -> Tuple[Dict[str, Dict[str, str]], Dict[str, FormattedTool]]:
        """Fetch tool information from specified enabled MCP servers."""
        servers_info: Dict[str, Dict[str, str]] = {}
        formatted_tools: Dict[str, FormattedTool] = {}

        if not enabled_servers:
            logger.warning(
                "MC: No enabled MCP servers specified. Cannot fetch tool info."
            )
            return servers_info, formatted_tools

        logger.debug(f"MC: Fetching tool info for enabled servers: {enabled_servers}")

        # Use a single client instance for efficiency
        async with MCPClient(self.server_registery) as client:
            for server_name in enabled_servers:
                if server_name not in self.server_registery.servers:
                    logger.warning(
                        f"MC: Enabled server '{server_name}' not found in Server Manager. Skipping."
                    )
                    continue

                try:
                    servers_info[server_name] = {}
                    tools = await client.list_tools(server_name)
                    logger.debug(
                        f"MC: Found {len(tools)} tools on server '{server_name}'"
                    )
                    for tool in tools:
                        servers_info[server_name][tool.name] = {}
                        tool_info = servers_info[server_name][tool.name]
                        tool_info["description"] = tool.description
                        tool_info["parameters"] = tool.inputSchema.get("properties", {})
                        tool_info["required"] = tool.inputSchema.get("required", [])

                        # Store the tool info in FormattedTool format
                        formatted_tools[tool.name] = FormattedTool(
                            input_schema=tool.inputSchema,
                            related_server=server_name,
                            description=tool.description,
                            # Generic schema will be generated later if needed
                            generic_schema=None,
                        )
                except (ValueError, RuntimeError, ConnectionError) as e:
                    logger.error(
                        f"MC: Failed to get info for server '{server_name}': {e}"
                    )
                    if (
                        server_name not in servers_info
                    ):  # Ensure entry exists even on error
                        servers_info[server_name] = {}
                    continue  # Continue to next server
                except Exception as e:
                    logger.error(
                        f"MC: Unexpected error for server '{server_name}': {e}"
                    )
                    if server_name not in servers_info:
                        servers_info[server_name] = {}
                    continue  # Continue to next server

        logger.debug(
            f"MC: Finished fetching tool info. Found {len(formatted_tools)} tools across enabled servers."
        )
        return servers_info, formatted_tools

    def construct_mcp_prompt_string(
        self, servers_info: Dict[str, Dict[str, str]]
    ) -> str:
        """Build a single prompt string describing enabled servers and their tools."""
        full_prompt_content = ""
        if not servers_info:
            logger.warning(
                "MC: Cannot construct MCP prompt string, servers_info is empty."
            )
            return full_prompt_content

        logger.debug(
            f"MC: Constructing MCP prompt string for {len(servers_info)} server(s)."
        )

        for server_name, tools in servers_info.items():
            if not tools:  # Skip servers where info couldn't be fetched
                logger.warning(
                    f"MC: No tool info available for server '{server_name}', skipping in prompt."
                )
                continue

            prompt_content = f"Server: {server_name}\n"
            prompt_content += "    Tools:\n"
            for tool_name, tool_info in tools.items():
                prompt_content += f"        {tool_name}:\n"
                # Ensure description is handled correctly (might be None)
                description = tool_info.get("description", "No description available.")
                prompt_content += f"            Description: {description}\n"
                parameters = tool_info.get("parameters", {})
                if parameters:
                    prompt_content += "            Parameters:\n"
                    for param_name, param_info in parameters.items():
                        param_desc = param_info.get("description") or param_info.get(
                            "title", "No description provided."
                        )
                        param_type = param_info.get(
                            "type", "string"
                        )  # Default to string if type missing
                        prompt_content += f"                {param_name}:\n"
                        prompt_content += f"                    Type: {param_type}\n"
                        prompt_content += (
                            f"                    Description: {param_desc}\n"
                        )
                required = tool_info.get("required", [])
                if required:
                    prompt_content += f"            Required: {', '.join(required)}\n"
            full_prompt_content += prompt_content + "\n"  # Add newline between servers

        logger.debug("MC: Finished constructing MCP prompt string.")
        return full_prompt_content.strip()  # Remove trailing newline

    def format_tools_for_api(
        self, formatted_tools_dict: Dict[str, FormattedTool]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Format tools to OpenAI and Claude function-calling compatible schemas."""
        openai_tools = []
        claude_tools = []

        if not formatted_tools_dict:
            logger.warning(
                "MC: Cannot format tools for API, input dictionary is empty."
            )
            return openai_tools, claude_tools

        logger.debug(f"MC: Formatting {len(formatted_tools_dict)} tools for API usage.")

        for tool_name, data_object in formatted_tools_dict.items():
            if not isinstance(data_object, FormattedTool):
                logger.warning(f"MC: Skipping invalid tool format for '{tool_name}'")
                continue

            input_schema = data_object.input_schema
            properties: Dict[str, Dict[str, str]] = input_schema.get("properties", {})
            tool_description = data_object.description or "No description provided."
            required_params = input_schema.get("required", [])

            # Format for OpenAI
            openai_function_params = {
                "type": "object",
                "properties": {},
                "required": required_params,
                "additionalProperties": False,  # Disallow extra properties
            }
            for param_name, param_info in properties.items():
                param_schema = {
                    "type": param_info.get("type", "string"),
                    "description": param_info.get("description")
                    or param_info.get("title", "No description provided."),
                }
                # Add enum if present
                if "enum" in param_info:
                    param_schema["enum"] = param_info["enum"]
                # Handle array type correctly
                if param_schema["type"] == "array" and "items" in param_info:
                    param_schema["items"] = param_info["items"]
                elif param_schema["type"] == "array" and "items" not in param_info:
                    logger.warning(
                        f"MC: Array parameter '{param_name}' in tool '{tool_name}' is missing 'items' definition. Assuming items are strings."
                    )
                    param_schema["items"] = {"type": "string"}  # Default or log warning

                openai_function_params["properties"][param_name] = param_schema

            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_description,
                        "parameters": openai_function_params,
                    },
                }
            )

            # Format for Claude
            claude_input_schema = {
                "type": "object",
                "properties": properties,
                "required": required_params,
            }
            claude_tools.append(
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": claude_input_schema,
                }
            )

        logger.debug(
            f"MC: Finished formatting tools. OpenAI: {len(openai_tools)}, Claude: {len(claude_tools)}."
        )
        return openai_tools, claude_tools

    async def get_tools(
        self, enabled_servers: List[str]
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Run the dynamic fetching and formatting process."""
        logger.info(
            f"MC: Running dynamic tool construction for servers: {enabled_servers}"
        )
        servers_info, formatted_tools_dict = await self.get_server_and_tool_info(
            enabled_servers
        )
        mcp_prompt_string = self.construct_mcp_prompt_string(servers_info)
        openai_tools, claude_tools = self.format_tools_for_api(formatted_tools_dict)
        logger.info("MC: Dynamic tool construction complete.")
        return mcp_prompt_string, openai_tools, claude_tools
