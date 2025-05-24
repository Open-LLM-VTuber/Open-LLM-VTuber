import copy

class to_v_1_2_0:
    def __init__(self, old_model_list: list):
        """
        :param old_model_list: list of dicts (each representing a Live2D model config)
        """
        self.old_models = old_model_list

    def upgrade(self) -> dict:
        """
        Return upgraded model_dict structure including 'models' list and new version
        """
        upgraded_models = self._upgrade_models(self.old_models)

        return {
            "models": upgraded_models,
            "conf_version": "1.2.0"
        }

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
