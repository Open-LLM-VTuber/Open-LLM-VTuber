from typing import AsyncIterator, List, Dict, Any, Callable, Literal
from loguru import logger

from .agent_interface import AgentInterface
from ..output_types import SentenceOutput, DisplayText, Actions
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
            interrupt_method: Literal["system", "user"] = "user",
            faq_handler=None,
            character_avatar: str = None,
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
            faq_handler: FAQ处理器实例
            character_avatar: 角色头像路径
        """
        super().__init__()
        self._memory = []
        self._live2d_model = live2d_model
        self._tts_preprocessor_config = tts_preprocessor_config
        self._faster_first_response = faster_first_response
        self._segment_method = segment_method
        self.interrupt_method = interrupt_method
        # Flag to ensure a single interrupt handling per conversation
        self._interrupt_handled = False
        self._faq_handler = faq_handler
        self._character_avatar = character_avatar
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
            self, chat_func: Callable[[List[Dict[str, Any]], str], AsyncIterator[str]]
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
            # 从输入中获取用户查询文本
            user_query = ""
            for text_data in input_data.texts:
                if text_data.source == TextSource.INPUT:
                    user_query += text_data.content + " "
            user_query = user_query.strip()

            # 处理FAQ匹配（如果启用）
            direct_answer = None
            enhanced_prompt = None
            similarity = 0.0

            if self._faq_handler and user_query:
                try:
                    direct_answer, enhanced_prompt, similarity = await self._faq_handler.process_query(user_query)
                    logger.info(
                        f"FAQ匹配结果: 直接回答={bool(direct_answer)}, 增强提示={bool(enhanced_prompt)}, 相似度={similarity:.2f}")
                except Exception as e:
                    logger.error(f"处理FAQ匹配时出错: {e}")

            # 高匹配度：直接返回FAQ答案
            if direct_answer:
                logger.info(f"从FAQ直接返回答案 (匹配度: {similarity:.2f})")
                # 将答案作为完整响应添加到记忆中
                self._add_message(direct_answer, "assistant")
                # 直接产生答案的token流
                for char in direct_answer:
                    yield char
                return

            # 中等匹配度：使用增强提示
            if enhanced_prompt:
                logger.info(f"使用FAQ增强提示 (匹配度: {similarity:.2f})")
                # 创建带有增强提示的系统消息
                enhanced_system = f"{self._system}\n\n{enhanced_prompt}"
                messages = self._to_messages(input_data)

                # 带增强提示的token流
                token_stream = chat_func(messages, enhanced_system)
            else:
                # 低匹配度或未启用FAQ：正常生成回复
                logger.info(f"常规LLM回复 (匹配度: {similarity:.2f})")
                messages = self._to_messages(input_data)
                token_stream = chat_func(messages, self._system)

            # 处理LLM生成的token流
            complete_response = ""
            async for token in token_stream:
                yield token
                complete_response += token

            # 存储完整响应
            self._add_message(complete_response, "assistant")

        return chat_with_memory

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

        # Load and format the group conversation prompt
        group_context = prompt_loader.load_util("group_conversation_prompt").format(
            human_name=human_name, other_ais=other_ais
        )

        self._memory.append({"role": "user", "content": group_context})

        logger.debug(f"Added group conversation context: '''{group_context}'''")