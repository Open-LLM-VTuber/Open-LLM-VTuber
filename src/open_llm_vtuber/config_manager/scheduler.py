# config_manager/scheduler.py
from pydantic import Field
from typing import Dict, ClassVar, List

from .i18n import I18nMixin, Description


class ScheduledJob(I18nMixin):
    """A single scripted segment of the show."""

    name: str = Field(..., alias="name")
    cron: str = Field("", alias="cron")  # "minute hour day month weekday"
    interval_minutes: int = Field(0, alias="interval_minutes")
    text: str = Field("", alias="text")  # empty -> proactive_speak_prompt
    scene: str = Field("", alias="scene")  # OBS scene switched before speaking
    background: str = Field("", alias="background")  # stage-update background
    transition: str = Field("fade", alias="transition")
    duration_ms: int = Field(800, alias="duration_ms")
    draw: int = Field(0, alias="draw", ge=0, le=3)  # 0 = no tarot draw
    draw_seed: int = Field(0, alias="draw_seed")  # 0 = random spread each fire
    question: str = Field("", alias="question")  # seeker's question, optional
    enabled: bool = Field(True, alias="enabled")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "name": Description(en="Job name, used in the logs", zh="任务名称，用于日志"),
        "cron": Description(
            en="Crontab expression with 5 fields (minute hour day month weekday)",
            zh="5 字段的 crontab 表达式（分 时 日 月 周）",
        ),
        "interval_minutes": Description(
            en="Run every N minutes (used when cron is empty)",
            zh="每 N 分钟运行一次（cron 为空时使用）",
        ),
        "text": Description(
            en="Instruction for the LLM; empty uses the configured "
            "proactive speak prompt",
            zh="给 LLM 的指令；留空则使用配置的主动发言提示词",
        ),
        "scene": Description(
            en="OBS scene to switch to when the job fires (needs obs.enabled)",
            zh="任务触发时切换到的 OBS 场景（需要 obs.enabled）",
        ),
        "background": Description(
            en="Background sent to the overlay as a stage-update "
            "(the job name is used as the stage id)",
            zh="作为 stage-update 发送给 overlay 的背景（任务名作为舞台 id）",
        ),
        "transition": Description(
            en="Stage transition: 'fade' or 'none'", zh="舞台过渡：'fade' 或 'none'"
        ),
        "duration_ms": Description(
            en="Stage transition duration in milliseconds",
            zh="舞台过渡时长（毫秒）",
        ),
        "draw": Description(
            en="Draw N tarot cards when the job fires (0 = no draw, max 3). The "
            "cards appear on the overlay and are described to the LLM",
            zh="任务触发时抽取 N 张塔罗牌（0 表示不抽，最多 3 张）。牌面显示在 overlay 上并告知 LLM",
        ),
        "draw_seed": Description(
            en="0 = a different spread on every fire; any other number replays "
            "the same spread",
            zh="0 表示每次随机；其他数字则重复同一组牌",
        ),
        "question": Description(
            en="Seeker's question added to the tarot brief (optional)",
            zh="加入塔罗提示中的求问者问题（可选）",
        ),
        "enabled": Description(en="Enable this job", zh="启用该任务"),
    }


class OBSConfig(I18nMixin):
    """OBS Studio WebSocket settings (scene switching and stream control)."""

    enabled: bool = Field(False, alias="enabled")
    host: str = Field("127.0.0.1", alias="host")
    port: int = Field(4455, alias="port", ge=1, le=65535)
    password: str = Field("", alias="password")
    timeout: float = Field(3.0, alias="timeout", ge=0.5, le=30.0)
    start_stream: bool = Field(False, alias="start_stream")
    stop_stream_on_shutdown: bool = Field(False, alias="stop_stream_on_shutdown")
    switch_scenes: bool = Field(True, alias="switch_scenes")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "enabled": Description(
            en="Connect to OBS so jobs can switch scenes and start the stream",
            zh="连接 OBS，以便任务切换场景并启动直播",
        ),
        "host": Description(en="OBS WebSocket host", zh="OBS WebSocket 主机"),
        "port": Description(en="OBS WebSocket port", zh="OBS WebSocket 端口"),
        "password": Description(
            en="Password shown in OBS -> Tools -> WebSocket Server Settings",
            zh="OBS -> 工具 -> WebSocket 服务器设置中显示的密码",
        ),
        "timeout": Description(
            en="Connection and request timeout in seconds", zh="连接与请求超时（秒）"
        ),
        "start_stream": Description(
            en="Call StartStream when the scheduler starts",
            zh="调度器启动时调用 StartStream",
        ),
        "stop_stream_on_shutdown": Description(
            en="Call StopStream when the server shuts down",
            zh="服务器关闭时调用 StopStream",
        ),
        "switch_scenes": Description(
            en="Allow jobs to switch the OBS program scene",
            zh="允许任务切换 OBS 当前场景",
        ),
    }


class SchedulerConfig(I18nMixin):
    """Configuration for the scripted live broadcast scheduler."""

    enabled: bool = Field(False, alias="enabled")
    timezone: str = Field("Europe/Madrid", alias="timezone")
    target_client: str = Field("first", alias="target_client")
    obs: OBSConfig = Field(default_factory=OBSConfig, alias="obs")
    jobs: List[ScheduledJob] = Field(default_factory=list, alias="jobs")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "enabled": Description(
            en="Enable the scheduler that emits scripted segments",
            zh="启用定时播出调度器",
        ),
        "timezone": Description(
            en="IANA timezone used for the cron expressions",
            zh="cron 表达式使用的时区",
        ),
        "target_client": Description(
            en="Client that receives the segment: 'first' or a client_uid",
            zh="接收播出的客户端：'first' 或指定 client_uid",
        ),
        "obs": Description(
            en="OBS Studio WebSocket integration (optional)",
            zh="OBS Studio WebSocket 集成（可选）",
        ),
        "jobs": Description(en="List of scheduled segments", zh="定时播出任务列表"),
    }
