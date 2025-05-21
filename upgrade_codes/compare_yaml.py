from ruamel.yaml import YAML


def collect_all_key_paths(d, prefix=""):
    keys = set()
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        keys.add(full_key)
        if isinstance(v, dict):
            keys.update(collect_all_key_paths(v, full_key))
    return keys

def compare_yaml_keys(path1, path2):
    yaml = YAML(typ="safe")
    with open(path1, "r", encoding="utf-8") as f1, open(path2, "r", encoding="utf-8") as f2:
        config1 = yaml.load(f1)
        config2 = yaml.load(f2)

    keys1 = collect_all_key_paths(config1)
    keys2 = collect_all_key_paths(config2)

    only_in_1 = keys1 - keys2
    only_in_2 = keys2 - keys1

    return only_in_1, only_in_2

if __name__ == "__main__":
    conf1 = "config_templates/conf.ZH.default.yaml"
    conf2 = "config_templates/conf.default.yaml"
    only_in_1, only_in_2 = compare_yaml_keys(conf1, conf2)

    if not only_in_1 and not only_in_2:
        print("✅ 两个 YAML 文件的 key 完全一致")
    else:
        print("❌ 不一致:")
        if only_in_1:
            print("仅在", conf1, "中存在的 key:", only_in_1)
        if only_in_2:
            print("仅在", conf2 ,"中存在的 key:", only_in_2)
