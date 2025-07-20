# upgrade/comment_sync.py
from typing import Dict
from logging import Logger
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


class CommentSynchronizer:
    def __init__(
        self,
        default_path: str,
        user_path: str,
        logger: Logger,
        yaml: YAML,
        texts_compare: Dict[str, str],
    ):
        self.default_path = default_path
        self.user_path = user_path
        self.logger = logger
        self.yaml = yaml
        self.texts_compare = texts_compare

    def sync(self) -> None:
        try:
            with open(self.default_path, "r", encoding="utf-8") as f:
                default_tree: CommentedMap = self.yaml.load(f)
            with open(self.user_path, "r", encoding="utf-8") as f:
                user_tree: CommentedMap = self.yaml.load(f)

            def sync_comments(
                default_node: CommentedMap, user_node: CommentedMap, path: str = ""
            ) -> None:
                if not isinstance(default_node, CommentedMap) or not isinstance(
                    user_node, CommentedMap
                ):
                    return

                for key in default_node:
                    if key in user_node:
                        current_path = f"{path}.{key}" if path else key
                        if hasattr(default_node, "ca") and hasattr(user_node, "ca"):
                            if key in default_node.ca.items:
                                user_node.ca.items[key] = default_node.ca.items[key]
                        sync_comments(default_node[key], user_node[key], current_path)

            sync_comments(default_tree, user_tree)

            if hasattr(default_tree, "ca") and hasattr(user_tree, "ca"):
                user_tree.ca.end = default_tree.ca.end

            with open(self.user_path, "w", encoding="utf-8") as f:
                self.yaml.dump(user_tree, f)

            self.logger.info(self.texts_compare["comment_sync_success"])
        except Exception as e:
            self.logger.error(self.texts_compare["comment_sync_error"].format(error=e))
