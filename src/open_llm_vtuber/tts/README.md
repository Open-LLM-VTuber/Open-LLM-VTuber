# 新增 TTS 引擎

将实现放在本目录，例如 `my_voice_tts.py`。模块导出继承
`TTSInterface` 的 `TTSEngine`，实现 `generate_audio`，返回生成的音频路径。
建议把常用参数默认值放在构造函数里，需要的密钥从环境变量读取。
引擎仅在选中时导入，项目其余引擎不需要安装它的专属依赖。

可以通过环境变量启用，不需要编辑主配置：

```sh
VTUBER_TTS_ENGINE=my_voice_tts uv run run_server.py
```

该变量对整个进程生效，包括切换角色。如果需要让某个角色单独选用该引擎，
可以在其角色 YAML 的 `character_config` 下写入以下配置，且启动时不设置覆盖变量：

```yaml
tts_config:
  tts_model: my_voice_tts
  my_voice_tts:
    voice: narrator
```

参数块可省略。自定义参数按关键字传给构造函数。已有内置引擎继续使用原有配置。
