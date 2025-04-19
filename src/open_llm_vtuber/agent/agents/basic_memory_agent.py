import json
from typing import AsyncIterator, List, Dict, Any, Callable, Literal
from loguru import logger
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall

from .agent_interface import AgentInterface
from ..output_types import SentenceOutput, DisplayText
from ..stateless_llm.stateless_llm_interface import StatelessLLMInterface
from ...chat_history_manager import get_history
from ..transformers import (
    sentence_divider,
    actions_extractor,
    tts_filter,
    display_processor,
)
from ...config_manager import TTSPreprocessorConfig
from ..input_types import BatchInput, TextSource, ImageSource
from prompts import prompt_loader
from ...mcpp.client import MCPClient
from ...mcpp.server_manager import MCPServerManager
from ...mcpp.tool_manager import ToolManager
from ...mcpp.json_detector import StreamJSONDetector
from ...mcpp.types import CallableTool


class BasicMemoryAgent(AgentInterface):
    """
    Agent with basic chat memory using a list to store messages.
    Implements text-based responses with sentence processing pipeline.
    """

    _system: str = """You are an error message repeater. 
        Your job is repeating this error message: 
        'No system prompt set. Please set a system prompt'. 
        Don't say anything else.
        """

    def __init__(
        self,
        llm: StatelessLLMInterface,
        system: str,
        live2d_model,
        tts_preprocessor_config: TTSPreprocessorConfig = None,
        faster_first_response: bool = True,
        segment_method: str = "pysbd",
        use_mcpp: bool = True,
        mcp_prompt: str = None,
        interrupt_method: Literal["system", "user"] = "user",
        tool_prompts: Dict[str, str] = None,
    ):
        """
        Initialize the agent with LLM, system prompt and configuration

        Args:
            llm: `StatelessLLMInterface` - The LLM to use
            system: `str` - System prompt
            live2d_model: `Live2dModel` - Model for expression extraction
            tts_preprocessor_config: `TTSPreprocessorConfig` - Configuration for TTS preprocessing
            faster_first_response: `bool` - Whether to enable faster first response
            segment_method: `str` - Method for sentence segmentation
            interrupt_method: `Literal["system", "user"]` -
                Methods for writing interruptions signal in chat history.
            tool_prompts: `Dict[str, str]` - Dictionary of tool prompts from system_config

        """
        super().__init__()
        self._memory = []
        self._live2d_model = live2d_model
        self._tts_preprocessor_config = tts_preprocessor_config
        self._faster_first_response = faster_first_response
        self._segment_method = segment_method
        self._mcp_server_manager = MCPServerManager() if use_mcpp else None
        self._tool_manager = ToolManager() if use_mcpp else None
        self._json_detector = StreamJSONDetector() if use_mcpp else None
        self._mcp_prompt = mcp_prompt if mcp_prompt else None
        self.prompt_mode_flag = False
        self.interrupt_method = interrupt_method
        self._tool_prompts = tool_prompts or {}
        # Flag to ensure a single interrupt handling per conversation
        self._interrupt_handled = False
        self._set_llm(llm)
        self.set_system(system)
        logger.info("BasicMemoryAgent initialized.")

    def _set_llm(self, llm: StatelessLLMInterface):
        """
        Set the (stateless) LLM to be used for chat completion.
        Instead of assigning directly to `self.chat`, store it to `_chat_function`
        so that the async method chat remains intact.

        Args:
            llm: StatelessLLMInterface - the LLM instance.
        """
        self._llm = llm
        self.chat = self._chat_function_factory(llm.chat_completion)

    def set_system(self, system: str):
        """
        Set the system prompt
        system: str
            the system prompt
        """
        logger.debug(f"Memory Agent: Setting system prompt: '''{system}'''")

        if self.interrupt_method == "user":
            system = f"{system}\n\nIf you received `[interrupted by user]` signal, you were interrupted."
            

        self._system = system

    def _add_message(
        self,
        message: str | List[Dict[str, Any]],
        role: str,
        display_text: DisplayText | None = None,
    ):
        """
        Add a message to the memory

        Args:
            message: Message content (string or list of content items)
            role: Message role
            display_text: Optional display information containing name and avatar
        """
        if isinstance(message, list):
            text_content = ""
            for item in message:
                if item.get("type") == "text":
                    text_content += item["text"]
        else:
            text_content = message

        message_data = {
            "role": role,
            "content": text_content,
        }

        # Add display information if provided
        if display_text:
            if display_text.name:
                message_data["name"] = display_text.name
            if display_text.avatar:
                message_data["avatar"] = display_text.avatar

        self._memory.append(message_data)

    def set_memory_from_history(self, conf_uid: str, history_uid: str) -> None:
        """Load the memory from chat history"""
        messages = get_history(conf_uid, history_uid)

        self._memory = []
        self._memory.append(
            {
                "role": "system",
                "content": self._system,
            }
        )

        for msg in messages:
            self._memory.append(
                {
                    "role": "user" if msg["role"] == "human" else "assistant",
                    "content": msg["content"],
                }
            )

    def handle_interrupt(self, heard_response: str) -> None:
        """
        Handle an interruption by the user.

        Args:
            heard_response: str - The part of the AI response heard by the user before interruption
        """
        if self._interrupt_handled:
            return

        self._interrupt_handled = True

        if self._memory and self._memory[-1]["role"] == "assistant":
            self._memory[-1]["content"] = heard_response + "..."
        else:
            if heard_response:
                self._memory.append(
                    {
                        "role": "assistant",
                        "content": heard_response + "...",
                    }
                )
        self._memory.append(
            {
                "role": "system" if self.interrupt_method == "system" else "user",
                "content": "[Interrupted by user]",
            }
        )

    def _to_text_prompt(self, input_data: BatchInput) -> str:
        """
        Format BatchInput into a prompt string for the LLM.

        Args:
            input_data: BatchInput - The input data containing texts and images

        Returns:
            str - Formatted message string
        """
        message_parts = []

        # Process text inputs in order
        for text_data in input_data.texts:
            if text_data.source == TextSource.INPUT:
                message_parts.append(text_data.content)
            elif text_data.source == TextSource.CLIPBOARD:
                message_parts.append(f"[Clipboard content: {text_data.content}]")

        # Process images in order
        if input_data.images:
            message_parts.append("\nImages in this message:")
            for i, img_data in enumerate(input_data.images, 1):
                source_desc = {
                    ImageSource.CAMERA: "captured from camera",
                    ImageSource.SCREEN: "screenshot",
                    ImageSource.CLIPBOARD: "from clipboard",
                    ImageSource.UPLOAD: "uploaded",
                }[img_data.source]
                message_parts.append(f"- Image {i} ({source_desc})")

        return "\n".join(message_parts)

    def _to_messages(self, input_data: BatchInput) -> List[Dict[str, Any]]:
        """
        Prepare messages list with image support.
        """
        messages = self._memory.copy()

        if input_data.images:
            content = []
            text_content = self._to_text_prompt(input_data)
            content.append({"type": "text", "text": text_content})

            for img_data in input_data.images:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": img_data.data, "detail": "auto"},
                    }
                )

            user_message = {"role": "user", "content": content}
        else:
            user_message = {"role": "user", "content": self._to_text_prompt(input_data)}

        messages.append(user_message)
        self._add_message(user_message["content"], "user")
        return messages

    def _chat_function_factory(
        self, 
        chat_func: Callable[[
            List[Dict[str, Any]], str, List[Dict[str, Any]]],
            AsyncIterator[str | List[ChoiceDeltaToolCall]
        ]]
    ) -> Callable[..., AsyncIterator[SentenceOutput]]:
        """
        Create the chat pipeline with transformers

        The pipeline:
        LLM tokens -> sentence_divider -> actions_extractor -> display_processor -> tts_filter
        """

        @tts_filter(self._tts_preprocessor_config)
        @display_processor()
        @actions_extractor(self._live2d_model)
        @sentence_divider(
            faster_first_response=self._faster_first_response,
            segment_method=self._segment_method,
            valid_tags=["think"],
        )
        async def chat_with_memory(input_data: BatchInput) -> AsyncIterator[str]:
            """
            Chat implementation with memory and processing pipeline

            Args:
                input_data: BatchInput

            Returns:
                AsyncIterator[str] - Token stream from LLM
            """

            messages = self._to_messages(input_data)

            # MCP Plus enabled
            if self._mcp_server_manager:
                tools_waiting_to_call: List[CallableTool] = []
                tools = self._tool_manager.get_all_tools()
                logger.debug(f"TM: All available tools: {tools}")
                
                # Get token stream from LLM
                token_stream: AsyncIterator[str | List[ChoiceDeltaToolCall]] = chat_func(
                    messages, self._system, tools=tools
                )
                complete_response = ""
                
                # TODO: Support older LLMs using API Function Call
                # Stage A: Deal with the token stream, detecting tool calls.
                # Case 1: Process the token stream in API Tool Use mode.
                if not self.prompt_mode_flag:
                    async for token in token_stream:
                        # Case 1-1: Handle Tool Call tokens.
                        if isinstance(token, list):
                            try:
                                for tool_call in token:
                                    tool = self._tool_manager.get_tool(tool_call.function.name)
                                    if not tool:
                                        raise ValueError(
                                            f"Tool '{tool_call.function.name}' not found in ToolManager."
                                        )
                                    server = tool.related_server
                                    tool = CallableTool(
                                        name=tool_call.function.name,
                                        server=server,
                                        args=json.loads(
                                            tool_call.function.arguments
                                        ),
                                        id=tool_call.id,
                                    )
                                    tools_waiting_to_call.append(tool)
                                    
                            except json.JSONDecodeError:
                                logger.error("Failed to decode tool call arguments")
                                logger.error(f"Tool call: {tool_call}")
                                yield "Error calling tool: Failed to decode tool call arguments, see the log for details."
                                continue
                            
                            except ValueError as e:
                                logger.error(f"Error processing tool call: {e}")
                                yield token
                                continue
                        
                        # Case 1-2: API not support tools, switch to prompt mode
                        elif token == "__API_NOT_SUPPORT_TOOLS__":
                            self._tool_manager.disable()
                            if self._mcp_prompt:
                                self._system += f"\n\n{self._mcp_prompt}"
                            logger.info("Disabled ToolManager, trying to use MCP via prompt.")
                            
                            # First time need to recreate the LLM.
                            re_stream = chat_func(messages, self._system)
                            async for token in self.process_json_stream(re_stream):
                                # Normal tokens
                                if not isinstance(token, list):
                                    yield token
                                    complete_response += token
                                    continue
                                # Handle JSON response
                                tools = self._process_tool_from_dict_list(token)
                                if tools:
                                    tools_waiting_to_call.extend(tools)
                                    logger.info(f"Tool call detected: {tools}")
                        
                        # Case 1-3: Handle normal tokens.
                        else:
                            yield token
                            complete_response += token
                
                # Case 2: Process the token stream in prompt mode.
                else:
                    async for token in self.process_json_stream(token_stream):
                        # Normal tokens
                        if not isinstance(token, list):
                            yield token
                            complete_response += token
                            continue
                        # Handle JSON response
                        tools = self._process_tool_from_dict_list(token)
                        if tools:
                            tools_waiting_to_call.extend(tools)
                            logger.info(f"Tool call detected: {tools}")
                
                
                # Stage B: Call the tools.
                if tools_waiting_to_call:
                    tools_response = []
                    for tool in tools_waiting_to_call:
                        try:
                            logger.info(f"Start calling tool: {tool.name}")
                            async with MCPClient(self._mcp_server_manager) as client:
                                await client.connect_to_server(tool.server)
                                response = await client.call_tool(tool)
                                if self.prompt_mode_flag:
                                    response = {"role": "user", "content": response}
                                else:
                                    # Create a message in Assistant role with tool_calls to satisfy API requirement
                                    # This ensures we have a tool_calls message before adding a tool role message
                                    assistant_message = {
                                        "role": "assistant",
                                        "content": None,
                                        "tool_calls": [
                                            {
                                                "id": tool.id,
                                                "type": "function",
                                                "function": {
                                                    "name": tool.name,
                                                    "arguments": json.dumps(tool.args)
                                                }
                                            }
                                        ]
                                    }
                                    # Add the assistant message with tool_calls
                                    messages.append(assistant_message)
                                    
                                    response = {"role": "tool", "tool_call_id": tool.id, "content": response}
                            logger.info(f"End calling tool: {tool.name}")
                            logger.debug(f"Call of '{tool}' completed with response: {response}")
                        except Exception as e:
                            logger.error(f"Error calling tool '{tool.name}': {e}")
                            response = {
                                "role": "user",
                                "content": f"Error calling tool '{tool.name}': {e}",
                            }
                        tools_response.append(response)
                    
                    messages.extend(tools_response)
                    
                    # Stage C: Call the LLM again with the tool responses.
                    token_stream = chat_func(messages, self._system)
                    complete_response = ""
                    
                    async for token in token_stream:
                        yield token
                        complete_response += token
                        
                        
            # MCP Plus disabled
            else:
                # Get token stream from LLM
                token_stream = chat_func(messages, self._system)
                complete_response = ""
                
                async for token in token_stream:
                    yield token
                    complete_response += token

            # Store complete response
            self._add_message(complete_response, "assistant")

        return chat_with_memory
    
    async def process_json_stream(self, stream: AsyncIterator[str]) -> AsyncIterator[str | Dict[str, Any]]:
        """
        Process the JSON stream from the LLM and handle tool calls.

        Args:
            stream: AsyncIterator[str] - The stream of JSON data

        Returns:
            AsyncIterator[str | Dict[str, Any]] - if JSON is detected, yield it
            else yield the token
        """
        potential_json = False
        full_json_tokens = ""
        async for token in stream:
            if '{' in token:
                potential_json = True
                full_json_tokens += token
            if potential_json:
                json_data = self._json_detector.process_chunk(token)
                full_json_tokens += token
                if json_data:
                    logger.debug(f"Detected JSON: {json_data}")
                    yield json_data
                    potential_json = False
            else:
                yield token
        logger.debug(f"Full JSON tokens: {full_json_tokens}")
    
    def _process_tool_from_dict_list(self, data: List[Dict[str, Any]]) -> List[CallableTool]:
        """Process the tool data from the LLM response.
        
        Args:
            data: List[Dict[str, Any]] - The list of dictionaries containing tool data
        
        Returns:
            List[CallableTool] - List of CallableTool objects
        """
        tools = []
        for item in data:
            server = item.get("mcp_server", None)
            tool = item.get("tool", None)
            arguments = item.get("arguments", None)
            if all([server, tool, arguments]):
                tools.append(
                    CallableTool(
                        name=tool,
                        server=server,
                        args=json.loads(arguments),
                    )
                )
        return tools

    async def chat(self, input_data: BatchInput) -> AsyncIterator[SentenceOutput]:
        """Placeholder chat method that will be replaced at runtime"""
        return self.chat(input_data)

    def reset_interrupt(self) -> None:
        """
        Reset the interrupt handled flag for a new conversation.
        """
        self._interrupt_handled = False

    def start_group_conversation(
        self, human_name: str, ai_participants: List[str]
    ) -> None:
        """
        Start a group conversation by adding a system message that informs the AI about
        the conversation participants.

        Args:
            human_name: str - Name of the human participant
            ai_participants: List[str] - Names of other AI participants in the conversation
        """
        other_ais = ", ".join(name for name in ai_participants)

        prompt_name = self._tool_prompts.get("group_conversation_prompt", "")

        if not prompt_name:
            logger.warning(
                "No group conversation prompt found. Continuing without group context."
            )
            return

        group_context = prompt_loader.load_util(prompt_name).format(
            human_name=human_name, other_ais=other_ais
        )

        self._memory.append({"role": "user", "content": group_context})

        logger.debug(f"Added group conversation context: '''{group_context}'''")
