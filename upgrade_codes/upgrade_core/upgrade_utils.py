import os
import platform
import subprocess
import sys
import time
from upgrade_codes.upgrade_core.constants import TEXTS, TEXTS_COMPARE
from typing import Callable, Any


class UpgradeUtility:
    def __init__(self, logger, lang):
        self.logger = logger
        self.lang = lang
        self.texts = TEXTS[lang]
        self.texts_compare = TEXTS_COMPARE[lang]

    def run_command(self, command):
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

    def check_git_installed(self):
        """Check if Git is installed"""
        command = "where git" if sys.platform == "win32" else "which git"
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False

    def log_system_info(self):
        """Log detailed system information"""
        texts = self.texts

        # Log OS info
        os_name = platform.system()
        os_version = platform.version()
        python_version = platform.python_version()
        self.logger.info(
            texts["env_info"].format(
                os_name=os_name, os_version=os_version, python_version=python_version
            )
        )

        # Log Git version
        success, git_version = self.run_command("git --version")
        if success:
            self.logger.info(
                texts["git_version"].format(git_version=git_version.strip())
            )

        # Log current branch
        success, branch = self.run_command("git branch --show-current")
        if success:
            self.logger.info(texts["current_branch"].format(branch=branch.strip()))

    def time_operation(self, func, *args, **kwargs):
        """Time an operation and return result with timing information"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed = end_time - start_time
        return result, elapsed

    def get_submodule_list(self):
        """Get a list of submodules"""
        if not os.path.exists(".gitmodules"):
            return []

        success, output = self.run_command(
            "git config --file .gitmodules --get-regexp path"
        )
        if not success:
            return []

        submodules = []
        for line in output.strip().split("\n"):
            if line:
                parts = line.strip().split(" ", 1)
                if len(parts) >= 2:
                    submodules.append(parts[1])

        return submodules

    def has_submodules(self):
        """Check if the repository has submodules by looking for .gitmodules file"""
        return os.path.exists(".gitmodules")

    def compare_dicts(
        self,
        name: str,
        get_a: Callable[[], Any],
        get_b: Callable[[], Any],
        compare_fn: Callable[[Any, Any], Any],
    ) -> bool:
        try:
            a = get_a()
            b = get_b()
            comparison_result = compare_fn(a, b)

            if isinstance(comparison_result, tuple):
                is_equal, differences = comparison_result
            else:
                is_equal, differences = comparison_result, []

            if is_equal:
                msg = self.texts_compare.get(
                    "compare_passed", "[DEBUG] {name} comparison passed."
                )
                self.logger.debug(msg.format(name=name))
                return True
            else:
                msg = self.texts_compare.get(
                    "compare_failed",
                    "[WARNING] {name} comparison failed: configs differ.",
                )
                self.logger.warning(msg.format(name=name))
                if differences:
                    for item in differences:
                        self.logger.warning(
                            self.texts_compare.get(
                                "compare_diff_item", "- {item}"
                            ).format(item=item)
                        )
                return False
        except Exception as e:
            msg = self.texts_compare.get(
                "compare_error", "[ERROR] {name} comparison error: {error}"
            )
            self.logger.error(msg.format(name=name, error=e))
            return False
