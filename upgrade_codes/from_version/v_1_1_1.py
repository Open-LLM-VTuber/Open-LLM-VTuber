import copy
import yaml


class to_v_1_2_0:
    def __init__(self, old_model_list, conf_yaml_path, language):
        """
        :param old_model_list: list of dicts (each representing a Live2D model config)
        :param conf_yaml_path: path to conf.yaml that should be upgraded
        :param language: language of the configuration ("zh" or "en")
        """
        self.old_models = old_model_list
        self.conf_yaml_path = conf_yaml_path
        self.language = language

        # Configuration migration mapping table (language-specific)
        self.migration_map = {
            "zh": {
                "shizuku.png": "mao.png",
                "Shizuku": "Mao",
                "shizuku-local": "mao_pro",
                "shizuku-local-001": "mao_pro_001",
                "distil-medium.en": "large-v3-turbo",
                "en": "zh",
                "v1.1.1": "v1.2.0",
            },
            "en": {
                "shizuku.png": "mao.png",
                "Shizuku": "Mao",
                "shizuku-local": "mao_pro",
                "shizuku-local-001": "mao_pro_001",
                "distil-medium.en": "large-v3-turbo",
                "v1.1.1": "v1.2.0",
            },
        }

    def upgrade(self):
        """
        Return upgraded model_dict structure including 'models' list and new version
        And perform in-place upgrade of conf.yaml
        """
        upgraded_models = self._upgrade_live2d_models(self.old_models)
        self._upgrade_conf_yaml()
        return upgraded_models

    def _upgrade_live2d_models(self, old_model_list: list) -> list:
        deprecated = {
            "other_unit_90001",
            "player_unit_00003",
            "mashiro",
            "shizuku-local",
            "shizuku",
        }
        upgrades = {"mao_pro"}
        new_models = []

        for model in old_model_list:
            name = model.get("name")
            if name in deprecated:
                continue

            upgraded = copy.deepcopy(model)

            if name in upgrades:
                if name == "mao_pro":
                    upgraded["url"] = (
                        "/live2d-models/mao_pro/runtime/mao_pro.model3.json"
                    )
                    upgraded["kScale"] = 0.5

            new_models.append(upgraded)

        return new_models

    def _upgrade_conf_yaml(self):
        try:
            with open(self.conf_yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Update system version number
            if "system_config" in data and isinstance(data["system_config"], dict):
                data["system_config"]["conf_version"] = "v1.2.0"

            # Update VAD config
            vad_config = data.get("character_config", {}).get("vad_config", {})
            if vad_config.get("vad_model") == "silero_vad":
                vad_config["vad_model"] = None

            # Update role-related configurations
            char_config = data.get("character_config", {})
            self._migrate_field(char_config, "avatar")
            self._migrate_field(char_config, "character_name")
            self._migrate_field(char_config, "conf_name")
            self._migrate_field(char_config, "conf_uid")
            self._migrate_field(char_config, "live2d_model_name")

            # Update ASR config
            asr_config = char_config.get("asr_config", {}).get("faster_whisper", {})
            self._migrate_field(asr_config, "model_path")

            if self.language == "zh":
                self._migrate_field(asr_config, "language")

            with open(self.conf_yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    data, f, allow_unicode=True, sort_keys=False, default_style="'"
                )  # Auto formatting with '

        except Exception as e:
            raise RuntimeError(f"Failed to upgrade conf.yaml: {e}")

    def _migrate_field(self, config_section: dict, field_name: str):
        if field_name in config_section:
            current_value = config_section[field_name]
            lang_map = self.migration_map.get(self.language, {})
            new_value = lang_map.get(current_value, current_value)
            config_section[field_name] = new_value
