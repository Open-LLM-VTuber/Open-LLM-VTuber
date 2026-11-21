# 资源库、扩展与播放器

顶部文件夹按钮打开资源库，可批量选择或拖入视频、音乐、图片和书籍。文件写入 `media/videos`、`media/music`、`media/images`、`media/books`；书库可通过 `VTUBER_BOOKS_DIR` 指定目录。同名文件自动编号，不覆盖已有文件。书籍最大 30 MB，其他文件最大 500 MB。

侧栏音乐播放器读取音乐库，支持播放、暂停、切歌、进度、音量、列表循环与单曲循环；视频标签提供本地视频列表与原生播放控件。浏览器不支持的编码需先转换。旧的右下角“场景与媒体”面板及自动场景切换已移除。背景在设置的常规页面选择。

设置 → 主题提供深色、浅色、跟随系统和五种强调色。修改即时预览，保存保留；取消、关闭或点击遮罩恢复打开时的值。

## 扩展格式

顶部网格按钮打开扩展管理。支持导入单独 `SKILL.md`、包含一个 `SKILL.md` 的 ZIP，或包含 `plugin.json` 的插件 ZIP。安装后默认停用。可启用、停用、移除和测试 MCP 连接。参考 Skill 位于 `doc/examples/reading-skill/SKILL.md`。

插件是本应用的声明式组合包，可组合多个 Skills 与 stdio MCP 服务，不运行安装脚本。当前仅加载 Skill 的 SKILL.md 正文；附属参考文件、脚本和其他应用的插件格式暂不支持。ZIP 解压总量上限 5 MB / 200 个条目。

```text
my-plugin.zip
├── plugin.json
└── skills/
    └── reading-notes/
        └── SKILL.md
```

```json
{
  "id": "my-plugin",
  "name": "阅读助手",
  "description": "读书笔记与时间工具",
  "mcpServers": {
    "my-time": {
      "command": "uvx",
      "args": ["mcp-server-time"],
      "env": {}
    }
  }
}
```

也可直接在“添加 MCP”中填写唯一服务 ID 和 command / args / env / cwd JSON。仅支持 stdio；HTTP/SSE、OAuth 与插件市场暂未实现。测试连接会运行命令并获取工具列表；运行环境和依赖需可用。

Skills 启停在下一次对话生效，不写入历史。每个 Skill 最多 24000 字符，已启用 Skill 总长度最多 60000 字符。MCP 配置会合并进现有工具系统；启停或移除后重启后端，再刷新网页生效。现有 `mcp_servers.json` 与角色配置不被改写。

扩展配置保存在 `config/extensions.json`，包含可能敏感的环境变量，已加入 Git 忽略。接口仅允许本机调用；直播模式禁止管理和加载扩展。

## 能力边界与执行验证

- MCP 是实际执行接口：服务提供什么工具，助手才能执行什么操作；连接成功只代表可以发现工具，不代表已完成用户任务。
- Skill 是工作方法与步骤，不会自动获得文件、浏览器、邮件等权限。只有配合可用工具才能执行相应操作。
- 插件是 Skills 与 MCP 配置的组合包，不等同于兼容其他应用的插件运行环境。
- 当前 MCP 结果会完整传递多段文本、结构化结果与资源链接；服务报告失败时，会向模型和界面传递失败状态。OpenAI/提示词模式仍不向模型传递图片像素。

可运行 `uv run --with pytest python -m pytest tests/test_mcp_execution.py tests/test_extensions.py -q` 验证：安装与启用、真实 stdio 连接、在临时目录写入并读回文件、结果与错误传递，以及提示词参数解析。测试不依赖外部账号，也不证明当前聊天模型一定能正确选择工具；实际使用仍需启用扩展并按上述要求重启后端，在对话中检查工具执行结果。
