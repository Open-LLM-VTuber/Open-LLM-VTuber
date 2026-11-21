import asyncio
import unittest

from langchain_core.messages import AIMessageChunk

from src.open_llm_vtuber.agent.conversation_graph import ConversationGraph
from src.open_llm_vtuber.agent.stateless_llm.openai_compatible_llm import AsyncLLM
from src.open_llm_vtuber.mcpp.types import ToolCallObject, ToolCallFunctionObject


def call():
    return ToolCallObject(
        id="call_1", function=ToolCallFunctionObject(name="lookup", arguments="{}")
    )


class Model:
    support_tools = True

    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.closed = 0

    async def chat_completion(self, messages, system, **kwargs):
        self.requests.append((list(messages), system, kwargs))
        try:
            for event in next(self.responses):
                yield event
        finally:
            self.closed += 1


class Executor:
    async def execute_tools(self, calls, caller_mode):
        yield {"type": "tool_status", "status": "running"}
        yield {
            "type": "final_tool_results",
            "results": [{"role": "tool", "tool_call_id": "call_1", "content": "found"}],
        }


class GraphTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, model, tools=None, executor=None, limit=8):
        memory = []
        graph = ConversationGraph(
            model,
            "system",
            tools or [],
            executor,
            lambda text, role: memory.append((role, text)),
            max_tool_rounds=limit,
        )
        events = [
            event async for event in graph.stream([{"role": "user", "content": "hi"}])
        ]
        return events, memory

    async def test_text_stream_and_memory(self):
        model = Model([["Hello", " world."]])
        events, memory = await self.collect(model)
        self.assertEqual("".join(events), "Hello world.")
        self.assertEqual(memory, [("assistant", "Hello world.")])
        self.assertEqual(model.closed, 1)

    async def test_tools_and_progress(self):
        model = Model([[[call()]], ["Result."]])
        events, _ = await self.collect(
            model, [{"type": "function", "function": {"name": "lookup"}}], Executor()
        )
        self.assertEqual(events[0]["type"], "tool_status")
        self.assertEqual(model.requests[1][0][-1]["role"], "tool")
        self.assertEqual(model.requests[1][0][-2]["tool_calls"][0]["id"], "call_1")

    async def test_native_tool_fallback(self):
        model = Model([["__API_NOT_SUPPORT_TOOLS__"], ["Fallback."]])
        events, _ = await self.collect(
            model, [{"type": "function", "function": {"name": "lookup"}}], Executor()
        )
        self.assertEqual("".join(events), "Fallback.")
        self.assertNotIn("tools", model.requests[1][2])

    async def test_round_limit(self):
        model = Model([[[call()]], [[call()]]])
        with self.assertRaisesRegex(RuntimeError, "max_tool_rounds"):
            await self.collect(
                model,
                [{"type": "function", "function": {"name": "lookup"}}],
                Executor(),
                limit=1,
            )

    async def test_adapter_merges_parallel_tool_chunks(self):
        class ChatModel:
            def bind_tools(self, tools):
                return self

            async def astream(self, messages):
                yield AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {"name": "lookup", "args": '{"q":', "id": "a", "index": 0},
                        {"name": "lookup", "args": "{}", "id": "b", "index": 1},
                    ],
                )
                yield AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {"name": None, "args": '"hi"}', "id": None, "index": 0},
                    ],
                )

        llm = AsyncLLM("test", "http://localhost:9999/v1")
        llm.chat_model = ChatModel()
        outputs = [x async for x in llm.chat_completion([], "system", tools=[{}])]
        self.assertEqual(len(outputs[0]), 2)
        self.assertEqual(outputs[0][0].function.arguments, '{"q":"hi"}')

    async def test_inline_stage_is_hidden_and_executed_once(self):
        model = Model(
            [
                ["Hello [local_", 'stage:{"operation":"wave"}]world.'],
                ['[local_stage:{"operation":"wave"}]Done.'],
            ]
        )
        events, _ = await self.collect(
            model,
            [{"type": "function", "function": {"name": "local_stage"}}],
            Executor(),
        )
        visible = "".join(e for e in events if isinstance(e, str))
        self.assertEqual(visible, "Hello world.Done.")
        self.assertEqual(len(model.requests), 2)

    async def test_prompt_tools_return_to_model(self):
        class PromptExecutor(Executor):
            def process_tool_from_prompt_json(self, data):
                return [{"id": "call_1", "name": "lookup", "args": {}}]

        model = Model(
            [['{"mcp_server":"test","tool":"lookup","arguments":{}}'], ["Done."]]
        )
        model.support_tools = False
        await self.collect(
            model,
            [{"type": "function", "function": {"name": "lookup"}}],
            PromptExecutor(),
        )
        self.assertEqual(model.requests[1][0][-1], {"role": "user", "content": "found"})

    async def test_old_configuration_defaults_and_limits(self):
        from src.open_llm_vtuber.config_manager.agent import BasicMemoryAgentConfig
        from pydantic import ValidationError

        self.assertEqual(
            BasicMemoryAgentConfig(llm_provider="claude_llm").max_tool_rounds, 8
        )
        with self.assertRaises(ValidationError):
            BasicMemoryAgentConfig(llm_provider="claude_llm", max_tool_rounds=0)

    async def test_model_cancellation_closes_provider(self):
        closed = asyncio.Event()
        started = asyncio.Event()

        class WaitingModel:
            async def chat_completion(self, messages, system, **kwargs):
                try:
                    started.set()
                    await asyncio.Event().wait()
                    yield "unreachable"
                finally:
                    closed.set()

        task = asyncio.create_task(self.collect(WaitingModel()))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(closed.is_set())


if __name__ == "__main__":
    unittest.main()
