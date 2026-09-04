import unittest

from openai.types.chat import ChatCompletionChunk

from open_llm_vtuber.agent.stateless_llm.openai_compatible_llm import AsyncLLM


class FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for chunk in self._chunks:
            yield chunk

    async def close(self):
        pass


class FakeCompletions:
    def __init__(self, chunks):
        self._chunks = chunks

    async def create(self, **_kwargs):
        return FakeStream(self._chunks)


class FakeClient:
    def __init__(self, chunks):
        self.chat = type("FakeChat", (), {"completions": FakeCompletions(chunks)})()


class OpenAICompatibleLLMTest(unittest.IsolatedAsyncioTestCase):
    async def test_stream_preserves_tool_call_extra_content(self):
        chunk = ChatCompletionChunk.model_validate(
            {
                "id": "completion-1",
                "created": 0,
                "model": "test-model",
                "object": "chat.completion.chunk",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "search",
                                        "arguments": "{}",
                                    },
                                    "extra_content": {
                                        "google": {
                                            "thought_signature": "encrypted-signature"
                                        }
                                    },
                                }
                            ]
                        },
                    }
                ],
            }
        )
        llm = object.__new__(AsyncLLM)
        llm.client = FakeClient([chunk])
        llm.model = "test-model"
        llm.temperature = 1.0
        llm.support_tools = True

        events = [event async for event in llm.chat_completion([], tools=[])]

        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0][0].extra_content,
            {"google": {"thought_signature": "encrypted-signature"}},
        )


if __name__ == "__main__":
    unittest.main()
