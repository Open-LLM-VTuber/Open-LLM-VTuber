"""LangChain chat model adapter retaining the application's streaming contract."""

from contextlib import aclosing
from typing import AsyncIterator

from langchain_core.messages import AIMessageChunk, SystemMessage, convert_to_messages
from langchain_openai import ChatOpenAI
from openai import APIError

from .stateless_llm_interface import StatelessLLMInterface
from ...mcpp.types import ToolCallObject


class AsyncLLM(StatelessLLMInterface):
    """OpenAI-compatible providers share LangChain message and tool handling."""

    def __init__(
        self,
        model: str,
        base_url: str,
        llm_api_key: str = "z",
        organization_id: str = "z",
        project_id: str = "z",
        temperature: float = 1.0,
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.support_tools = True
        self.chat_model = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=llm_api_key or "z",
            organization=organization_id,
            temperature=temperature,
            default_headers={"OpenAI-Project": project_id} if project_id else None,
            stream_usage=False,
        )

    async def chat_completion(self, messages, system=None, tools=None) -> AsyncIterator:
        request = convert_to_messages(
            [
                {k: v for k, v in message.items() if k not in ("name", "avatar")}
                for message in messages
            ]
        )
        if system:
            request.insert(0, SystemMessage(content=system))
        model = self.chat_model
        if tools and self.support_tools:
            model = model.bind_tools(tools)
        accumulated = None
        try:
            async with aclosing(model.astream(request)) as stream:
                async for chunk in stream:
                    if not isinstance(chunk, AIMessageChunk):
                        continue
                    accumulated = chunk if accumulated is None else accumulated + chunk
                    content = chunk.content
                    if isinstance(content, str):
                        if content:
                            yield content
                    else:
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                yield block.get("text", "")
            if accumulated is not None and accumulated.tool_call_chunks:
                # Preserve raw JSON so malformed calls reach ToolExecutor's error handling.
                yield [
                    ToolCallObject.from_dict(
                        {
                            "id": call["id"],
                            "type": "function",
                            "index": call["index"] or 0,
                            "function": {
                                "name": call["name"],
                                "arguments": call["args"],
                            },
                        }
                    )
                    for call in accumulated.tool_call_chunks
                ]
        except APIError as exc:
            if tools and "does not support tools" in str(exc):
                self.support_tools = False
                yield "__API_NOT_SUPPORT_TOOLS__"
            else:
                raise
