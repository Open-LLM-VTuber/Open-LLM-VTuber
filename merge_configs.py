import logging
from ruamel.yaml import YAML
from src.open_llm_vtuber.config_manager.utils import load_text_file_with_guess_encoding

logger = logging.getLogger(__name__)

# Multilingual texts for merge_configs log messages
TEXTS_MERGE = {
    "zh": {
        "new_config_item": "[信息] 新增配置项: {key}",
    },
    "en": {
        "new_config_item": "[INFO] New config item: {key}",
    },
}

# Multilingual texts for compare_configs log messages
TEXTS_COMPARE = {
    "zh": {
        "missing_keys": "[警告] 用户配置缺少以下键，可能与默认配置不一致: {keys}",
        "extra_keys": "[警告] 用户配置包含以下默认配置中不存在的键: {keys}",
        "up_to_date": "[调试] 用户配置与默认配置一致。",
    },
    "en": {
        "missing_keys": "[WARNING] User config is missing the following keys, which may be out-of-date: {keys}",
        "extra_keys": "[WARNING] User config contains the following keys not present in default config: {keys}",
        "up_to_date": "[DEBUG] User config is up-to-date with default config.",
    },
}


def merge_configs(user_path: str, default_path: str, lang: str = "en"):
    yaml = YAML()
    yaml.preserve_quotes = True

    user_config = yaml.load(load_text_file_with_guess_encoding(user_path))
    default_config = yaml.load(load_text_file_with_guess_encoding(default_path))

    new_keys = []

    def merge(d_user, d_default, path=""):
        for k, v in d_default.items():
            current_path = f"{path}.{k}" if path else k
            if k not in d_user:
                d_user[k] = v
                new_keys.append(current_path)
            elif isinstance(v, dict) and isinstance(d_user.get(k), dict):
                merge(d_user[k], v, current_path)
        return d_user

    merged = merge(user_config, default_config)

    # Update conf_version from default_config without overriding other user settings
    version_value = (
        user_config["system_config"].get("conf_version")
        if "system_config" in user_config
        else ""
    )
    version_change_string = "conf_version: " + version_value

    if (
        "system_config" in default_config
        and "conf_version" in default_config["system_config"]
    ):
        merged.setdefault("system_config", {})
        merged["system_config"]["conf_version"] = default_config["system_config"][
            "conf_version"
        ]
        version_change_string = (
            version_change_string
            + " -> "
            + default_config["system_config"]["conf_version"]
        )

    with open(user_path, "w") as f:
        yaml.dump(merged, f)

    # Log upgrade details (replacing manual file writing)
    texts = TEXTS_MERGE.get(lang, TEXTS_MERGE["en"])
    logger.info(version_change_string)
    for key in new_keys:
        logger.info(texts["new_config_item"].format(key=key))
    return new_keys


def collect_all_subkeys(d, base_path):
    """Collect all keys in the dictionary d, recursively, with base_path as the prefix."""
    keys = []
    # Only process if d is a dictionary
    if isinstance(d, dict):
        for key, value in d.items():
            current_path = f"{base_path}.{key}" if base_path else key
            keys.append(current_path)
            if isinstance(value, dict):
                keys.extend(collect_all_subkeys(value, current_path))
    return keys


def get_missing_keys(user, default, path=""):
    """Recursively find keys in default that are missing in user."""
    missing = []
    for key, default_val in default.items():
        current_path = f"{path}.{key}" if path else key
        if key not in user:
            missing.append(current_path)
        else:
            user_val = user[key]
            if isinstance(default_val, dict):
                if isinstance(user_val, dict):
                    missing.extend(
                        get_missing_keys(user_val, default_val, current_path)
                    )
                else:
                    subtree_missing = collect_all_subkeys(default_val, current_path)
                    missing.extend(subtree_missing)
    return missing


def get_extra_keys(user, default, path=""):
    """Recursively find keys in user that are not present in default."""
    extra = []
    for key, user_val in user.items():
        current_path = f"{path}.{key}" if path else key
        if key not in default:
            # Only collect subkeys if the value is a dictionary
            if isinstance(user_val, dict):
                subtree_extra = collect_all_subkeys(user_val, current_path)
                extra.extend(subtree_extra)
            extra.append(current_path)
        else:
            default_val = default[key]
            if isinstance(user_val, dict) and isinstance(default_val, dict):
                extra.extend(get_extra_keys(user_val, default_val, current_path))
            elif isinstance(user_val, dict):
                subtree_extra = collect_all_subkeys(user_val, current_path)
                extra.extend(subtree_extra)
    return extra


def compare_configs(user_path: str, default_path: str, lang: str = "en") -> bool:
    """Compare user and default configs, log discrepancies, and return status."""
    yaml = YAML(typ="safe")
    yaml.preserve_quotes = True

    user_config = yaml.load(load_text_file_with_guess_encoding(user_path))
    default_config = yaml.load(load_text_file_with_guess_encoding(default_path))

    missing = get_missing_keys(user_config, default_config)
    extra = get_extra_keys(user_config, default_config)

    texts = TEXTS_COMPARE.get(lang, TEXTS_COMPARE["en"])

    if missing:
        logger.warning(texts["missing_keys"].format(keys=", ".join(missing)))
        return False
    if extra:
        logger.warning(texts["extra_keys"].format(keys=", ".join(extra)))
    else:
        logger.debug(texts["up_to_date"])

    return True
