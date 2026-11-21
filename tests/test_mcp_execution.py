"""Exercise actual stdio execution and preserve evidence returned to the model."""
import asyncio
import json
import sys
from unittest.mock import AsyncMock

from mcp.types import CallToolResult, TextContent

from src.open_llm_vtuber.mcpp.mcp_client import MCPClient
from src.open_llm_vtuber.mcpp.server_registry import ServerRegistry
from src.open_llm_vtuber.mcpp.tool_executor import ToolExecutor
from src.open_llm_vtuber.mcpp.tool_manager import ToolManager
from src.open_llm_vtuber.mcpp.types import FormattedTool, MCPServer


def test_real_stdio_write_and_read(tmp_path, monkeypatch):
    monkeypatch.setattr('src.open_llm_vtuber.broadcast.LIVE', False)
    server = tmp_path / 'server.py'
    server.write_text('''from pathlib import Path
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("workspace-test")
@mcp.tool()
def write_note(text: str) -> str:
    Path("note.txt").write_text(text, encoding="utf-8")
    return "saved"
@mcp.tool()
def read_note() -> str:
    return Path("note.txt").read_text(encoding="utf-8")
mcp.run()
''')
    registry = ServerRegistry()
    registry.servers = {'test': MCPServer(name='test', command=sys.executable,
                                         args=[str(server)], cwd=str(tmp_path))}

    async def run():
        async with MCPClient(registry) as client:
            discovered = await client.list_tools('test')
            manager = ToolManager(initial_tools_dict={
                t.name: FormattedTool(input_schema=t.inputSchema, related_server='test')
                for t in discovered
            })
            executor = ToolExecutor(client, manager)
            for name, args, expected in [('write_note', {'text': '真实写入验证'}, 'saved'),
                                         ('read_note', {}, '真实写入验证')]:
                updates = [u async for u in executor.execute_tools(
                    [{'id': name, 'name': name, 'input': args}], 'OpenAI')]
                assert updates[-2]['status'] == 'completed'
                assert expected in updates[-1]['results'][0]['content']
    asyncio.run(run())
    assert (tmp_path / 'note.txt').read_text() == '真实写入验证'


def test_multiblock_structured_and_error_results(monkeypatch):
    monkeypatch.setattr('src.open_llm_vtuber.broadcast.LIVE', False)

    async def run():
        client = MCPClient(ServerRegistry())
        session = AsyncMock()
        client.active_sessions['test'] = session
        executor = ToolExecutor(client, ToolManager(initial_tools_dict={
            'report': FormattedTool(input_schema={}, related_server='test')}))
        session.call_tool.return_value = CallToolResult(
            content=[TextContent(type='text', text='第一段'), TextContent(type='text', text='第二段')],
            structuredContent={'artifact': 'note.txt'}, isError=False)
        error, text, _, _ = await executor.run_single_tool('report', '1', {})
        assert not error
        assert '第一段\n第二段' in text
        assert json.dumps({'artifact': 'note.txt'}) in text
        session.call_tool.return_value = CallToolResult(
            content=[TextContent(type='text', text='失败原因'), TextContent(type='text', text='修复建议')],
            isError=True)
        updates = [u async for u in executor.execute_tools(
            [{'id': '2', 'name': 'report', 'input': {}}], 'Claude')]
        assert updates[-2]['status'] == 'error'
        result = updates[-1]['results'][0]
        assert result['is_error'] is True
        assert result['content'] == '失败原因\n修复建议'
    asyncio.run(run())


def test_prompt_arguments_accept_objects_and_json_strings():
    executor = ToolExecutor(None, ToolManager())
    for arguments in ({}, '{}', {'text': 'hello'}, '{"text": "hello"}'):
        calls = executor.process_tool_from_prompt_json([
            {'mcp_server': 'test', 'tool': 'echo', 'arguments': arguments}])
        assert len(calls) == 1
        assert isinstance(calls[0]['args'], dict)
    assert executor.process_tool_from_prompt_json([
        {'mcp_server': 'test', 'tool': 'echo', 'arguments': '[]'}]) == []
