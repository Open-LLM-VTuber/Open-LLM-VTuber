import io
import json
import sys
import zipfile
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.open_llm_vtuber import extensions


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(extensions, 'STORE', tmp_path / 'extensions.json')
    monkeypatch.setattr('src.open_llm_vtuber.broadcast.LIVE', False)
    app = FastAPI()
    app.include_router(extensions.init_extension_routes(SimpleNamespace()))
    with TestClient(app) as client:
        yield client


def archive(files):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as out:
        for name, content in files.items():
            out.writestr(name, content)
    return data.getvalue()


def test_skill_install_enable_prompt_remove(client):
    text = '---\nname: writing\ndescription: 写作技能\n---\n先列大纲。'
    assert client.post('/api/extensions/install?filename=SKILL.md', content=text.encode()).status_code == 200
    assert extensions.skill_context() == ''
    assert client.patch('/api/extensions/writing', json={'enabled': True}).status_code == 200
    assert '先列大纲' in extensions.skill_context()
    assert client.get('/api/extensions').json()['items'][0]['enabled'] is True
    assert client.post('/api/extensions/install?filename=SKILL.md', content=text.encode()).status_code == 409
    assert client.delete('/api/extensions/writing').status_code == 200
    assert extensions.skill_context() == ''


def test_plugin_config_and_archive_boundary(client):
    content = archive({'plugin.json': json.dumps({'id': 'bundle', 'mcpServers': {'bundle-server': {'command': 'python', 'args': ['server.py'], 'env': {'TOKEN': 'secret'}}}}), 'skills/hello/SKILL.md': '# Hello'})
    assert client.post('/api/extensions/install?filename=bundle.zip', content=content).status_code == 200
    assert 'secret' not in client.get('/api/extensions').text
    assert client.patch('/api/extensions/bundle', json={'enabled': True}).status_code == 200
    assert extensions.managed_servers()['bundle-server']['command'] == 'python'
    from src.open_llm_vtuber.mcpp.server_registry import ServerRegistry
    assert ServerRegistry().get_server('bundle-server') is not None
    bad = archive({'../SKILL.md': 'unsafe'})
    assert client.post('/api/extensions/install?filename=bad.zip', content=bad).status_code == 400
    assert client.post('/api/extensions/install?filename=bad.zip', content=b'broken').status_code == 400
    assert client.post('/api/extensions/mcp', json={'id': 'remote', 'config': {'url': 'https://example.com'}}).status_code == 400
    assert client.get('/api/extensions', headers={'Origin': 'https://example.com'}).status_code == 403


def test_real_stdio_connection(client, tmp_path):
    server = tmp_path / 'server.py'
    server.write_text('from mcp.server.fastmcp import FastMCP\nmcp = FastMCP("test")\n@mcp.tool()\ndef echo(text: str) -> str:\n    return text\nmcp.run()\n')
    response = client.post('/api/extensions/mcp', json={'id': 'test-stdio', 'config': {'command': sys.executable, 'args': [str(server)]}})
    assert response.status_code == 200
    response = client.post('/api/extensions/test-stdio/test')
    assert response.status_code == 200, response.text
    assert response.json()['results'][0]['tools'] == ['echo']
