import os
import shutil
from upgrade_codes.upgrade_core.constants import USER_CONF,BACKUP_CONF,TEXTS, ZH_DEFAULT_CONF, EN_DEFAULT_CONF, TEXTS_COMPARE, TEXTS_MERGE
import logging
from ruamel.yaml import YAML
from src.open_llm_vtuber.config_manager.utils import load_text_file_with_guess_encoding
from upgrade_codes.upgrade_core.comment_sync import CommentSynchronizer
from upgrade_codes.version_manager import VersionUpgradeManager
from upgrade_codes.upgrade_core.upgrade_utils import UpgradeUtility
from upgrade_codes.upgrade_core.comment_diff_fn import comment_diff_fn

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
        self.upgrade_utils = UpgradeUtility(self.logger, self.lang)

    def sync_user_config(self) -> None:
        if not os.path.exists(self.user_path):
            self.logger.warning(self.texts["no_config"])
            self.logger.warning(self.texts["copy_default_config"])
            shutil.copy2(self.default_path, self.user_path)
            return

        if not self.compare_field_keys():
            self.backup_user_config()
            self.merge_and_update_user_config()
        else:
            self.logger.info(self.texts["configs_up_to_date"])

        if not self.compare_comments():
            comment_sync = CommentSynchronizer(
                self.default_path,
                self.user_path,
                self.logger,
                self.yaml,
                self.texts_compare
            )
            comment_sync.sync()
        else:
            self.logger.info(self.texts_compare["comments_up_to_date"])

        self.upgrade_version_if_needed()



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

        with open(self.user_path, "w", encoding="utf-8") as f:
            self.yaml.dump(merged, f)

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

        self.logger.info(self.texts_compare["extra_keys_deleted_count"].format(count=len(deleted_keys)))
        for key in deleted_keys:
            self.logger.info(self.texts_compare["extra_keys_deleted_item"].format(key=key))

    def compare_field_keys(self) -> bool:
        """Compare field structure differences (missing/extra keys)"""
        def field_compare_fn(user, default):
            missing = self.get_missing_keys(user, default)
            extra = self.get_extra_keys(user, default)

            if missing:
                self.logger.warning(self.texts_compare["missing_keys"].format(keys=", ".join(missing)))
            if extra:
                self.logger.warning(self.texts_compare["extra_keys"].format(keys=", ".join(extra)))
                self.delete_extra_keys()
            return (not missing, missing + extra)

        return self.upgrade_utils.compare_dicts(
            name="keys",
            get_a=lambda: self.yaml.load(load_text_file_with_guess_encoding(self.user_path)),
            get_b=lambda: self.yaml.load(load_text_file_with_guess_encoding(self.default_path)),
            compare_fn=field_compare_fn
        )

    def compare_comments(self) -> bool:
        return self.upgrade_utils.compare_dicts(
            name="comments",
            get_a=lambda: load_text_file_with_guess_encoding(self.user_path),
            get_b=lambda: load_text_file_with_guess_encoding(self.default_path),
            compare_fn=comment_diff_fn
        )
        
    def upgrade_version_if_needed(self):
        try:
            with open(self.user_path, "r", encoding="utf-8") as f:
                user_config = self.yaml.load(f)

            current_version = user_config.get("system_config", {}).get("conf_version", "")

            with open(self.default_path, "r", encoding="utf-8") as f:
                default_config = self.yaml.load(f)
            latest_version = default_config.get("system_config", {}).get("conf_version", "")

            if current_version == latest_version:
                self.logger.info(self.texts["version_upgrade_none"].format(version=current_version))
                return

            VersionUpgradeManager(self.logger).upgrade(current_version)

            self.logger.info(self.texts["version_upgrade_success"].format(old=current_version, new=latest_version))

        except Exception as e:
            self.logger.error(self.texts["version_upgrade_failed"].format(error=e))




