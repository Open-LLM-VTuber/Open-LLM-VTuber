from pydantic import Field
from typing import Dict, ClassVar, List
from .i18n import I18nMixin, Description


class BiliBiliLiveConfig(I18nMixin):
    """Configuration for BiliBili Live platform."""

    room_ids: List[int] = Field([], alias="room_ids")
    sessdata: str = Field("", alias="sessdata")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "room_ids": Description(
            en="List of BiliBili live room IDs to monitor", zh="要监控的B站直播间ID列表"
        ),
        "sessdata": Description(
            en="SESSDATA cookie value for authenticated requests (optional)",
            zh="用于认证请求的SESSDATA cookie值（可选）",
        ),
    }


class TikTokLiveConfig(I18nMixin):
    """Configuration for TikTok Live platform."""

    enabled: bool = Field(False, alias="enabled")
    unique_id: str = Field("", alias="unique_id")
    proxy_url: str = Field("", alias="proxy_url")
    max_queue: int = Field(5, alias="max_queue")
    cooldown_seconds: float = Field(6.0, alias="cooldown_seconds")
    min_gift_coins: int = Field(1, alias="min_gift_coins")
    reply_to_gifts: bool = Field(True, alias="reply_to_gifts")
    reply_to_follows: bool = Field(True, alias="reply_to_follows")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "enabled": Description(
            en="Enable the TikTok Live connector", zh="启用TikTok直播连接器"
        ),
        "unique_id": Description(
            en="TikTok username of the account that is live (without @)",
            zh="正在直播的TikTok账号用户名（不含@）",
        ),
        "proxy_url": Description(
            en="Proxy WebSocket URL (leave empty to build it from system_config)",
            zh="代理WebSocket地址（留空则根据system_config生成）",
        ),
        "max_queue": Description(
            en="Maximum number of pending events (gifts are dropped last)",
            zh="待处理事件的最大数量（礼物最后才丢弃）",
        ),
        "cooldown_seconds": Description(
            en="Minimum seconds between two replies", zh="两次回复之间的最短秒数"
        ),
        "min_gift_coins": Description(
            en="Ignore gifts cheaper than this many coins",
            zh="忽略低于该币值的礼物",
        ),
        "reply_to_gifts": Description(
            en="Thank viewers for their gifts", zh="感谢观众的礼物"
        ),
        "reply_to_follows": Description(
            en="Greet new followers", zh="向新关注者打招呼"
        ),
    }


class LiveConfig(I18nMixin):
    """Configuration for live streaming platforms integration."""

    bilibili_live: BiliBiliLiveConfig = Field(
        BiliBiliLiveConfig(), alias="bilibili_live"
    )
    tiktok_live: TikTokLiveConfig = Field(TikTokLiveConfig(), alias="tiktok_live")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "bilibili_live": Description(
            en="Configuration for BiliBili Live platform", zh="B站直播平台配置"
        ),
        "tiktok_live": Description(
            en="Configuration for TikTok Live platform", zh="TikTok直播平台配置"
        ),
    }
