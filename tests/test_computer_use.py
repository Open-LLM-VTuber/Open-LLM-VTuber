import asyncio
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.open_llm_vtuber.computer_use import service
from src.open_llm_vtuber.computer_use.access import LOCAL_CONTROL, PASSIVE_TURN
from src.open_llm_vtuber.computer_use.browser import Browser
from src.open_llm_vtuber.mcpp.tool_executor import ToolExecutor
from src.open_llm_vtuber.mcpp.tool_manager import ToolManager


@pytest.fixture
def control(tmp_path, monkeypatch):
    instance = service.ControlService()
    monkeypatch.setattr(service, 'STORE', tmp_path / 'control.json')
    monkeypatch.setattr(service, 'CONTROL', instance)
    monkeypatch.setattr('src.open_llm_vtuber.broadcast.LIVE', False)
    return instance


def test_disabled_remote_passive_and_live_cannot_execute(control, monkeypatch):
    async def run():
        control.browser.execute = AsyncMock(return_value=({}, []))
        with pytest.raises(PermissionError):
            await control.execute('browser', {'action': 'snapshot'})
        token = LOCAL_CONTROL.set(True)
        try:
            with pytest.raises(PermissionError):
                await control.execute('browser', {'action': 'snapshot'})
            await control.update({'browser': True})
            passive = PASSIVE_TURN.set(True)
            with pytest.raises(PermissionError):
                await control.execute('browser', {'action': 'snapshot'})
            PASSIVE_TURN.reset(passive)
            monkeypatch.setattr('src.open_llm_vtuber.broadcast.LIVE', True)
            with pytest.raises(PermissionError):
                await control.execute('browser', {'action': 'snapshot'})
            control.browser.execute.assert_not_called()
        finally:
            LOCAL_CONTROL.reset(token)
    asyncio.run(run())


def test_stop_cancels_active_and_queued_work(control):
    async def run():
        started = asyncio.Event()
        async def blocked(*args, **kwargs):
            started.set()
            await asyncio.Event().wait()
        control.browser.execute = AsyncMock(side_effect=blocked)
        control.browser.close = AsyncMock()
        token = LOCAL_CONTROL.set(True)
        try:
            await control.update({'browser': True})
            active = asyncio.create_task(control.execute('browser', {'action': 'snapshot'}))
            await started.wait()
            queued = asyncio.create_task(control.execute('browser', {'action': 'snapshot'}))
            await asyncio.sleep(0)
            await control.update({'browser': False, 'computer': False, 'stopped': True})
            with pytest.raises(RuntimeError, match='停止'):
                await active
            with pytest.raises(PermissionError):
                await queued
            assert control.browser.execute.await_count == 1
            control.browser.close.assert_awaited_once()
            assert control.status()['events'][0]['status'] == 'stopped'
        finally:
            LOCAL_CONTROL.reset(token)
    asyncio.run(run())


def test_control_api_origin_and_persistence(control):
    app = FastAPI()
    app.include_router(service.init_control_routes())
    with TestClient(app) as client:
        assert client.get('/api/control').json()['settings']['browser'] is False
        assert client.patch('/api/control', json={'browser': True}, headers={'Origin': 'https://evil.example'}).status_code == 403
        assert client.patch('/api/control', json={'browser': True}, headers={'Host': 'evil.example'}).status_code == 403
        assert client.patch('/api/control', json={'browser': 'true'}).status_code == 422
        assert client.patch('/api/control', json={'browser': True}).status_code == 200
        assert service.ControlService().settings['browser'] is True
        assert client.post('/api/control/stop').json()['settings'] == {'browser': False, 'computer': False, 'stopped': True}
        assert client.post('/api/control/probe/browser').status_code == 422


def test_multimodal_results_keep_tool_pairing(control):
    async def run():
        encoded = base64.b64encode(b'test image').decode()
        control.execute = AsyncMock(return_value=({'width': 1280}, [
            {'type': 'image', 'mimeType': 'image/jpeg', 'data': encoded}]))
        executor = ToolExecutor(None, ToolManager())
        calls = [{'id': 'one', 'name': 'local_computer', 'input': {'action': 'screenshot'}},
                 {'id': 'two', 'name': 'local_computer', 'input': {'action': 'screenshot'}}]
        updates = [u async for u in executor.execute_tools(calls, 'OpenAI')]
        results = updates[-1]['results']
        assert [r['role'] for r in results] == ['tool', 'tool', 'user']
        assert [r['tool_call_id'] for r in results[:2]] == ['one', 'two']
        assert results[-1]['content'][1]['image_url']['url'].endswith(encoded)
        assert encoded not in str(updates[:-1])  # Don't broadcast screenshots into status/chat logs.
        claude = [u async for u in executor.execute_tools(calls[:1], 'Claude')]
        assert claude[-1]['results'][0]['content'][1]['source']['data'] == encoded
        invalid = await executor.run_single_tool('local_browser', 'bad', {'action': 'shell'})
        assert invalid[0] is True
    asyncio.run(run())


@pytest.fixture
def website():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = '''<!doctype html><html><head><title>Control test</title></head><body>
            <h1>Local form</h1><label>Your note<input id="note"></label>
            <button onclick="document.querySelector('#result').textContent=document.querySelector('#note').value">Save note</button>
            <p id="result" role="status"></p></body></html>'''.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    server.server_close()
    thread.join()


def test_real_browser_actions_through_model_executor(control, website, tmp_path):
    pytest.importorskip('playwright.async_api')
    async def run():
        control.browser = Browser(profile=tmp_path / 'profile', headless=True)
        token = LOCAL_CONTROL.set(True)
        await control.update({'browser': True})
        executor = ToolExecutor(None, ToolManager())
        async def call(arguments):
            error, text, _, images = await executor.run_single_tool('local_browser', 'test', arguments)
            assert not error, text
            return text, images
        try:
            text, _ = await call({'action': 'navigate', 'url': website})
            assert 'Your note' in text
            await call({'action': 'fill', 'role': 'textbox', 'name': 'Your note', 'text': '浏览器真实执行成功'})
            text, _ = await call({'action': 'click', 'role': 'button', 'name': 'Save note'})
            assert '浏览器真实执行成功' in text
            assert await control.browser.page.locator('#result').inner_text() == '浏览器真实执行成功'
            _, images = await call({'action': 'screenshot'})
            assert base64.b64decode(images[0]['data']).startswith(b'\xff\xd8')
            error, text, _, _ = await executor.run_single_tool('local_browser', 'bad', {'action': 'navigate', 'url': 'file:///etc/passwd'})
            assert error and 'http/https' in text
            await control.update({'browser': False})
            assert control.browser.context is None
            error, _, _, _ = await executor.run_single_tool('local_browser', 'off', {'action': 'snapshot'})
            assert error
        finally:
            await control.close()
            LOCAL_CONTROL.reset(token)
    asyncio.run(run())
