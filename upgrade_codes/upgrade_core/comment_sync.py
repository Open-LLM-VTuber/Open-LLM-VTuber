# upgrade/comment_sync.py

class CommentSynchronizer:
    def __init__(self, default_path, user_path, logger, yaml, texts_compare):
        self.default_path = default_path
        self.user_path = user_path
        self.logger = logger
        self.yaml = yaml
        self.texts_compare = texts_compare
    def sync(self):
        try:
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
                        sync_comments(default_node[key], user_node[key], current_path)
                        
            sync_comments(default_tree, user_tree)

            if hasattr(default_tree, 'ca') and hasattr(user_tree, 'ca'):
                user_tree.ca.end = default_tree.ca.end

            with open(self.user_path, "w", encoding="utf-8") as f:
                self.yaml.dump(user_tree, f)

            self.logger.info(self.texts_compare["comment_sync_success"])
        except Exception as e:
            self.logger.error(self.texts_compare["comment_sync_error"].format(error=e))

