"""Shared runtime gates, cancellation and local-only settings for control tools."""
import asyncio
from collections import deque
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from .access import LOCAL_CONTROL, PASSIVE_TURN, local_request
from .browser import Browser
from .desktop import Desktop, permissions

STORE = Path('config/control.json')


class ControlService:
    def __init__(self):
        self.browser = Browser()
        self.desktop = Desktop()
        self.lock = asyncio.Lock()
        self.generation = 0
        self.active = None
        self.events = deque(maxlen=30)
        self._settings = None

    @property
    def settings(self):
        if self._settings is None:
            defaults = {'computer': False, 'browser': False, 'stopped': False}
            try:
                saved = json.loads(STORE.read_text())
                defaults.update({k: v for k, v in saved.items() if k in defaults and isinstance(v, bool)})
            except (OSError, ValueError, AttributeError):
                pass
            self._settings = defaults
        return self._settings

    def persist(self):
        STORE.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=STORE.parent, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as out:
                json.dump(self.settings, out)
            os.replace(name, STORE)
        finally:
            Path(name).unlink(missing_ok=True)

    def check(self, kind, generation):
        from ..broadcast import LIVE
        if LIVE or PASSIVE_TURN.get() or not LOCAL_CONTROL.get():
            raise PermissionError('仅允许本机用户发起的对话使用电脑与浏览器控制；直播和主动闲聊不可使用')
        if self.settings['stopped'] or not self.settings[kind] or generation != self.generation:
            raise PermissionError('控制已停止或尚未启用，请在设置 → 电脑与浏览器中开启')

    def status(self):
        from ..broadcast import LIVE
        return {'settings': dict(self.settings), 'permissions': permissions(), 'live': LIVE,
                'browserInstalled': importlib.util.find_spec('playwright') is not None,
                'browserRunning': self.browser.context is not None,
                'running': self.active is not None,
                'events': list(self.events)}

    async def update(self, changes):
        # Invalidate in-flight and queued work before awaiting cleanup.
        self.generation += 1
        self.settings.update(changes)
        self.persist()
        if self.active:
            self.active.cancel()
        self.desktop.observed = False
        async with self.lock:
            if not self.settings['browser'] or self.settings['stopped']:
                await self.browser.close()
        return self.status()

    async def execute(self, kind, arguments):
        generation = self.generation
        self.check(kind, generation)
        action = arguments.get('action', '')
        payload = {k: v for k, v in arguments.items() if k != 'action' and v is not None}
        async with self.lock:
            self.check(kind, generation)
            cancelled = threading.Event()
            def check_desktop():
                if cancelled.is_set():
                    raise RuntimeError('操作已取消')
                self.check(kind, generation)
            async def run():
                if kind == 'browser':
                    return await self.browser.execute(action, **payload)
                return await asyncio.to_thread(self.desktop.execute, action,
                                               check_desktop, **payload)
            self.active = asyncio.create_task(run())
            status = 'completed'
            try:
                result = await asyncio.wait_for(self.active, timeout=35)
                self.check(kind, generation)
                return result
            except asyncio.CancelledError:
                status = 'stopped'
                # An external stop becomes a tool result; cancellation of the chat propagates.
                if generation == self.generation:
                    raise
                raise RuntimeError('用户已停止控制操作')
            except Exception:
                status = 'error'
                raise
            finally:
                cancelled.set()
                self.active = None
                self.events.appendleft({'kind': kind, 'action': action, 'status': status,
                                        'time': datetime.now(timezone.utc).isoformat()})

    async def close(self):
        self.generation += 1
        if self.active:
            self.active.cancel()
        async with self.lock:
            await self.browser.close()


CONTROL = ControlService()


class SettingsInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    computer: bool | None = None
    browser: bool | None = None


def init_control_routes():
    async def only_local(request: Request):
        from ..broadcast import LIVE
        if LIVE or not local_request(request):
            raise HTTPException(403, '仅允许本机管理控制能力，直播模式不可用')
    router = APIRouter(prefix='/api/control', dependencies=[Depends(only_local)])

    @router.get('')
    async def status():
        return CONTROL.status()

    @router.patch('')
    async def update(body: SettingsInput):
        changes = body.model_dump(exclude_none=True)
        if any(changes.values()):
            changes['stopped'] = False
        return await CONTROL.update(changes)

    @router.post('/stop')
    async def stop():
        return await CONTROL.update({'computer': False, 'browser': False, 'stopped': True})

    @router.post('/probe/{kind}')
    async def probe(kind: str):
        if kind not in {'computer', 'browser'}:
            raise HTTPException(404)
        token = LOCAL_CONTROL.set(True)
        try:
            result, _ = await CONTROL.execute(kind, {'action': 'screenshot' if kind == 'computer' else 'snapshot'})
            return {'message': '截图成功，屏幕录制权限可用' if kind == 'computer' else '专用浏览器已启动，可读取页面',
                    'result': result, 'state': CONTROL.status()}
        except Exception as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            LOCAL_CONTROL.reset(token)

    @router.post('/permissions/{kind}')
    async def open_permissions(kind: str):
        import subprocess
        import sys
        if sys.platform != 'darwin' or kind not in {'screen', 'accessibility'}:
            raise HTTPException(400, '不支持此权限设置')
        pane = 'Privacy_ScreenCapture' if kind == 'screen' else 'Privacy_Accessibility'
        await asyncio.to_thread(subprocess.run, ['/usr/bin/open', f'x-apple.systempreferences:com.apple.preference.security?{pane}'], check=True)
        return {'message': '已打开系统设置；授权后点击刷新状态'}

    return router
