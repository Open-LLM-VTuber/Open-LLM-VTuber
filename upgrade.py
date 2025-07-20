import time
from upgrade_codes.upgrade_manager import UpgradeManager
from upgrade_codes.upgrade_core.constants import TEXTS

upgrade_manager = UpgradeManager()
upgrade_manager.check_user_config_exists()

def run_upgrade():
    logger = upgrade_manager.logger
    start_time = time.time()

    lang = upgrade_manager.lang
    logger.info(TEXTS[lang]["welcome_message"])
    texts = TEXTS[lang]

    logger.info(texts["start_upgrade"])
    upgrade_manager.log_system_info()

    if not upgrade_manager.check_git_installed():
        logger.error(texts["git_not_found"])
        return

    response = input("\033[93m" + texts["operation_preview"] + "\033[0m").lower()
    if response != "y":
        return

    success, error_msg = upgrade_manager.run_command("git rev-parse --is-inside-work-tree")
    if not success:
        logger.error(texts["not_git_repo"])
        logger.error(f"Error details: {error_msg}")
        return

    # Check for unpushed commits (ahead of remote)
    logger.info(texts["checking_ahead_status"])
    success, ahead_behind = upgrade_manager.run_command(
        "git rev-list --left-right --count HEAD...@{upstream}"
    )
    if success:
        ahead, behind = map(int, ahead_behind.strip().split())
        if ahead > 0:
            logger.error(texts["local_ahead"].format(count=ahead))
            logger.error(texts["push_blocked"])
            logger.info(texts["backup_suggestion"])
            logger.warning(texts["abort_upgrade"])
            return

    # Check for uncommitted changes
    logger.info(texts["checking_stash"])
    success, changes = upgrade_manager.run_command("git status --porcelain")
    if not success:
        logger.error(f"Failed to check git status: {changes}")
        return

    has_changes = bool(changes.strip())
    if has_changes:
        change_count = len([line for line in changes.strip().split("\n") if line])
        logger.debug(texts["detected_changes"].format(count=change_count))
        logger.warning(texts["uncommitted"])

        operation, elapsed = upgrade_manager.time_operation(upgrade_manager.run_command, "git stash")
        success, output = operation
        logger.debug(
            texts["operation_time"].format(operation="git stash", time=elapsed)
        )

        if not success:
            logger.error(texts["stash_error"])
            logger.error(f"Error details: {output}")
            return
        logger.info(texts["changes_stashed"])

    # Check remote status
    logger.info(texts["checking_remote"])
    operation, elapsed = upgrade_manager.time_operation(upgrade_manager.run_command, "git fetch")
    success, output = operation
    logger.debug(texts["operation_time"].format(operation="git fetch", time=elapsed))

    if success:
        success, ahead_behind = upgrade_manager.run_command(
            "git rev-list --left-right --count HEAD...@{upstream}"
        )
        if success:
            ahead, behind = ahead_behind.strip().split()
            if int(behind) > 0:
                logger.info(texts["remote_behind"].format(count=behind))
            else:
                logger.info(texts["remote_ahead"])

    # Pull updates
    logger.info(texts["pulling"])
    operation, elapsed = upgrade_manager.time_operation(upgrade_manager.run_command, "git pull")
    success, output = operation
    logger.debug(texts["operation_time"].format(operation="git pull", time=elapsed))

    if not success:
        logger.error(texts["pull_error"])
        logger.error(f"Error details: {output}")
        if has_changes:
            logger.warning(texts["restoring"])
            success, restore_output = upgrade_manager.run_command("git stash pop")
            if not success:
                logger.error(f"Failed to restore changes: {restore_output}")
        return

    # Update submodules
    submodules = upgrade_manager.get_submodule_list()
    if submodules:
        logger.info(texts["updating_submodules"])
        
        operation, elapsed = upgrade_manager.time_operation(
            upgrade_manager.run_command, "git submodule update --init --recursive"
        )
        success, output = operation
        logger.debug(
            texts["operation_time"].format(operation="git submodule update", time=elapsed)
        )
        
        if not success:
            logger.error(texts["submodule_update_error"])
            logger.error(f"Error details: {output}")
        else:
            for submodule in submodules:
                logger.debug(texts["submodule_updated"].format(submodule=submodule))
    else:
        logger.info(texts["no_submodules"])


    # Update config
    upgrade_manager.sync_user_config()
    upgrade_manager.update_user_config()

    if has_changes:
        logger.warning(texts["restoring"])
        operation, elapsed = upgrade_manager.time_operation(upgrade_manager.run_command, "git stash pop")
        success, output = operation
        logger.debug(
            texts["operation_time"].format(operation="git stash pop", time=elapsed)
        )

        if not success:
            logger.error(texts["conflict_warning"])
            logger.error(f"Error details: {output}")
            logger.warning(texts["manual_resolve"])
            logger.info(texts["stash_list"])
            logger.info(texts["stash_pop"])
            return

    end_time = time.time()
    total_elapsed = end_time - start_time
    logger.info(texts["finish_upgrade"].format(time=total_elapsed))

    logger.info(texts["upgrade_complete"])
    logger.info(texts["check_config"])
    logger.info(texts["resolve_conflicts"])
    logger.info(texts["check_backup"])

if __name__ == "__main__":
    run_upgrade()