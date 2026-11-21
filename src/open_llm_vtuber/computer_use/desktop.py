"""macOS control using Quartz, with permission and lock checks before every action."""
import base64
import ctypes
import io
import subprocess
import sys
import tempfile
from pathlib import Path

KEYS = {'enter': 36, 'tab': 48, 'space': 49, 'backspace': 51, 'escape': 53,
        'left': 123, 'right': 124, 'down': 125, 'up': 126, 'delete': 117,
        'a': 0, 's': 1, 'd': 2, 'f': 3, 'h': 4, 'g': 5, 'z': 6, 'x': 7,
        'c': 8, 'v': 9, 'b': 11, 'q': 12, 'w': 13, 'e': 14, 'r': 15,
        'y': 16, 't': 17, 'o': 31, 'u': 32, 'i': 34, 'p': 35,
        'l': 37, 'j': 38, 'k': 40, 'n': 45, 'm': 46}


def permissions():
    if sys.platform != 'darwin':
        return {'supported': False, 'screen': False, 'accessibility': False, 'locked': False,
                'message': 'Computer use 当前支持 macOS'}
    try:
        import Quartz as Q
        session = Q.CGSessionCopyCurrentDictionary() or {}
        services = ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
        services.AXIsProcessTrusted.restype = ctypes.c_bool
        services.AXIsProcessTrusted.argtypes = []
        return {'supported': True, 'screen': bool(Q.CGPreflightScreenCaptureAccess()),
                'accessibility': bool(services.AXIsProcessTrusted()),
                'locked': bool(session.get('CGSSessionScreenIsLocked', False)),
                'message': '请为启动后端的终端或应用授予屏幕录制与辅助功能权限'}
    except ImportError:
        return {'supported': False, 'screen': False, 'accessibility': False, 'locked': False,
                'message': '请运行 uv sync --extra control 安装 macOS 控制依赖'}


class Desktop:
    def __init__(self):
        self.observed = False

    def execute(self, action, check, **args):
        import Quartz as Q
        check()
        state = permissions()
        if state['locked']:
            raise RuntimeError('屏幕已锁定，已阻止电脑操作')
        if not state['screen']:
            raise RuntimeError('缺少屏幕录制权限，请在系统设置中授权后重试')
        if action != 'screenshot' and not state['accessibility']:
            raise RuntimeError('缺少辅助功能权限，请在系统设置中授权后重试')
        if action not in {'screenshot', 'open_app'} and not self.observed:
            raise ValueError('请先截图观察当前屏幕，再执行电脑操作')
        if action == 'open_app':
            app = args.get('app', '')
            if not app or app.startswith('-') or len(app) > 150:
                raise ValueError('请输入有效应用名称')
            check()
            subprocess.run(['/usr/bin/open', '-a', app], check=True, timeout=5, capture_output=True)
        elif action == 'click':
            bounds = Q.CGDisplayBounds(Q.CGMainDisplayID())
            x, y = args.get('x', -1), args.get('y', -1)
            if not (0 <= x < bounds.size.width and 0 <= y < bounds.size.height):
                raise ValueError('点击坐标必须在主屏幕范围内，单位为截图中的逻辑像素')
            right = args.get('button', 'left') == 'right'
            button = Q.kCGMouseButtonRight if right else Q.kCGMouseButtonLeft
            down = Q.kCGEventRightMouseDown if right else Q.kCGEventLeftMouseDown
            up = Q.kCGEventRightMouseUp if right else Q.kCGEventLeftMouseUp
            check()
            for event_type in (down, up):
                Q.CGEventPost(Q.kCGHIDEventTap, Q.CGEventCreateMouseEvent(None, event_type, (x, y), button))
        elif action == 'type':
            text = args.get('text', '')
            if len(text) > 2000:
                raise ValueError('单次输入最多 2000 字符')
            for offset in range(0, len(text), 20):
                check()
                chunk = text[offset:offset + 20]
                event = Q.CGEventCreateKeyboardEvent(None, 0, True)
                Q.CGEventKeyboardSetUnicodeString(event, len(chunk.encode('utf-16-le')) // 2, chunk)
                Q.CGEventPost(Q.kCGHIDEventTap, event)
                Q.CGEventPost(Q.kCGHIDEventTap, Q.CGEventCreateKeyboardEvent(None, 0, False))
        elif action == 'press':
            parts = args.get('key', '').lower().split('+')
            if parts[-1] not in KEYS:
                raise ValueError('不支持此按键；支持字母、enter/tab/escape、方向键及 cmd/ctrl/alt/shift 组合')
            modifiers = {'cmd': Q.kCGEventFlagMaskCommand, 'ctrl': Q.kCGEventFlagMaskControl,
                         'alt': Q.kCGEventFlagMaskAlternate, 'shift': Q.kCGEventFlagMaskShift}
            flags = 0
            for part in parts[:-1]:
                if part not in modifiers:
                    raise ValueError('不支持此组合键修饰符')
                flags |= modifiers[part]
            check()
            for down in (True, False):
                event = Q.CGEventCreateKeyboardEvent(None, KEYS[parts[-1]], down)
                Q.CGEventSetFlags(event, flags)
                Q.CGEventPost(Q.kCGHIDEventTap, event)
        elif action == 'scroll':
            check()
            amount = max(-1200, min(1200, args.get('amount', 500)))
            Q.CGEventPost(Q.kCGHIDEventTap, Q.CGEventCreateScrollWheelEvent(None, Q.kCGScrollEventUnitPixel, 1, -amount))
        elif action != 'screenshot':
            raise ValueError('不支持的电脑操作')
        check()
        with tempfile.TemporaryDirectory(prefix='vt-screen-') as folder:
            path = Path(folder) / 'screen.png'
            subprocess.run(['/usr/sbin/screencapture', '-x', '-m', str(path)],
                           check=True, timeout=8, capture_output=True)
            bounds = Q.CGDisplayBounds(Q.CGMainDisplayID())
            size = (int(bounds.size.width), int(bounds.size.height))
            output = Path(folder) / 'screen.jpg'
            subprocess.run(['/usr/bin/sips', '-s', 'format', 'jpeg', '-z', str(size[1]), str(size[0]),
                            str(path), '--out', str(output)], check=True, timeout=8, capture_output=True)
            encoded = base64.b64encode(output.read_bytes()).decode()
        self.observed = True
        return {'width': size[0], 'height': size[1], 'coordinateSpace': '主屏幕逻辑像素',
                'message': '已截取操作后的屏幕；请核验实际结果，不要仅根据输入事件声称成功。'}, [
            {'type': 'image', 'mimeType': 'image/jpeg', 'data': encoded}]
