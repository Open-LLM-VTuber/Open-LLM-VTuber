"""As there are many different servers and tools,
we need to construct the prompt for each server and its tools.
Plus, we need to format the tools information to a more generic structure
for OpenAI API to them by using the MCPClient.
"""

import json
import os.path

from typing import Dict, Optional
from pathlib import Path
from loguru import logger

from .types import MCPServerPrompt, MCPServerType, FormattedTool
from .client import MCPClient
from .server_manager import MCPServerManager
from .tool_manager import ToolManager
from .utils.path import validate_file

DEFAULT_SERVERS_PROMPT_PATH = Path(__file__).parent / "configs" / "servers_prompt.json"
DEFAULT_FORMATTED_TOOLS_PATH = Path(__file__).parent / "configs" / "formatted_tools.json"

DEFAULT_FILES_PATH = {
    "servers_prompt": DEFAULT_SERVERS_PROMPT_PATH,
    "formatted_tools": DEFAULT_FORMATTED_TOOLS_PATH,
}


class MixedConstructor:
    """Construct prompts for MCP servers and tools.
    Also constructs the tools information to a standard structure.
    This class is responsible for managing the prompts and tools information.
    """

    def __init__(
        self,
        prompt_paths: Dict[str, str | Path] = DEFAULT_FILES_PATH,
        server_manager: Optional[MCPServerManager] = None,
        tool_manager: Optional[ToolManager] = None,
    ) -> None:
        """Initialize the Prompt Constructor.

        Args:
            prompt_paths (Dict[str, str | Path]): Paths to the prompt files.
                The keys are 'servers_prompt' and 'formatted_tools'.
                The values are the paths to the respective files.
            server_manager (Optional[MCPServerManager]): The server manager to use for managing servers.
                If None, a default MCPServerManager will be created.
                Default is None.
        """
        self.servers_prompt = validate_file(
            prompt_paths.get("servers_prompt", DEFAULT_SERVERS_PROMPT_PATH)
        )

        self.prompts: Dict[str, Dict[str, str | float] | MCPServerPrompt] = json.loads(
            self.servers_prompt.read_text(encoding="utf-8")
        )
        
        self.server_manager = server_manager or MCPServerManager()
        self.tool_manager = tool_manager or ToolManager(
            prompt_paths.get("formatted_tools", DEFAULT_FORMATTED_TOOLS_PATH)
        )

        # Structure of self.servers_info:
        # {
        #     "MCP Server Name": {
        #         "Tool 1": {
        #             "description": "Description of Tool 1",
        #             "parameters": {
        #                 "param1": {
        #                     "type": "string",
        #                     "description": "Description of param1",
        #                 },
        #                 "param2": {
        #                     "type": "integer",
        #                     "description": "Description of param2",
        #                 },
        #             },
        #             "required": ["param1", "param2"],
        #         }
        #     }
        # }
        self.servers_info: Dict[str, Dict[str, str]] = {}
        
        self._preprocess_prompts()
    
    def _preprocess_prompts(self) -> None:
        """Preprocess the prompts to standard data structure."""
        for server_name, prompt in self.prompts.items():
            if isinstance(prompt, dict):
                content = prompt.get("content", None)
                mtime = prompt.get("mtime", None)

                if content and mtime:
                    self.prompts[server_name] = MCPServerPrompt(
                        content=content, mtime=mtime
                    )
                    continue

            logger.warning(
                f"MC: Invalid prompt format for server '{server_name}'. "
                "Expected a dictionary with 'content' and 'mtime' keys."
            )
    
    def _reformat_prompts_to_dict(self) -> None:
        """Reformat the prompts to a dictionary."""
        for server_name, prompt in self.prompts.items():
            if isinstance(prompt, MCPServerPrompt):
                self.prompts[server_name] = {
                    "content": prompt.content,
                    "mtime": prompt.mtime,
                }
                continue
            
            logger.warning(
                f"MC: Invalid prompt format for server '{server_name}'. "
                "Expected an instance of MCPServerPrompt."
            )
            
    def _reformat_tools_to_dict(self) -> None:
        """Reformat the tools to a dictionary."""
        for tool_name, tool_info in self.tool_manager.tools.items():
            if isinstance(tool_info, FormattedTool):
                self.tool_manager.tools[tool_name] = {
                    "input_schema": tool_info.input_schema,
                    "related_server": tool_info.related_server,
                    "generic_schema": tool_info.generic_schema,
                }
                continue

            logger.warning(
                f"MC: Invalid tool format for '{tool_name}'. "
                "Expected an instance of FormattedTool."
            )

    def _dump_prompts(self) -> None:
        """Dump the constructed prompts to the prompts file."""
        self._reformat_prompts_to_dict()
        self.servers_prompt.write_text(
            json.dumps(self.prompts, indent=4), encoding="utf-8"
        )
        logger.info(f"MC: Dumped prompts to '{self.servers_prompt}'")
        
    def _dump_tools(self) -> None:
        """Dump the formatted tools to the tools file."""
        self._reformat_tools_to_dict()
        self.tool_manager.formatted_tools.write_text(
            json.dumps(self.tool_manager.tools, indent=4), encoding="utf-8"
        )
        logger.info(f"MC: Dumped tools to '{self.tool_manager.formatted_tools}'")
    
    async def get_servers_info(self) -> None:
        """Get the tools information from the MCP servers."""
        for server_name in self.server_manager.servers.keys():
            async with MCPClient(self.server_manager) as client:
                try:
                    await client.connect_to_server(server_name)
                except Exception as e:
                    logger.error(
                        f"MC: Failed to connect to server '{server_name}': {e}"
                    )
                    logger.error(f"MC: Cannot get the info of server '{server_name}'")
                    continue
                self.servers_info[server_name] = {}
                tools = await client.list_tools()
                for tool in tools:
                    self.servers_info[server_name][tool.name] = {}
                    tool_info = self.servers_info[server_name][tool.name]
                    tool_info["description"] = tool.description
                    tool_info["parameters"] = tool.inputSchema.get("properties", {})
                    tool_info["required"] = tool.inputSchema.get("required", [])
                    self.tool_manager.tools[tool.name] = FormattedTool(
                        input_schema=tool.inputSchema,
                        related_server=server_name,
                    )

    def construct_servers_prompt(self, force: bool = False) -> None:
        """Construct the prompt for each server and its tools.
        
        Args:
            force (bool, optional): If True, reconstruct prompts for all servers, 
                even if they already exist in the prompts dictionary and didn't have any changes. 
                If False, skip servers by check the server file's last modified time(only custom servers).
                Default is False.
        """
        
        for server_name, tools in self.servers_info.items():
            
            server = self.server_manager.get_server(server_name)
            if server.type is MCPServerType.Custom:
                mtime = os.path.getmtime(server.path)
            else:
                mtime = -1
            
            prompt = self.prompts.get(server_name, None)
            if isinstance(prompt, MCPServerPrompt):
                if not force and prompt.mtime == mtime and mtime > 0:
                    logger.debug(
                        f"MC: Skipping server '{server_name}' as it has not changed."
                    )
                    continue
                else:
                    logger.debug(
                        f"MC: Reconstructing prompt for server '{server_name}'."
                    )
            else:
                logger.debug(f"MC: Constructing prompt for server '{server_name}'.")

            prompt = f"Server: {server_name}\n"
            prompt += "    Tools:\n"
            for tool_name, tool_info in tools.items():
                prompt += f"        {tool_name}:\n"
                prompt += f"            Description: {tool_info['description']}\n"
                prompt += "            Parameters:\n"
                for param_name, param_info in tool_info["parameters"].items():
                    description = param_info.get("description")
                    description = (
                        description
                        if description
                        else param_info.get("title", "No description provided.")
                    )
                    prompt += f"                {param_name}:\n"
                    prompt += f"                    Type: {param_info['type']}\n"
                    prompt += f"                    Description: {description}\n"
                if tool_info["required"]:
                    prompt += (
                        f"            Required: {', '.join(tool_info['required'])}\n"
                    )

            self.prompts[server_name] = MCPServerPrompt(
                content=prompt, mtime=mtime
            )
            logger.info(f"MC: Constructed prompt for server '{server_name}'.")
            
        self._dump_prompts()

    def format_tools(self) -> None:
        """Format the tools information to a standard structure."""
        for tool_name in self.tool_manager.tools.keys():
            data_object = self.tool_manager.tools.get(tool_name, None)
            if isinstance(data_object, FormattedTool):
                input_schema = data_object.input_schema
                properties: Dict[str, Dict[str, str]] = input_schema.get("properties", {})
                data_object.generic_schema = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": input_schema.get("description", "No description provided."),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                param_name: {
                                    "type": param_info.get("type", "string"),
                                    "description": param_info.get("description", param_info.get("title", "No description provided.")),
                                }
                                for param_name, param_info in properties.items()
                            },
                            "required": input_schema.get("required", []),
                        }
                    }
                }
                logger.debug(f"MC: Formatted tool '{tool_name}' to standard structure.")
            else:
                logger.warning(
                    f"MC: Invalid tool format for '{tool_name}'. "
                    "Expected an instance of FormattedTool."
                )
        
        self._dump_tools()
    
    async def run(self, force: bool = False) -> None:
        """Run the mixed constructor asynchronously."""
        await self.get_servers_info()
        self.construct_servers_prompt(force)
        self.format_tools()


# if __name__ == "__main__":
#     import asyncio
#     prompt_constructor = PromptConstructor()
#     asyncio.run(prompt_constructor.run())
#     logger.info("PC: Prompt construction completed.")
