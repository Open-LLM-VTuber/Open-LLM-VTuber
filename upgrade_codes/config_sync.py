import os
import shutil
from upgrade_codes.constants import USER_CONF,BACKUP_CONF,TEXTS
from upgrade_codes.merge_configs import compare_configs, merge_configs

class ConfigSynchronizer:
    def sync_user_config(self, logger, lang: str = "en") -> None:
        texts = TEXTS[lang]
        default_template = (
            "config_templates/conf.ZH.default.yaml"
            if lang == "zh"
            else "config_templates/conf.default.yaml"
        )

        if os.path.exists(USER_CONF):
            if not compare_configs(USER_CONF, default_template, lang):
                try:
                    backup_path = os.path.abspath(BACKUP_CONF)
                    logger.info(
                        texts["backup_user_config"].format(
                            user_conf=USER_CONF, backup_conf=BACKUP_CONF
                        )
                    )
                    logger.debug(texts["config_backup_path"].format(path=backup_path))
                    shutil.copy2(USER_CONF, BACKUP_CONF)

                    new_keys = merge_configs(USER_CONF, default_template, lang)
                    if new_keys:
                        logger.info(texts["merged_config_success"])
                        for key in new_keys:
                            logger.info(f"  - {key}")
                    else:
                        logger.info(texts["merged_config_none"])
                except Exception as e:
                    logger.error(texts["merge_failed"].format(error=e))
            else:
                logger.info(texts["configs_up_to_date"])
        else:
            logger.warning(texts["no_config"])
            logger.warning(texts["copy_default_config"])
            shutil.copy2(default_template, USER_CONF)
