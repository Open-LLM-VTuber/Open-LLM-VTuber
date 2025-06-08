# upgrade/manager.py
from upgrade_codes.upgrade_core.language import select_language
from upgrade_codes.config_sync import ConfigSynchronizer
from upgrade_codes.upgrade_core.logger import configure_logging
from upgrade_codes.upgrade_core.upgrade_utils import UpgradeUtility

class UpgradeManager:
    def __init__(self):
        self.lang = select_language()
        self.logger = configure_logging()
        self.upgrade_utils = UpgradeUtility(self.logger, self.lang)
        self.config_sync = ConfigSynchronizer(self.lang, self.logger)

    def sync_user_config(self):
        self.config_sync.sync_user_config()

    def update_user_config(self):
        self.config_sync.update_user_config()

    def log_system_info(self):
        return self.upgrade_utils.log_system_info()

    def check_git_installed(self):
        return self.upgrade_utils.check_git_installed()

    def run_command(self, command):
        return self.upgrade_utils.run_command(command)

    def time_operation(self, func, *args, **kwargs):
        return self.upgrade_utils.time_operation(func, *args, **kwargs)

    def get_submodule_list(self):
        return self.upgrade_utils.get_submodule_list()

    def has_submodules(self):
        return self.upgrade_utils.has_submodules()