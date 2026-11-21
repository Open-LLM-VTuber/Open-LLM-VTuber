"""Capability-aware Live2D action planning without an extra LLM round trip."""

import json
import re
from pathlib import Path
from loguru import logger

ACTION_TAG = re.compile(r"\[action:([^\]]*)\]", re.IGNORECASE)


class Live2DActionAgent:
    def __init__(self, model_info, root=Path("live2d-models")):
        self.actions = []
        self.enabled = model_info.get("actionAgent", {}).get("enabled", True)
        self.traits = model_info.get("actionAgent", {}).get("traits", "")
        if not self.enabled:
            return
        try:
            url = model_info.get("url", "").split("?", 1)[0]
            prefix = "/live2d-models/"
            if not url.startswith(prefix):
                return
            root = Path(root).resolve()
            path = (root / url[len(prefix) :]).resolve()
            if not path.is_relative_to(root):
                return
            settings = json.loads(path.read_text(encoding="utf-8-sig"))
            labels = model_info.get("actionAgent", {}).get("motionDescriptions", {})
            idle = model_info.get("idleMotionGroupName", "Idle")
            for group, motions in (
                settings.get("FileReferences", {}).get("Motions", {}).items()
            ):
                if group == idle:
                    continue
                for index, motion in enumerate(motions):
                    asset = (path.parent / motion["File"]).resolve()
                    if not asset.is_relative_to(root) or not asset.is_file():
                        continue
                    key = f"{group}:{index}"
                    self.actions.append(
                        {
                            "group": group,
                            "index": index,
                            "description": labels.get(
                                key, f"未标注动作 {motion['File']}，勿假定其含义"
                            ),
                        }
                    )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning(f"Cannot load Live2D action capabilities: {exc}")

    def prompt(self):
        if not self.actions:
            return ""
        options = "\n".join(
            f"[action:{i}] {a['description']}" for i, a in enumerate(self.actions)
        )
        return (
            f"\nLive2D 动作代理：角色特点：{self.traits or '遵循当前角色人设'}。\n"
            f"模型实际可用动作如下：\n{options}\n"
            "可在适合表演的句首放一个 [action:编号] 标签，配合已有情绪标签。"
            "每次回复最多两次，避免相邻句重复动作；普通说明无需动作。"
            "只使用清单内编号，不编造模型能力。未标注动作仅在用户要求展示动作时选择。"
            "不要向用户朗读动作标签。\n"
        )

    def extract(self, text):
        selected = []
        for match in ACTION_TAG.finditer(text):
            value = match.group(1)
            if value.isdecimal() and int(value) < len(self.actions):
                action = self.actions[int(value)]
                selected = [{"group": action["group"], "index": action["index"]}]
                break
        return ACTION_TAG.sub("", text), selected
