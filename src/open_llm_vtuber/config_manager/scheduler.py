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
    scene: str = Field("", alias="scene")  # reserved for the OBS integration
    enabled: bool = Field(True, alias="enabled")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "name": Description(
            en="Job name, used in the logs", zh="任务名称，用于日志"
        ),
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
            en="Optional OBS scene to switch to (reserved for phase 3)",
            zh="可选的 OBS 场景（为第三阶段保留）",
        ),
        "enabled": Description(
            en="Enable this job", zh="启用该任务"
        ),
    }


class SchedulerConfig(I18nMixin):
    """Configuration for the scripted live broadcast scheduler."""

    enabled: bool = Field(False, alias="enabled")
    timezone: str = Field("Europe/Madrid", alias="timezone")
    target_client: str = Field("first", alias="target_client")
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
        "jobs": Description(
            en="List of scheduled segments", zh="定时播出任务列表"
        ),
    }
