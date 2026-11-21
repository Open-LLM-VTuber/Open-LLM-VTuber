"""Resolve conversation-driven stage changes against local assets."""

from .media_library import list_media

DESCRIPTION = (
    "控制侧栏音乐和视频播放器。用户请求听歌、看本地视频、暂停或继续时调用此工具。"
    "用 list 查看可选文件；play 使用媒体库返回的 path 和 kind。播放须符合用户意愿。"
    "命令由网页执行，不要声称已确认播放成功。背景在设置页面手动配置。"
)
SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["list", "play", "pause", "resume", "stop"],
        },
        "path": {"type": "string", "description": "媒体库相对路径"},
        "kind": {"type": "string", "enum": ["music", "videos"]},
    },
    "required": ["action"],
    "additionalProperties": False,
}


def control_stage(action, path=None, kind=None):
    if action == "list":
        return list_media(), None
    elif action == "play":
        if not any(entry["path"] == path for entry in list_media().get(kind, [])):
            raise ValueError("媒体不存在，请先查询列表")
    elif action not in {"pause", "resume", "stop"}:
        raise ValueError("未知场景操作")
    return {"dispatched": action, "playback_confirmed": False, "note": "仅派发操作，尚未确认浏览器执行成功"}, {"action": action, "path": path, "kind": kind}
