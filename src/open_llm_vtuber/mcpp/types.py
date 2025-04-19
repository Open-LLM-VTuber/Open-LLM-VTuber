from dataclasses import dataclass, field
from datetime import timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path


class MCPServerType(str, Enum):
    """Enum for MCP Server Types."""

    Official = 0
    Custom = 1


@dataclass
class MCPServerPrompt:
    
    content: str
    mtime: Optional[float] = None


@dataclass
class MCPServer:
    """Class representing a MCP Server
    
    Args:
        name (str): Name of the server.
        command (str): Command to run the server.
        args (List[str], optional): Arguments for the command. Defaults to an empty list.
        env (Optional[Dict[str, str]], optional): Environment variables for the command. Defaults to None.
        timeout (Optional[timedelta], optional): Timeout for the command. Defaults to 10 seconds.
        type (MCPServerType, optional): Type of the server. Defaults to MCPServerType.Custom.
        path (Optional[Path], optional): Path to the server executable. Defaults to None.
    """
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    timeout: Optional[timedelta] = timedelta(seconds=10)
    type: MCPServerType = MCPServerType.Custom
    path: Optional[Path] = None
    

@dataclass
class FormattedTool:
    """"Class representing a formatted tool
    
    Args:
        input_schema (Dict[str, Any]): Input schema for the tool.
        related_server (str): The name of the server that contains the tool.
        generic_schema (Optional[Dict[str, Any]], optional): Generic schema for the tool. Defaults to None.
    """
    input_schema: Dict[str, Any]
    related_server: str
    generic_schema: Optional[Dict[str, Any]] = None


@dataclass
class CallableTool:
    """Class representing a callable tool
    
    Args:
        name (str): Name of the tool.
        server (str): The name of the server that contains the tool.
        args (Dict[str, Any], optional): Arguments for the tool. Defaults to an empty dictionary.
        id (Optional[str], optional): ID of the tool. Defaults to None.
    """
    name: str
    server: str
    args: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None


@dataclass
class ToolCallFunctionObject:
    """Class representing a function object in a tool call
    
    This class mimics the OpenAI API function object structure for tool calls.
    
    Args:
        name (str): Name of the function.
        arguments (str): Arguments for the function as a JSON string.
    """
    name: str = ""
    arguments: str = ""


@dataclass
class ToolCallObject:
    """Class representing a tool call object
    
    This class mimics the OpenAI API ChoiceDeltaToolCall structure.
    
    Args:
        id (str): Unique identifier for the tool call.
        type (str): Type of the tool call, typically "function".
        index (int): Index of the tool call in the sequence.
        function (ToolCallFunctionObject): Function information for the tool call.
    """
    id: Optional[str] = None
    type: str = "function"
    index: int = 0
    function: ToolCallFunctionObject = field(default_factory=ToolCallFunctionObject)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCallObject":
        """Create a ToolCallObject from a dictionary
        
        Args:
            data (Dict[str, Any]): Dictionary containing tool call data.
            
        Returns:
            ToolCallObject: A new ToolCallObject instance.
        """
        function = ToolCallFunctionObject(
            name=data["function"]["name"],
            arguments=data["function"]["arguments"]
        )
        return cls(
            id=data["id"],
            type=data["type"],
            index=data["index"],
            function=function
        )