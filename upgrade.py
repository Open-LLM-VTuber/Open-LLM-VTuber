import os
import sys
import platform
import subprocess
import time
from upgrade_codes.manager import UpgradeManager
from upgrade_codes.constants import TEXTS

upgrade_manager = UpgradeManager()

def run_command(command):
    """Run shell command and return result"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return (
            False,
            f"Command failed with error code {e.returncode}\nError: {e.stderr}",
        )
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def check_git_installed():
    """Check if Git is installed"""
    command = "where git" if sys.platform == "win32" else "which git"
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.SubprocessError:
        return False


def log_system_info(logger, lang):
    """Log detailed system information"""
    texts = TEXTS[lang]

    # Log OS info
    os_name = platform.system()
    os_version = platform.version()
    python_version = platform.python_version()
    logger.info(
        texts["env_info"].format(
            os_name=os_name, os_version=os_version, python_version=python_version
        )
    )

    # Log Git version
    success, git_version = run_command("git --version")
    if success:
        logger.info(texts["git_version"].format(git_version=git_version.strip()))

    # Log current branch
    success, branch = run_command("git branch --show-current")
    if success:
        logger.info(texts["current_branch"].format(branch=branch.strip()))


def time_operation(func, *args, **kwargs):
    """Time an operation and return result with timing information"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    elapsed = end_time - start_time
    return result, elapsed


def get_submodule_list():
    """Get a list of submodules"""
    if not os.path.exists(".gitmodules"):
        return []

    success, output = run_command("git config --file .gitmodules --get-regexp path")
    if not success:
        return []

    submodules = []
    for line in output.strip().split("\n"):
        if line:
            parts = line.strip().split(" ", 1)
            if len(parts) >= 2:
                submodules.append(parts[1])

    return submodules


def has_submodules():
    """Check if the repository has submodules by looking for .gitmodules file"""
    return os.path.exists(".gitmodules")


def perform_upgrade(custom_logger=None):
    logger = custom_logger or upgrade_manager.logger
    start_time = time.time()

    logger.info(TEXTS["en"]["welcome_message"])
    lang = upgrade_manager.lang
    texts = TEXTS[lang]

    logger.info(texts["start_upgrade"])
    log_system_info(logger, lang)

    if not check_git_installed():
        logger.error(texts["git_not_found"])
        return

    response = input("\033[93m" + texts["operation_preview"] + "\033[0m").lower()
    if response != "y":
        logger.warning(texts["abort_upgrade"])
        return

    success, error_msg = run_command("git rev-parse --is-inside-work-tree")
    if not success:
        logger.error(texts["not_git_repo"])
        logger.error(f"Error details: {error_msg}")
        return

    # Check for uncommitted changes
    logger.info(texts["checking_stash"])
    success, changes = run_command("git status --porcelain")
    if not success:
        logger.error(f"Failed to check git status: {changes}")
        return

    has_changes = bool(changes.strip())
    if has_changes:
        change_count = len([line for line in changes.strip().split("\n") if line])
        logger.debug(texts["detected_changes"].format(count=change_count))
        logger.warning(texts["uncommitted"])

        operation, elapsed = time_operation(run_command, "git stash")
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
    operation, elapsed = time_operation(run_command, "git fetch")
    success, output = operation
    logger.debug(texts["operation_time"].format(operation="git fetch", time=elapsed))

    if success:
        success, ahead_behind = run_command(
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
    operation, elapsed = time_operation(run_command, "git pull")
    success, output = operation
    logger.debug(texts["operation_time"].format(operation="git pull", time=elapsed))

    if not success:
        logger.error(texts["pull_error"])
        logger.error(f"Error details: {output}")
        if has_changes:
            logger.warning(texts["restoring"])
            success, restore_output = run_command("git stash pop")
            if not success:
                logger.error(f"Failed to restore changes: {restore_output}")
        return

    # Update submodules
    submodules = get_submodule_list()
    if submodules:
        logger.info(texts["updating_submodules"])

        # First update all submodules
        operation, elapsed = time_operation(
            run_command, "git submodule update --init --recursive"
        )
        success, output = operation
        logger.debug(
            texts["operation_time"].format(operation="submodule update", time=elapsed)
        )

        if not success:
            logger.error(texts["submodule_error"])
            logger.error(f"Error details: {output}")
        else:
            logger.info(texts["submodules_updated"])

            # Log individual submodule details
            for submodule in submodules:
                logger.debug(texts["submodule_updated"].format(submodule=submodule))
    else:
        logger.info(texts["no_submodules"])

    # Update config
    upgrade_manager.sync_user_config()

    if has_changes:
        logger.warning(texts["restoring"])
        operation, elapsed = time_operation(run_command, "git stash pop")
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

    logger.info("\n" + texts["upgrade_complete"])
    logger.info(texts["check_config"])
    logger.info(texts["resolve_conflicts"])
    logger.info(texts["check_backup"])


if __name__ == "__main__":
    perform_upgrade()
