uv run python scripts/run_with_services.py


cd frontend
npm run dev
npm run build

npm --prefix frontend run build
uv run python scripts/run_with_services.py


uv run python scripts/run_bilibili_live.py

#tmp


uv run --extra bilibili python scripts/run_with_services.py

### Agent runtime (LangChain / LangGraph)

`basic_memory_agent` retains its existing configuration name and `AgentInterface`.
OpenAI-compatible providers (including Ollama) and Claude now use LangChain chat
models. A shared LangGraph `model → tools → model` flow handles streaming text,
MCP progress, tool results, prompt-based fallback and inline stage commands.
Existing history, retrieval, interruption and speech processing remain in the
agent pipeline. Hosted Letta/Hume agents and the optional legacy template / local
llama.cpp providers keep their provider-specific implementations.

Set `character_config.agent_config.agent_settings.basic_memory_agent.max_tool_rounds`
(default `8`, range `1–100`) to bound tool execution per turn. Old character
configurations work without this field. The runtime supports Python 3.10–3.12;
stream events are passed explicitly for Python 3.10 compatibility. Graph state is
per turn; existing application history remains the source of conversation memory,
without an additional checkpoint database.

Install with `uv sync` (include `--extra control` / `--extra bilibili` when needed).
`pyproject.toml`, `uv.lock`, and the generated `requirements.txt` include the
LangChain integrations and LangGraph runtime. Model connection errors propagate
to the conversation error handler instead of being stored as assistant speech.
