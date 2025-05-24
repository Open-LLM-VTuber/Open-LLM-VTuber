# upgrade_codes/upgrade_core/comment_diff_fn.py
from ruamel.yaml import YAML
from io import StringIO

def extract_comments(yaml_text: str) -> dict:
    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(StringIO(yaml_text))

    comment_map = {}

    def get_comment_text(comment_list):
        if not comment_list:
            return ""
        return "\n".join(str(c.value).strip() for c in comment_list if c).strip()

    def recurse(node, path=""):
        if not isinstance(node, dict):
            return
        if hasattr(node, 'ca') and node.ca.items:
            for key in node:
                full_path = f"{path}.{key}" if path else str(key)
                if key in node.ca.items:
                    comment_map[full_path] = get_comment_text(node.ca.items[key])
                recurse(node[key], full_path)

    recurse(data)
    return comment_map

def comment_diff_fn(user_text: str, default_text: str):
    user_comments = extract_comments(user_text)
    default_comments = extract_comments(default_text)

    diff_keys = []
    for key in default_comments:
        if key not in user_comments:
            diff_keys.append(key)
        elif default_comments[key] != user_comments[key]:
            diff_keys.append(key)

    return (len(diff_keys) == 0), diff_keys
