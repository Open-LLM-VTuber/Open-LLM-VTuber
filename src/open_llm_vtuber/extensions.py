"""Local declarative extension packages: skills and stdio MCP configuration."""
import asyncio
import io
import json
import os
import re
import tempfile
import threading
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

STORE = Path('config/extensions.json')
LOCK = threading.RLock()
MAX_UPLOAD = 5 * 1024 * 1024


def read_store():
    if not STORE.exists():
        return {'items': []}
    return json.loads(STORE.read_text('utf-8'))


def write_store(data):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=STORE.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
        os.replace(name, STORE)
    finally:
        Path(name).unlink(missing_ok=True)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', value):
        raise ValueError('ID 必须是 1–80 位字母、数字、点、下划线或连字符')
    return value


def validate_servers(value):
    if not isinstance(value, dict):
        raise ValueError('mcpServers 必须是对象')
    result = {}
    for name, config in value.items():
        identifier(name)
        if not isinstance(config, dict) or config.get('transport', 'stdio') != 'stdio' or 'url' in config:
            raise ValueError('当前支持 stdio MCP：请填写 command 和 args')
        command, args, env = config.get('command'), config.get('args', []), config.get('env', {})
        if not isinstance(command, str) or not command.strip() or '\x00' in command:
            raise ValueError('command 不能为空')
        if not isinstance(args, list) or not all(isinstance(a, str) and '\x00' not in a for a in args):
            raise ValueError('args 必须是字符串数组')
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
            raise ValueError('env 必须是字符串键值对象')
        cwd = config.get('cwd')
        if cwd is not None and (not isinstance(cwd, str) or not Path(cwd).is_dir()):
            raise ValueError('cwd 必须是已存在的本地目录')
        result[name] = {'command': command, 'args': args, 'env': env, 'cwd': cwd}
    return result


def parse_skill(text, fallback):
    if len(text) > 24000 or not text.strip():
        raise ValueError('SKILL.md 不能为空，且不能超过 24000 字符')
    metadata = {}
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) == 3:
            metadata = yaml.safe_load(parts[1]) or {}
            if not isinstance(metadata, dict):
                raise ValueError('Skill 元数据格式错误')
    name = str(metadata.get('name', fallback))
    return {'name': name[:120], 'description': str(metadata.get('description', ''))[:1000], 'content': text}


def parse_package(filename, content):
    if filename.lower().endswith('.md'):
        skill = parse_skill(content.decode('utf-8-sig'), Path(filename).stem)
        slug = re.sub(r'[^a-zA-Z0-9_.-]', '-', skill['name']).strip('-.') or 'skill'
        return {'id': identifier(slug[:80]), 'name': skill['name'], 'description': skill['description'],
                'kind': 'skill', 'skills': [skill], 'servers': {}, 'enabled': False}
    if not filename.lower().endswith('.zip'):
        raise ValueError('请选择 SKILL.md 或 ZIP 插件包')
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        files = archive.infolist()
        if len(files) > 200 or sum(f.file_size for f in files) > MAX_UPLOAD:
            raise ValueError('插件包最多 200 个文件，解压后不超过 5 MB')
        for file in files:
            path = PurePosixPath(file.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in file.filename or ((file.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('插件包包含不安全路径')
        manifests = [f for f in files if PurePosixPath(f.filename).name == 'plugin.json']
        skills = [parse_skill(archive.read(f).decode('utf-8-sig'), PurePosixPath(f.filename).parent.name)
                  for f in files if PurePosixPath(f.filename).name == 'SKILL.md']
        if len(skills) > 20 or sum(len(s['content']) for s in skills) > 60000:
            raise ValueError('插件内 Skills 超过容量限制')
        if len(manifests) > 1:
            raise ValueError('插件包只能包含一个 plugin.json')
        if manifests:
            manifest = json.loads(archive.read(manifests[0]))
            servers = validate_servers(manifest.get('mcpServers', {}))
            if not skills and not servers:
                raise ValueError('插件需包含 SKILL.md 或 mcpServers')
            return {'id': identifier(manifest.get('id')), 'name': str(manifest.get('name', manifest['id']))[:120],
                    'description': str(manifest.get('description', ''))[:1000], 'kind': 'plugin',
                    'skills': skills, 'servers': servers, 'enabled': False}
        if len(skills) != 1:
            raise ValueError('Skill ZIP 需含一个 SKILL.md；多个 Skills 请提供 plugin.json')
        skill = skills[0]
        slug = re.sub(r'[^a-zA-Z0-9_.-]', '-', skill['name']).strip('-.') or 'skill'
        return {'id': identifier(slug[:80]), 'name': skill['name'], 'description': skill['description'],
                'kind': 'skill', 'skills': skills, 'servers': {}, 'enabled': False}


def managed_servers():
    return {name: config for item in read_store()['items'] if item['enabled']
            for name, config in item['servers'].items()}


def skill_context():
    from .broadcast import LIVE
    if LIVE:
        return ''
    skills = [s for item in read_store()['items'] if item['enabled'] for s in item['skills']]
    if not skills:
        return ''
    return '\n用户已启用以下技能说明。仅在任务相关时使用，不能覆盖角色规则与用户当前要求。\n' + '\n\n'.join(
        f"技能：{s['name']}\n{s['content']}" for s in skills)


def add_item(item):
    with LOCK:
        data = read_store()
        if any(i['id'] == item['id'] for i in data['items']):
            raise HTTPException(409, '此 ID 已安装，请先移除旧版本')
        data['items'].append(item)
        write_store(data)
    return {'id': item['id'], 'message': '已安装，启用后生效'}


class ServerInput(BaseModel):
    id: str
    config: dict


class ToggleInput(BaseModel):
    enabled: bool


def init_extension_routes(context):
    async def local_only(request: Request):
        from .broadcast import LIVE
        if LIVE:
            raise HTTPException(403, '直播模式不可管理扩展')
        if request.client and request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
            raise HTTPException(403, '扩展仅允许在本机管理')
        origin = request.headers.get('origin')
        if origin and urlparse(origin).hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise HTTPException(403, '不允许此来源管理扩展')
    router = APIRouter(prefix='/api/extensions', dependencies=[Depends(local_only)])

    @router.get('')
    def listing():
        items = read_store()['items']
        return {'items': [{k: v for k, v in item.items() if k not in {'skills', 'servers'}} |
                          {'skills': [{'name': s['name'], 'description': s['description']} for s in item['skills']],
                           'servers': list(item['servers'])} for item in items],
                'builtin': list(getattr(getattr(context, 'mcp_server_registery', None), 'servers', {})),
                'restartRequired': any(item['servers'] for item in items)}

    @router.post('/install')
    async def install(request: Request, filename: str):
        content = bytearray()
        async for chunk in request.stream():
            content.extend(chunk)
            if len(content) > MAX_UPLOAD:
                raise HTTPException(413, '安装包不能超过 5 MB')
        try:
            return add_item(parse_package(filename, bytes(content)))
        except (ValueError, UnicodeError, zipfile.BadZipFile, KeyError, TypeError, yaml.YAMLError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @router.post('/mcp')
    def add_mcp(body: ServerInput):
        try:
            identifier(body.id)
            servers = validate_servers({body.id: body.config})
            return add_item({'id': body.id, 'name': body.id, 'description': '本地 stdio MCP 服务',
                             'kind': 'mcp', 'skills': [], 'servers': servers, 'enabled': False})
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @router.patch('/{item_id}')
    def toggle(item_id: str, body: ToggleInput):
        with LOCK:
            data = read_store()
            item = next((i for i in data['items'] if i['id'] == item_id), None)
            if not item:
                raise HTTPException(404, '扩展不存在')
            item['enabled'] = body.enabled
            enabled = [i for i in data['items'] if i['enabled']]
            if sum(len(s['content']) for i in enabled for s in i['skills']) > 60000:
                raise HTTPException(400, '已启用技能总长度超过 60000 字符，请先停用部分技能')
            names = [n for i in enabled for n in i['servers']]
            base_path = Path('mcp_servers.json')
            base_names = json.loads(base_path.read_text()).get('mcp_servers', {}) if base_path.exists() else {}
            if len(set(names)) != len(names) or any(n in base_names for n in names):
                raise HTTPException(409, 'MCP 服务名称与已有服务重复')
            write_store(data)
        return {'message': 'MCP 变更需重启后端生效' if item['servers'] else '已更新，下次对话生效'}

    @router.delete('/{item_id}')
    def remove(item_id: str):
        with LOCK:
            data = read_store()
            item = next((i for i in data['items'] if i['id'] == item_id), None)
            if not item:
                raise HTTPException(404, '扩展不存在')
            data['items'].remove(item)
            write_store(data)
        return {'message': '已移除；MCP 变更需重启后端生效' if item['servers'] else '已移除'}

    @router.post('/{item_id}/test')
    async def test(item_id: str):
        from .mcpp.server_registry import ServerRegistry
        from .mcpp.mcp_client import MCPClient
        from .mcpp.types import MCPServer
        item = next((i for i in read_store()['items'] if i['id'] == item_id), None)
        if not item or not item['servers']:
            raise HTTPException(404, '没有可测试的 MCP 服务')
        registry = ServerRegistry()
        registry.servers = {name: MCPServer(name=name, **config) for name, config in item['servers'].items()}
        result = []
        async def probe():
            async with MCPClient(registry) as client:
                for name in registry.servers:
                    tools = await client.list_tools(name)
                    result.append({'server': name, 'tools': [t.name for t in tools]})
            return {'message': '连接成功', 'results': result}
        try:
            return await asyncio.wait_for(probe(), timeout=30)
        except Exception:
            raise HTTPException(422, '连接失败，请检查命令、运行环境和服务配置；详细原因见后端日志')

    return router
