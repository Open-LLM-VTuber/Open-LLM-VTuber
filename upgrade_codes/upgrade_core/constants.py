# upgrade/constants.py
# CURRENT_SCRIPT_VERSION = "0.2.0"
from ruamel.yaml import YAML
from src.open_llm_vtuber.config_manager.utils import load_text_file_with_guess_encoding

USER_CONF = "conf.yaml"
BACKUP_CONF = "conf.yaml.backup"

ZH_DEFAULT_CONF = "config_templates/conf.ZH.default.yaml"
EN_DEFAULT_CONF = "config_templates/conf.default.yaml"

yaml = YAML()
user_config = yaml.load(load_text_file_with_guess_encoding(EN_DEFAULT_CONF ))
CURRENT_SCRIPT_VERSION = user_config.get("system_config", {}).get("conf_version")

TEXTS = {
    "zh": {
        # "welcome_message": f"Auto-Upgrade Script {CURRENT_SCRIPT_VERSION}\nOpen-LLM-VTuber 升级脚本 - 此脚本仍在实验阶段，可能无法按预期工作。",
        "welcome_message": f"正在从 {CURRENT_SCRIPT_VERSION} 自动升级...",
        # "lang_select": "请选择语言/Please select language (zh/en):",
        # "invalid_lang": "无效的语言选择，使用英文作为默认语言",
        "not_git_repo": "错误：当前目录不是git仓库。请进入 Open-LLM-VTuber 目录后再运行此脚本。\n当然，更有可能的是你下载的Open-LLM-VTuber不包含.git文件夹 (如果你是透过下载压缩包而非使用 git clone 命令下载的话可能会造成这种情况)，这种情况下目前无法用脚本升级。",
        "backup_user_config": "正在备份 {user_conf} 到 {backup_conf}",
        "configs_up_to_date": "[DEBUG] 用户配置已是最新。",
        "no_config": "警告：未找到conf.yaml文件",
        "copy_default_config": "正在从模板复制默认配置",
        "uncommitted": "发现未提交的更改，正在暂存...",
        "stash_error": "错误：无法暂存更改",
        "changes_stashed": "更改已暂存",
        "pulling": "正在从远程仓库拉取更新...",
        "pull_error": "错误：无法拉取更新",
        "restoring": "正在恢复暂存的更改...",
        "conflict_warning": "警告：恢复暂存的更改时发生冲突",
        "manual_resolve": "请手动解决冲突",
        "stash_list": "你可以使用 'git stash list' 查看暂存的更改",
        "stash_pop": "使用 'git stash pop' 恢复更改",
        "upgrade_complete": "升级完成！",
        "check_config": "1. 请检查conf.yaml是否需要更新",
        "resolve_conflicts": "2. 如果有配置文件冲突，请手动解决",
        "check_backup": "3. 检查备份的配置文件以确保没有丢失重要设置",
        "git_not_found": "错误：未检测到 Git。请先安装 Git:\nWindows: https://git-scm.com/download/win\nmacOS: brew install git\nLinux: sudo apt install git",
        "operation_preview": """
此脚本将执行以下操作：
1. 备份当前的 conf.yaml 配置文件
2. 暂存所有未提交的更改 (git stash)
3. 从远程仓库拉取最新代码 (git pull)
4. 尝试恢复之前暂存的更改 (git stash pop)

是否继续？(y/N): """,
        "abort_upgrade": "升级已取消",
        "merged_config_success": "新增配置项已合并:",
        "merged_config_none": "未发现新增配置项。",
        "merge_failed": "配置合并失败: {error}",
        "updating_submodules": "正在更新子模块...",
        "submodules_updated": "子模块更新完成",
        "submodule_error": "更新子模块时出错",
        "no_submodules": "未检测到子模块，跳过更新",
        "env_info": "系统环境: {os_name} {os_version}, Python {python_version}",
        "git_version": "Git 版本: {git_version}",
        "current_branch": "当前分支: {branch}",
        "operation_time": "操作 '{operation}' 完成, 耗时: {time:.2f} 秒",
        "checking_stash": "检查是否有未提交的更改...",
        "detected_changes": "检测到 {count} 个文件有更改",
        "submodule_updating": "正在更新子模块: {submodule}",
        "submodule_updated": "子模块已更新: {submodule}",
        "checking_remote": "正在检查远程仓库状态...",
        "remote_ahead": "本地版本已是最新",
        "remote_behind": "发现 {count} 个新提交可供更新",
        "config_backup_path": "配置备份路径: {path}",
        "start_upgrade": "开始升级流程...",
        "version_upgrade_success": "配置版本已成功升级: {old} → {new}",
        "version_upgrade_none": "无需升级配置，当前版本为 {version}",
        "version_upgrade_failed": "升级配置时出错: {error}",
        "finish_upgrade": "升级流程结束, 总耗时: {time:.2f} 秒",
    },
    "en": {
        # "welcome_message": f"Auto-Upgrade Script {CURRENT_SCRIPT_VERSION}\nOpen-LLM-VTuber upgrade script - This script is highly experimental and may not work as expected.",
        "welcome_message": f"Starting auto upgrade from {CURRENT_SCRIPT_VERSION}...",
        # "lang_select": "请选择语言/Please select language (zh/en):",
        # "invalid_lang": "Invalid language selection, using English as default",
        "not_git_repo": "Error: Current directory is not a git repository. Please run this script inside the Open-LLM-VTuber directory.\nAlternatively, it is likely that the Open-LLM-VTuber you downloaded does not contain the .git folder (this can happen if you downloaded a zip archive instead of using git clone), in which case you cannot upgrade using this script.",
        "backup_user_config": "Backing up {user_conf} to {backup_conf}",
        "configs_up_to_date": "[DEBUG] User configuration is up-to-date.",
        "no_config": "Warning: conf.yaml not found",
        "copy_default_config": "Copying default configuration from template",
        "uncommitted": "Found uncommitted changes, stashing...",
        "stash_error": "Error: Unable to stash changes",
        "changes_stashed": "Changes stashed",
        "pulling": "Pulling updates from remote repository...",
        "pull_error": "Error: Unable to pull updates",
        "restoring": "Restoring stashed changes...",
        "conflict_warning": "Warning: Conflicts occurred while restoring stashed changes",
        "manual_resolve": "Please resolve conflicts manually",
        "stash_list": "Use 'git stash list' to view stashed changes",
        "stash_pop": "Use 'git stash pop' to restore changes",
        "upgrade_complete": "Upgrade complete!",
        "check_config": "1. Please check if conf.yaml needs updating",
        "resolve_conflicts": "2. Resolve any config file conflicts manually",
        "check_backup": "3. Check backup config to ensure no important settings are lost",
        "git_not_found": "Error: Git not found. Please install Git first:\nWindows: https://git-scm.com/download/win\nmacOS: brew install git\nLinux: sudo apt install git",
        "operation_preview": """
This script will perform the following operations:
1. Backup current conf.yaml configuration file
2. Stash all uncommitted changes (git stash)
3. Pull latest code from remote repository (git pull)
4. Attempt to restore previously stashed changes (git stash pop)

Continue? (y/N): """,
        "abort_upgrade": "Upgrade aborted",
        "merged_config_success": "Merged new configuration items:",
        "merged_config_none": "No new configuration items found.",
        "merge_failed": "Configuration merge failed: {error}",
        "updating_submodules": "Updating submodules...",
        "submodules_updated": "Submodules updated successfully",
        "submodule_error": "Error updating submodules",
        "no_submodules": "No submodules detected, skipping update",
        "env_info": "Environment: {os_name} {os_version}, Python {python_version}",
        "git_version": "Git version: {git_version}",
        "current_branch": "Current branch: {branch}",
        "operation_time": "Operation '{operation}' completed in {time:.2f} seconds",
        "checking_stash": "Checking for uncommitted changes...",
        "detected_changes": "Detected changes in {count} files",
        "submodule_updating": "Updating submodule: {submodule}",
        "submodule_updated": "Submodule updated: {submodule}",
        "checking_remote": "Checking remote repository status...",
        "remote_ahead": "Local version is up to date",
        "remote_behind": "Found {count} new commits to pull",
        "config_backup_path": "Config backup path: {path}",
        "start_upgrade": "Starting upgrade process...",
        "version_upgrade_success": "Config version upgraded: {old} → {new}",
        "version_upgrade_none": "No upgrade needed. Current version is {version}",
        "version_upgrade_failed": "Failed to upgrade config version: {error}",
        "finish_upgrade": "Upgrade process completed, total time: {time:.2f} seconds",
    },
}

# Multilingual texts for merge_configs log messages
TEXTS_MERGE = {
    "zh": {
        "new_config_item": "[信息] 新增配置项: {key}",
    },
    "en": {
        "new_config_item": "[INFO] New config item: {key}",
    },
}

# Multilingual texts for compare_configs log messages
TEXTS_COMPARE = {
    "zh": {
        "missing_keys": "[警告] 用户配置缺少以下键，可能与默认配置不一致: {keys}",
        "extra_keys": "[警告] 用户配置包含以下默认配置中不存在的键: {keys}",
        "up_to_date": "[调试] 用户配置与默认配置一致。",
    },
    "en": {
        "missing_keys": "[WARNING] User config is missing the following keys, which may be out-of-date: {keys}",
        "extra_keys": "[WARNING] User config contains the following keys not present in default config: {keys}",
        "up_to_date": "[DEBUG] User config is up-to-date with default config.",
    },
}