"""Bounded LangGraph conversation flow, shared by all stateless providers.

Memory remains owned by AgentInterface; graph state belongs to a single turn.
Custom streaming carries text and existing MCP progress events to the TTS pipeline.
"""

import asyncio
import json
from contextlib import aclosing
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from .stage_stream import StageStream
from ..mcpp.json_detector import StreamJSONDetector
from ..mcpp.types import ToolCallObject, ToolCallFunctionObject


class TurnState(TypedDict):
    messages: list[dict[str, Any]]
    calls: list
    rounds: int
    prompt_mode: bool
    seen_inline: set[str]
    retry: bool
    emit: Any


class ConversationGraph:
    def __init__(
        self, llm, system, tools, executor, remember, *, prompt="", max_tool_rounds=8
    ):
        self.llm = llm
        self.system = system
        self.tools = tools
        self.executor = executor
        self.remember = remember
        self.prompt = prompt
        self.max_tool_rounds = max_tool_rounds
        graph = StateGraph(TurnState)
        graph.add_node("model", self._model)
        graph.add_node("tools", self._tools)
        graph.add_edge(START, "model")
        graph.add_conditional_edges("model", self._route)
        graph.add_edge("tools", "model")
        self.graph = graph.compile()

    def _route(self, state):
        if state.get("retry"):
            return "model"
        if state["calls"]:
            if state["rounds"] >= self.max_tool_rounds:
                raise RuntimeError("Agent exceeded max_tool_rounds")
            return "tools"
        return END

    async def _model(self, state: TurnState):
        writer = state["emit"]
        prompt_mode = state["prompt_mode"]
        system = self.system
        if prompt_mode and self.prompt:
            system += "\n\n" + self.prompt
        detector = StreamJSONDetector() if prompt_mode else None
        stage = StageStream()
        text = ""
        calls = []
        messages = list(state["messages"])
        seen_inline = set(state["seen_inline"])
        kwargs = {"tools": self.tools} if self.tools and not prompt_mode else {}
        async with aclosing(
            self.llm.chat_completion(messages, system, **kwargs)
        ) as stream:
            async for event in stream:
                if event == "__API_NOT_SUPPORT_TOOLS__":
                    # Retry once without native tools; subsequent turns reuse provider capability.
                    return {"prompt_mode": True, "calls": [], "retry": True}
                if isinstance(event, list):
                    calls.extend(event)
                    continue
                if not isinstance(event, str):
                    continue
                event = stage.feed(event)
                text += event
                if event:
                    writer(event)
                if detector and (detected := detector.process_chunk(event)):
                    calls = self.executor.process_tool_from_prompt_json(
                        detected if isinstance(detected, list) else [detected]
                    )
                    if calls:
                        break
        tail = stage.finish()
        if tail:
            text += tail
            writer(tail)
        if self.tools and self.executor and not prompt_mode:
            stage_enabled = any(
                t.get("function", {}).get("name") == "local_stage" for t in self.tools
            )
            if stage_enabled:
                for args in stage.arguments:
                    encoded = json.dumps(args, ensure_ascii=False, sort_keys=True)
                    if encoded in seen_inline or len(seen_inline) >= 8:
                        continue
                    seen_inline.add(encoded)
                    calls.append(
                        ToolCallObject(
                            id=f"call_{uuid4().hex}",
                            function=ToolCallFunctionObject(
                                name="local_stage", arguments=encoded
                            ),
                        )
                    )
        if text:
            self.remember(text, "assistant")
        if calls and not prompt_mode:
            messages.append(
                {
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {
                                "name": c.function.name,
                                "arguments": c.function.arguments,
                            },
                        }
                        for c in calls
                    ],
                }
            )
        elif calls:
            messages.append({"role": "assistant", "content": text})
        return {
            "messages": messages,
            "calls": calls,
            "seen_inline": seen_inline,
            "retry": False,
        }

    async def _tools(self, state: TurnState):
        writer = state["emit"]
        if self.executor is None:
            raise RuntimeError("Tool calls require a configured ToolExecutor")
        results = None
        mode = "Prompt" if state["prompt_mode"] else "OpenAI"
        async with aclosing(
            self.executor.execute_tools(state["calls"], caller_mode=mode)
        ) as stream:
            async for event in stream:
                if event.get("type") == "final_tool_results":
                    results = event.get("results", [])
                else:
                    writer(event)
        if not results:
            raise RuntimeError("ToolExecutor returned no tool results")
        messages = list(state["messages"])
        if state["prompt_mode"]:
            messages.append(
                {
                    "role": "user",
                    "content": "\n".join(str(r.get("content", "")) for r in results),
                }
            )
        else:
            messages.extend(results)
        return {"messages": messages, "rounds": state["rounds"] + 1, "calls": []}

    async def stream(self, messages):
        # Explicit writer avoids contextvars propagation requirements on Python 3.10.
        queue = asyncio.Queue()
        done = object()

        async def run():
            try:
                await self.graph.ainvoke(
                    {
                        "messages": list(messages),
                        "calls": [],
                        "rounds": 0,
                        "prompt_mode": bool(
                            self.tools and not getattr(self.llm, "support_tools", False)
                        ),
                        "seen_inline": set(),
                        "retry": False,
                        "emit": queue.put_nowait,
                    },
                    config={"recursion_limit": 2 * self.max_tool_rounds + 5},
                )
            finally:
                queue.put_nowait(done)

        task = asyncio.create_task(run())
        try:
            while True:
                event = await queue.get()
                if event is done:
                    break
                yield event
            await task
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
