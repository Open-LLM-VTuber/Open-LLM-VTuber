# config_manager/system.py
from typing import Dict, ClassVar, Literal

from pydantic import Field, model_validator

from .i18n import I18nMixin, Description


class AudioExportConfig(I18nMixin):
    """Container used when the server re-encodes TTS audio for the client (A23).

    ``wav`` keeps the latency minimal on a LAN (no decoding, no ffmpeg at
    runtime). ``mp3`` at 64 kbps cuts the WebSocket traffic ~10x, which is what
    you want when the overlay/OBS runs on another machine or through a tunnel.
    """

    audio_format: Literal["wav", "mp3"] = Field("wav", alias="format")
    bitrate: str = Field("64k", alias="bitrate")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "format": Description(
            en="Audio container sent over the WebSocket: 'wav' (LAN, lowest "
            "latency) or 'mp3' (~10x less traffic, requires ffmpeg)",
            zh="通过 WebSocket 发送的音频格式：'wav'（局域网，延迟最低）或 "
            "'mp3'（流量约减少 10 倍，需要 ffmpeg）",
        ),
        "bitrate": Description(
            en="MP3 bitrate; ignored when format is 'wav'",
            zh="MP3 比特率；format 为 'wav' 时忽略",
        ),
    }


class SystemConfig(I18nMixin):
    """System configuration settings."""

    conf_version: str = Field(..., alias="conf_version")
    host: str = Field(..., alias="host")
    port: int = Field(..., alias="port")
    config_alts_dir: str = Field(..., alias="config_alts_dir")
    tool_prompts: Dict[str, str] = Field(..., alias="tool_prompts")
    enable_proxy: bool = Field(False, alias="enable_proxy")
    # Optional so that conf.yaml files written before A23 keep validating.
    audio_export: AudioExportConfig = Field(
        default_factory=AudioExportConfig, alias="audio_export"
    )

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "conf_version": Description(en="Configuration version", zh="配置文件版本"),
        "host": Description(en="Server host address", zh="服务器主机地址"),
        "port": Description(en="Server port number", zh="服务器端口号"),
        "config_alts_dir": Description(
            en="Directory for alternative configurations", zh="备用配置目录"
        ),
        "tool_prompts": Description(
            en="Tool prompts to be inserted into persona prompt",
            zh="要插入到角色提示词中的工具提示词",
        ),
        "enable_proxy": Description(
            en="Enable proxy mode for multiple clients",
            zh="启用代理模式以支持多个客户端使用一个 ws 连接",
        ),
        "audio_export": Description(
            en="Audio format used for the TTS payloads sent to clients",
            zh="发送给客户端的 TTS 音频格式",
        ),
    }

    @model_validator(mode="after")
    def check_port(cls, values):
        port = values.port
        if port < 0 or port > 65535:
            raise ValueError("Port must be between 0 and 65535")
        return values
