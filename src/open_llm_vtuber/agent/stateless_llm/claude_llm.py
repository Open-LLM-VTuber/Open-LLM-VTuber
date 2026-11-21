"""Anthropic integration using the same LangChain streaming contract as OpenAI."""

from langchain_anthropic import ChatAnthropic

from .openai_compatible_llm import AsyncLLM as LangChainLLM


class AsyncLLM(LangChainLLM):
    def __init__(
        self,
        model="claude-3-haiku-latest",
        base_url=None,
        llm_api_key=None,
        system=None,
    ):
        self.model = model
        self.base_url = base_url
        self.system = system
        self.support_tools = True
        self.chat_model = ChatAnthropic(
            model_name=model,
            api_key=llm_api_key,
            base_url=base_url,
            max_tokens=1024,
        )

    async def chat_completion(self, messages, system=None, tools=None):
        async for event in super().chat_completion(
            messages, system or self.system, tools
        ):
            yield event
