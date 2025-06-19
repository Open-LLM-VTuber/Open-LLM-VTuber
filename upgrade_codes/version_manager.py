import json
from pathlib import Path
from upgrade_codes.upgrade_core.constants import USER_CONF, UPGRADE_TEXTS
from upgrade_codes.from_version.v_1_1_1 import to_v_1_2_0
# from upgrade_codes.from_version.v_1_2_0 import to_v_1_2_1 # Future update

class VersionUpgradeManager:
    def __init__(self, language, logger):
        self.logger = logger
        self.language = language
        self.log_texts = UPGRADE_TEXTS.get(language, UPGRADE_TEXTS["en"])
        self.indent_spaces = 4
        self.user_config = USER_CONF
        
        self.upgrade_chain = [
            ("v1.1.1", "v1.2.0", to_v_1_2_0),
            # ("v1.2.0", "v1.2.1", to_v_1_2_1),  # future update
        ]

    def upgrade(self, current_version: str) -> str:
        upgraded_version = current_version
        upgraded = False

        for from_version, to_version, module in self.upgrade_chain:
            if upgraded_version == from_version:
                self.logger.info(self.log_texts["upgrading_path"].format(from_version=from_version, to_version=to_version))
                try:
                    model_path = Path("model_dict.json")
                    with open(model_path, "r", encoding="utf-8") as f:
                        model_dict = json.load(f)

                    if isinstance(model_dict, list):
                        new_data = module(model_dict, self.user_config, self.language).upgrade()
                        with open(model_path, "w", encoding="utf-8") as f:
                            json.dump(new_data, f, indent=self.indent_spaces, ensure_ascii=False)

                        upgraded_version = to_version
                        self.logger.info(self.log_texts["upgrade_success"].format(language=self.language))
                        upgraded = True
                    else:
                        self.logger.info(self.log_texts["already_latest"])
                        break
                except Exception as e:
                    self.logger.error(self.log_texts["upgrade_error"].format(error=e))
                    break

        if not upgraded:
            self.logger.info(self.log_texts["no_upgrade_routine"].format(version=current_version))

        return upgraded_version
