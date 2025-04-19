import json

from pathlib import Path
from loguru import logger
from typing import Dict, Any, List, Literal
from openai import NotGiven, NOT_GIVEN

from .types import FormattedTool
from .utils.path import validate_file

DEFAULT_FORMATTED_TOOLS_PATH = Path(__file__).parent / "configs" / "formatted_tools.json"

class ToolManager:
    """Tool Manager for managing tools."""

    def __init__(
        self, formatted_tools_path: str | Path = DEFAULT_FORMATTED_TOOLS_PATH
    ) -> None:
        """Initialize the Tool Manager.

        Args:
            formatted_tools_path (str | Path): Path to the formatted tools file.
                Default is './configs/formatted_tools.json'.
        """
        self.formatted_tools = validate_file(formatted_tools_path)
        
        self.tools: Dict[str, Dict[str, Any] | FormattedTool] = json.loads(
            self.formatted_tools.read_text(encoding="utf-8")
        )
        
        self.__enabled = True
        
        self._preprocess_tools()
    
    def _preprocess_tools(self) -> None:
        """Preprocess the tools to standard data structure."""
        for tool_name, tool_info in self.tools.items():
            if isinstance(tool_info, dict):
                input_schema = tool_info.get("input_schema", None)
                related_server = tool_info.get("related_server", None)
                generic_schema = tool_info.get("generic_schema", None)

                if input_schema and related_server:
                    self.tools[tool_name] = FormattedTool(
                        input_schema=input_schema,
                        related_server=related_server,
                        generic_schema=generic_schema,
                    )
                    continue

            logger.warning(
                f"TM: Invalid tool format for '{tool_name}'. "
                "Expected a dictionary with 'input_schema' and 'related_server' keys."
            )
    
    def get_tool(self, tool_name: str) -> FormattedTool | None:
        """Get a tool by its name.

        Args:
            tool_name (str): Name of the tool.

        Returns:
            FormattedTool | None: The tool if found, else None.
        """
        return self.tools.get(tool_name, None)

    def get_all_tools(self, mode: Literal["OpenAI", "Claude"] = "OpenAI") -> List[Dict[str, Any]] | NotGiven:
        """Get all generic schemas.

        Args:
            mode (Literal["OpenAI", "Claude"]): Mode to get the schemas for.
                Default is "OpenAI".
        
        Returns:
            List[Dict[str, Any]]: List of schemas that suit API's requirements.
            NotGiven: If the tool manager is not enabled.
        """
        if not self.__enabled:
            return NOT_GIVEN
        if mode.upper() == "OPENAI":
            return [
                tool.generic_schema for tool in self.tools.values() if isinstance(tool, FormattedTool)
            ]
        elif mode.upper() == "CLAUDE":
            return [
                tool.input_schema for tool in self.tools.values() if isinstance(tool, FormattedTool)
            ]
        else:
            logger.warning(
                f"TM: Invalid mode '{mode}'. Expected 'OpenAI' or 'Claude'."
            )
            return NOT_GIVEN
    
    def enable(self) -> None:
        """Enable the tool manager."""
        self.__enabled = True
    
    def disable(self) -> None:
        """Disable the tool manager."""
        self.__enabled = False