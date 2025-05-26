import json
from pathlib import Path
from upgrade_codes.from_version.v_1_1_1 import to_v_1_2_0
from upgrade_codes.upgrade_core.constants import USER_CONF

class VersionUpgradeManager:
    def __init__(self, logger=None):
        self.logger = logger
        self.routes = {
            "v1.1.1": self._upgrade_1_1_1_to_1_2_0,
        }
        self.user_config = USER_CONF

    def upgrade(self, version: str) -> None:
        upgrade_fn = self.routes.get(version)
        if upgrade_fn:
            upgrade_fn()
        else:
            if self.logger:
                self.logger.info(f"No upgrade routine for version {version}")

    def _upgrade_1_1_1_to_1_2_0(self):
        def _load_model_dict(self, path: Path):
            if not path.exists():
                if self.logger:
                    self.logger.warning("⚠️ model_dict.json not found. Skipping upgrade.")
                return None

            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"❌ Failed to read model_dict.json: {e}")
                return None
        model_path = Path("model_dict.json")
        model_dict = _load_model_dict(model_path)

        if model_dict is None:
            return

        try:
            if isinstance(model_dict, list):
                new_data = to_v_1_2_0(model_dict, self.user_config).upgrade()
                with open(model_path, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2, ensure_ascii=False)
                if self.logger:
                    self.logger.info("✅ model_dict.json upgraded to v1.2.0 format.")
            else:
                if self.logger:
                    self.logger.info("model_dict.json already in latest format.")
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Failed to upgrade model_dict.json: {e}")