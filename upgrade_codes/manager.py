# upgrade/manager.py
from upgrade_codes.language import select_language
from upgrade_codes.config_sync import ConfigSynchronizer
from upgrade_codes.logger import configure_logging

class UpgradeManager:
    def __init__(self):
        self.lang = select_language()
        self.logger = configure_logging()
        self.config_sync = ConfigSynchronizer()

    def sync_user_config(self):
        self.config_sync.sync_user_config(logger=self.logger, lang=self.lang)