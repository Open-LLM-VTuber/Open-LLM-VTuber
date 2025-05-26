import copy
import yaml

class to_v_1_2_0:
    def __init__(self, old_model_list: list, conf_yaml_path: str):
        """
        :param old_model_list: list of dicts (each representing a Live2D model config)
        :param conf_yaml_path: path to conf.yaml that should be upgraded
        """
        self.old_models = old_model_list
        self.conf_yaml_path = conf_yaml_path

    def upgrade(self) -> dict:
        """
        Return upgraded model_dict structure including 'models' list and new version
        And perform in-place upgrade of conf.yaml
        """
        upgraded_models = self._upgrade_models(self.old_models)
        self._upgrade_conf_yaml()
        return upgraded_models

    def _upgrade_models(self, old_model_list: list) -> list:
        deprecated = {"other_unit_90001", "player_unit_00003", "mashiro"}
        upgrades = {"shizuku-local", "shizuku", "mao_pro"}
        new_models = []

        for model in old_model_list:
            name = model.get("name")
            if name in deprecated:
                continue

            upgraded = copy.deepcopy(model)

            if name in upgrades:
                if name.startswith("shizuku"):
                    upgraded["url"] = "/live2d-models/shizuku/runtime/shizuku.model3.json"
                elif name == "mao_pro":
                    upgraded["url"] = "/live2d-models/mao_pro/runtime/mao_pro.model3.json"
                    upgraded["kScale"] = 0.5

                if "idleMotionGroupName" in upgraded:
                    upgraded["idleMotionGroupName"] = upgraded["idleMotionGroupName"].capitalize()

                if name == "shizuku":
                    upgraded["description"] = "Orange-Haired Girl. Same as shizuku-local. Kept for compatibility."

            new_models.append(upgraded)

        return new_models

    def _upgrade_conf_yaml(self):
        try:
            with open(self.conf_yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Step 1: update version
            if "system_config" in data:
                data["system_config"]["conf_version"] = "1.2.0"

            # Step 2: set vad_config.silero_vad = None
            if data.get("vad_config", {}).get("vad_model") == "silero_vad":
                data["vad_config"]["silero_vad"] = None

            with open(self.conf_yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

        except Exception as e:
            raise RuntimeError(f"Failed to upgrade conf.yaml: {e}")
