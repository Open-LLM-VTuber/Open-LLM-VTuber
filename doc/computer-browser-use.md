# 电脑与浏览器控制

设置 → 电脑与浏览器提供独立开关、权限状态、测试截屏、专用浏览器与立即停止。开关即时保存。默认关闭；直播、主动闲聊和非本机对话不可调用。

安装：`uv sync --extra control`，然后 `uv run --extra control playwright install chromium`。启动时使用 `uv run --extra control python scripts/run_with_services.py`，以保留可选依赖。

Computer use 当前支持 macOS 主屏幕：截图、打开应用、点击、Unicode 输入、组合键和滚动。需向启动后端的终端或应用授予屏幕录制及辅助功能权限，并使用支持图像输入的模型。锁屏不支持控制。点击坐标对应截图的逻辑像素。

Browser use 使用独立 Chromium 配置目录 `config/browser-profile`，可保留登录状态。支持页面文字快照、按可访问名称点击/填写/按键、滚动、标签页与截图。首次使用需在专用浏览器自行登录。当前不连接日常 Chrome，也不支持文件上传、下载管理和任意脚本执行。

模型通过 `local_computer` 与 `local_browser` 调用；截图作为图像送回模型，普通状态消息不包含截图数据。开关与停止状态在每次执行前检查，停止会取消浏览器任务并阻止排队任务；已经送出的系统输入事件无法撤回。

验证：`uv run --inexact --extra control --with pytest python -m pytest tests/test_computer_use.py tests/test_mcp_execution.py tests/test_extensions.py -q`。
