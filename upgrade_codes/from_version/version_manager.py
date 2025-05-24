from upgrade_codes.from_version.v_1_1_1 import to_v_1_2_0

class VersionUpgradeManager:
    def __init__(self, logger=None):
        self.logger = logger
        self.routes = {
            "1.1.1": self._upgrade_1_1_1_to_1_2_0,
        }

    def upgrade(self, version: str, model_dict: dict) -> dict:
        return self.routes.get(version, lambda x: x)(model_dict)

    def _upgrade_1_1_1_to_1_2_0(self, model_dict: dict) -> dict:
        # legacy model_dict is a list, new one should be dict with models + version
        if isinstance(model_dict, list):
            return to_v_1_2_0(model_dict).upgrade()
        return model_dict  # if it's already structured, return as-is