from typing import ClassVar

from pydantic import Field

from .i18n import Description, I18nMixin


class BiliBiliLiveConfig(I18nMixin):
    """Configuration for BiliBili Live platform."""

    room_ids: list[int] = Field([], alias="room_ids")
    sessdata: str = Field("", alias="sessdata")

    DESCRIPTIONS: ClassVar[dict[str, Description]] = {
        "room_ids": Description(
            en="List of BiliBili live room IDs to monitor", zh="要监控的B站直播间ID列表"
        ),
        "sessdata": Description(
            en="SESSDATA cookie value for authenticated requests (optional)",
            zh="用于认证请求的SESSDATA cookie值（可选）",
        ),
    }


class LiveConfig(I18nMixin):
    """Configuration for live streaming platforms integration."""

    bilibili_live: BiliBiliLiveConfig = Field(
        BiliBiliLiveConfig(), alias="bilibili_live"
    )

    DESCRIPTIONS: ClassVar[dict[str, Description]] = {
        "bilibili_live": Description(
            en="Configuration for BiliBili Live platform", zh="B站直播平台配置"
        ),
    }
