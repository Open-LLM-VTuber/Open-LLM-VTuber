# upgrade/comment_sync.py
import re

class CommentSynchronizer:
    def __init__(self, default_path, user_path, logger, yaml):
        self.default_path = default_path
        self.user_path = user_path
        self.logger = logger
        self.yaml = yaml

    def sync(self):
        self.logger.debug("[DEBUG] Starting comment synchronization")

        with open(self.default_path, "r", encoding="utf-8") as f:
            default_tree = self.yaml.load(f)
        with open(self.user_path, "r", encoding="utf-8") as f:
            user_tree = self.yaml.load(f)

        def sync_comments(default_node, user_node, path=""):
            if not isinstance(default_node, dict) or not isinstance(user_node, dict):
                return

            for key in default_node:
                if key in user_node:
                    current_path = f"{path}.{key}" if path else key
                    if hasattr(default_node, 'ca') and hasattr(user_node, 'ca'):
                        if key in default_node.ca.items:
                            user_node.ca.items[key] = default_node.ca.items[key]
                            self.logger.debug(f"[DEBUG] Synced comment for key: {current_path}")
                    sync_comments(default_node[key], user_node[key], current_path)

        sync_comments(default_tree, user_tree)

        if hasattr(default_tree, 'ca') and hasattr(user_tree, 'ca'):
            user_tree.ca.end = default_tree.ca.end
            self.logger.debug("[DEBUG] Synced end-of-file comments")

        with open(self.user_path, "w", encoding="utf-8") as f:
            self.yaml.dump(user_tree, f)

        self.logger.info("Comment synchronization completed.")
