# comment_diff_fn.py
from ruamel.yaml import YAML
from io import StringIO

def comment_diff_fn(default_text: str, user_text: str):
    yaml = YAML()
    yaml.preserve_quotes = True

    default_tree = yaml.load(StringIO(default_text))
    user_tree = yaml.load(StringIO(user_text))

    diff_keys = []

    def get_key_comment_str(node, key):
        """Return a string representation of all comments for a given key"""
        if not hasattr(node, 'ca') or key not in node.ca.items:
            return ''
        entry = node.ca.items[key]
        parts = []
        for c in [entry[0], entry[1], entry[2], entry[3]]:
            if c is not None:
                parts.append(str(c).strip())
        return "\n".join(parts)

    def compare_comments_recursive(d_node, u_node, path=""):
        if not isinstance(d_node, dict) or not isinstance(u_node, dict):
            return

        for key in d_node:
            current_path = f"{path}.{key}" if path else str(key)
            if key not in u_node:
                continue  # key 不存在就不对比注释

            # 获取注释并比较
            default_comment = get_key_comment_str(d_node, key)
            user_comment = get_key_comment_str(u_node, key)

            if default_comment != user_comment:
                diff_keys.append(current_path)

            compare_comments_recursive(d_node[key], u_node[key], current_path)

    compare_comments_recursive(default_tree, user_tree)
    return (len(diff_keys) == 0), diff_keys
