import json
from pathlib import Path
from packaging.version import parse as parse_version
from upgrade_codes.upgrade_core.constants import USER_CONF, UPGRADE_TEXTS
from upgrade_codes.from_version.v_1_1_1 import to_v_1_2_0
# from upgrade_codes.from_version.v_1_2_0 import to_v_1_3_0  # future upgrade


class VersionUpgradeManager:
    def __init__(self, language, logger):
        self.logger = logger
        self.language = language
        self.log_texts = UPGRADE_TEXTS.get(language, UPGRADE_TEXTS["en"])
        self.indent_spaces = 4
        self.user_config = USER_CONF

    def get_upgrade_mapping(self):
        """
        Define version upgrade tasks using version ranges.
        Each task maps a range [from_version, to_version) to a specific upgrade module.
        """
        return [
            {
                "from_range": (
                    "v1.1.1",
                    "v1.2.0",
                ),  # Inclusive lower bound, exclusive upper bound
                "from_version": "v1.1.1",
                "to_version": "v1.2.0",
                "module": to_v_1_2_0,
            },
            # Future upgrade example:
            # {
            #     "from_range": ("v1.2.0", "v1.3.0"),
            #     "from_version": "v1.2.0",
            #     "to_version": "v1.3.0",
            #     "module": to_v_1_3_0,
            # },
        ]

    def resolve_upgrade_task(self, current_version: str):
        """
        Determine which upgrade task applies to the given current_version.
        Returns a tuple of (from_version, to_version, module) if matched, else None.
        """
        parsed_current = parse_version(current_version.strip("v"))
        for task in self.get_upgrade_mapping():
            low = parse_version(task["from_range"][0].strip("v"))
            high = parse_version(task["from_range"][1].strip("v"))
            if low <= parsed_current < high:
                return task["from_version"], task["to_version"], task["module"]
        return None

    def upgrade(self, current_version: str) -> str:
        """
        Perform the upgrade process starting from current_version.
        If a matching version range is found, run the corresponding upgrade module.
        """
        task = self.resolve_upgrade_task(current_version)
        if not task:
            self.logger.info(
                self.log_texts["no_upgrade_routine"].format(version=current_version)
            )
            return current_version

        from_version, to_version, module = task
        self.logger.info(
            self.log_texts["upgrading_path"].format(
                from_version=current_version, to_version=to_version
            )
        )
        upgraded_version = current_version

        try:
            model_path = Path("model_dict.json")
            with open(model_path, "r", encoding="utf-8") as f:
                model_dict = json.load(f)

            if isinstance(model_dict, list):
                new_data = module(model_dict, self.user_config, self.language).upgrade()
                with open(model_path, "w", encoding="utf-8") as f:
                    json.dump(
                        new_data, f, indent=self.indent_spaces, ensure_ascii=False
                    )

                upgraded_version = to_version
                self.logger.info(
                    self.log_texts["upgrade_success"].format(language=self.language)
                )
            else:
                self.logger.info(self.log_texts["already_latest"])
        except Exception as e:
            self.logger.error(self.log_texts["upgrade_error"].format(error=e))

        return upgraded_version
