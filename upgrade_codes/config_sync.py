import os
import shutil
from upgrade_codes.constants import USER_CONF,BACKUP_CONF,TEXTS, ZH_DEFAULT_CONF, EN_DEFAULT_CONF, TEXTS_COMPARE, TEXTS_MERGE
import logging
from ruamel.yaml import YAML
from src.open_llm_vtuber.config_manager.utils import load_text_file_with_guess_encoding
from upgrade_codes.comment_sync import CommentSynchronizer

class ConfigSynchronizer:
    def __init__(self, lang="en", logger = logging.getLogger(__name__)):
        self.lang = lang
        self.texts = TEXTS[lang]
        self.default_path = ZH_DEFAULT_CONF if lang == "zh" else EN_DEFAULT_CONF
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.user_path = USER_CONF
        self.backup_path = BACKUP_CONF
        self.texts_merge = TEXTS_MERGE.get(lang, TEXTS_MERGE["en"])
        self.texts_compare = TEXTS_COMPARE.get(lang, TEXTS_COMPARE["en"])
        self.logger = logger

    def sync_user_config(self) -> None:
        if not os.path.exists(self.user_path):
            self.logger.warning(self.texts["no_config"])
            self.logger.warning(self.texts["copy_default_config"])
            shutil.copy2(self.default_path, self.user_path)
            return

        if self.compare_configs():
            self.logger.info(self.texts["configs_up_to_date"])
        else:
            self.backup_user_config()
            self.merge_and_update_user_config()
        comment_sync = CommentSynchronizer(self.default_path, self.user_path, self.logger, self.yaml)
        comment_sync.sync()

    def backup_user_config(self):
        backup_path = os.path.abspath(self.backup_path)
        self.logger.info(
            self.texts["backup_user_config"].format(
                user_conf=self.user_path, backup_conf=self.backup_path
            )
        )
        self.logger.debug(self.texts["config_backup_path"].format(path=backup_path))
        shutil.copy2(self.user_path, self.backup_path)

    def merge_and_update_user_config(self):
        try:
            new_keys = self.merge_configs()
            if new_keys:
                self.logger.info(self.texts["merged_config_success"])
                for key in new_keys:
                    self.logger.info(f"  - {key}")
            else:
                self.logger.info(self.texts["merged_config_none"])
        except Exception as e:
            self.logger.error(self.texts["merge_failed"].format(error=e))

    def merge_configs(self):
        user_config = self.yaml.load(load_text_file_with_guess_encoding(self.user_path))
        default_config = self.yaml.load(load_text_file_with_guess_encoding(self.default_path))

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

        with open(self.user_path, "w", encoding="utf-8") as f:
            self.yaml.dump(merged, f)

        # Log upgrade details (replacing manual file writing)
        self.logger.info(version_change_string)
        for key in new_keys:
            self.logger.info(self.texts_merge["new_config_item"].format(key=key))
        return new_keys
    
    def collect_all_subkeys(self, d, base_path):
        """Collect all keys in the dictionary d, recursively, with base_path as the prefix."""
        keys = []
        # Only process if d is a dictionary
        if isinstance(d, dict):
            for key, value in d.items():
                current_path = f"{base_path}.{key}" if base_path else key
                keys.append(current_path)
                if isinstance(value, dict):
                    keys.extend(self.collect_all_subkeys(value, current_path))
        return keys

    def get_missing_keys(self, user, default, path=""):
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
                            self.get_missing_keys(user_val, default_val, current_path)
                        )
                    else:
                        subtree_missing = self.collect_all_subkeys(default_val, current_path)
                        missing.extend(subtree_missing)
        return missing
    
    def get_extra_keys(self, user, default, path=""):
        """Recursively find keys in user that are not present in default."""
        extra = []
        for key, user_val in user.items():
            current_path = f"{path}.{key}" if path else key
            if key not in default:
                # Only collect subkeys if the value is a dictionary
                if isinstance(user_val, dict):
                    subtree_extra = self.collect_all_subkeys(user_val, current_path)
                    extra.extend(subtree_extra)
                extra.append(current_path)
            else:
                default_val = default[key]
                if isinstance(user_val, dict) and isinstance(default_val, dict):
                    extra.extend(self.get_extra_keys(user_val, default_val, current_path))
                elif isinstance(user_val, dict):
                    subtree_extra = self.collect_all_subkeys(user_val, current_path)
                    extra.extend(subtree_extra)
        return extra
    
    def delete_extra_keys(self):
        """Delete extra keys in user config that are not present in default config."""

        user_config = self.yaml.load(load_text_file_with_guess_encoding(self.user_path))
        default_config = self.yaml.load(load_text_file_with_guess_encoding(self.default_path))
        extra_keys = self.get_extra_keys(user_config, default_config)

        def delete_key_by_path(config_dict, key_path):
            keys = key_path.split(".")
            sub_dict = config_dict
            for k in keys[:-1]:
                if k in sub_dict and isinstance(sub_dict[k], dict):
                    sub_dict = sub_dict[k]
                else:
                    return False
            return sub_dict.pop(keys[-1], None) is not None

        deleted_keys = []
        for key_path in extra_keys:
            if delete_key_by_path(user_config, key_path):
                deleted_keys.append(key_path)

        with open(self.user_path, "w", encoding="utf-8") as f:
            self.yaml.dump(user_config, f)

        self.logger.info(f"Deleted {len(deleted_keys)} extra keys:")
        for key in deleted_keys:
            self.logger.info(f"  - {key}")

    def compare_configs(self) -> bool:
        """Compare user and default configs, log discrepancies, and return status."""

        user_config = self.yaml.load(load_text_file_with_guess_encoding(self.user_path))
        default_config = self.yaml.load(load_text_file_with_guess_encoding(self.default_path))

        missing = self.get_missing_keys(user_config, default_config)
        extra = self.get_extra_keys(user_config, default_config)

        if missing:
            self.logger.warning(self.texts_compare["missing_keys"].format(keys=", ".join(missing)))
            return False
        if extra:
            self.logger.warning(self.texts_compare["extra_keys"].format(keys=", ".join(extra)))
            self.delete_extra_keys()
        else:
            self.logger.debug(self.texts_compare["up_to_date"])

        return True

