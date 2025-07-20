from io import StringIO
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


def get_comment_text(comment_list):
    if not comment_list:
        return ""
    flattened = []
    for c in comment_list:
        if isinstance(c, list):
            for sub in c:
                if hasattr(sub, "value"):
                    flattened.append(str(sub.value).strip())
        elif hasattr(c, "value"):
            flattened.append(str(c.value).strip())
    return "\n".join(flattened).strip()


def extract_comments(yaml_text: str) -> dict:
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(StringIO(yaml_text))

    comment_map = {}

    def recurse(node, path=""):
        if not isinstance(node, CommentedMap):
            return
        if hasattr(node, "ca") and isinstance(node.ca.items, dict):
            for key in node:
                full_path = f"{path}.{key}" if path else str(key)
                if key in node.ca.items:
                    comment_map[full_path] = get_comment_text(node.ca.items[key])
                recurse(node[key], full_path)

    recurse(data)
    return comment_map


def comment_diff_fn(default_text: str, user_text: str):
    default_comments = extract_comments(default_text)
    user_comments = extract_comments(user_text)

    diff_keys = []

    all_keys = set(default_comments.keys()) | set(user_comments.keys())
    for key in all_keys:
        d = default_comments.get(key, "")
        u = user_comments.get(key, "")
        if d != u:
            diff_keys.append(key)

    return (len(diff_keys) == 0), diff_keys
