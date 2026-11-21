"""Varied idle suggestions; the character and conversation decide what fits."""
import random

ACTIVITIES = {
    "continue": "接住最近一个尚有余味的话题，补一个属于你自己的观察，不复述上一轮。",
    "read": "从本地书库接着读一小段，用你的性格分享一个发现；没有阅读进度时先选书查原文。",
    "music": "从本地音乐库挑一首符合当前氛围的歌并调用播放工具，简短说说选择理由，不编造听后感。",
    "video": "从本地视频库挑一个符合你兴趣的视频并调用播放工具，提出一个观看时可以留意的细节，不假装已经看过。",
    "story": "即兴讲一个两三句话的小故事或脑洞，体现你的兴趣和幽默方式；明确是想象，不伪装真实经历。",
    "game": "给一个与你兴趣有关的小谜题、二选一或想象挑战。一次只出一题，先不公布答案；用户不接就不要追问。",
    "perspective": "围绕最近话题给一个有趣的反向观点或生活类比，有自己的判断但不说教。",
    "quiet": "用一个简短、符合你性格的日常感想陪伴用户，不提问，不要求回应。",
}


def activity_hint(context, chooser=random.choice):
    identity = (context.character_config.conf_uid, context.history_uid)
    if getattr(context, "_proactive_identity", None) != identity:
        context._proactive_identity = identity
        context._proactive_recent = []
    recent = context._proactive_recent
    key = chooser([key for key in ACTIVITIES if key not in recent])
    context._proactive_recent = (recent + [key])[-3:]
    return (
        "本轮可选灵感（不合人物或语境就跳过，不要向用户念出活动安排）："
        + ACTIVITIES[key]
        + "\n人物性格、兴趣、关系边界和当前情绪以系统中的当前角色设定为准。"
        "不要为了执行灵感改变人设；用户等待问题答案时优先回答，用户已拒绝的活动不再推荐。"
    )
