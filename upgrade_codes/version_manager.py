import json
from pathlib import Path
from upgrade_codes.upgrade_core.constants import USER_CONF, UPGRADE_TEXTS
from upgrade_codes.from_version.v_1_1_1 import to_v_1_2_0

class VersionUpgradeManager:
    def __init__(self, language: str = "zh", logger=None):
        """
        :param language: language of the configuration ("zh" or "en")
        :param logger: logger instance for logging messages
        """
        self.logger = logger
        self.routes = {
            "v1.1.1": self._upgrade_1_1_1_to_1_2_0,
        }
        self.user_config = USER_CONF
        self.indent_spaces = 4
        self.language = language
        self.log_texts = UPGRADE_TEXTS.get(self.language, UPGRADE_TEXTS["en"])

    def upgrade(self, version: str) -> None:
        upgrade_fn = self.routes.get(version)
        if upgrade_fn:
            upgrade_fn()
        else:
            if self.logger:
                log_text = self.log_texts["no_upgrade_routine"].format(version=version)
                self.logger.info(log_text)

    def _upgrade_1_1_1_to_1_2_0(self):
        def _load_model_dict(path: Path):
            if not path.exists():
                if self.logger:
                    log_text = self.log_texts["model_dict_not_found"]
                    self.logger.warning(log_text)
                return None

            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                if self.logger:
                    log_text = self.log_texts["model_dict_read_error"].format(error=e)
                    self.logger.error(log_text)
                return None
                
        model_path = Path("model_dict.json")
        model_dict = _load_model_dict(model_path)

        if model_dict is None:
            return

        try:
            if isinstance(model_dict, list):
                new_data = to_v_1_2_0(model_dict, self.user_config, self.language).upgrade()
                with open(model_path, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=self.indent_spaces, ensure_ascii=False)
                if self.logger:
                    log_text = self.log_texts["upgrade_success"].format(language=self.language)
                    self.logger.info(log_text)
            else:
                if self.logger:
                    log_text = self.log_texts["already_latest"]
                    self.logger.info(log_text)
        except Exception as e:
            if self.logger:
                log_text = self.log_texts["upgrade_error"].format(error=e)
                self.logger.error(log_text)