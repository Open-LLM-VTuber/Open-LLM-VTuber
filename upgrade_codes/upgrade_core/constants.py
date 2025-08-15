# upgrade/constants.py
# CURRENT_SCRIPT_VERSION = "0.2.0"
from ruamel.yaml import YAML
from src.open_llm_vtuber.config_manager.utils import load_text_file_with_guess_encoding
import os

USER_CONF = "conf.yaml"
BACKUP_CONF = "conf.yaml.backup"

ZH_DEFAULT_CONF = "config_templates/conf.ZH.default.yaml"
EN_DEFAULT_CONF = "config_templates/conf.default.yaml"

yaml = YAML()
# user_config = yaml.load(load_text_file_with_guess_encoding(USER_CONF))
# CURRENT_SCRIPT_VERSION = user_config.get("system_config", {}).get("conf_version")


def load_user_config():
    if not os.path.exists(USER_CONF):
        return None
    text = load_text_file_with_guess_encoding(USER_CONF)
    if text is None:
        return None
    return yaml.load(text)


def get_current_script_version():
    config = load_user_config()
    if config:
        return config.get("system_config", {}).get("conf_version", "UNKNOWN")
    return "UNKNOWN"


CURRENT_SCRIPT_VERSION = get_current_script_version()

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
        "submodule_update_error": "❌ 子模块更新失败。",
        "checking_remote": "正在检查远程仓库状态...",
        "remote_ahead": "本地版本已是最新",
        "remote_behind": "发现 {count} 个新提交可供更新",
        "config_backup_path": "配置备份路径: {path}",
        "start_upgrade": "开始升级流程...",
        "version_upgrade_success": "配置版本已成功升级: {old} → {new}",
        "version_upgrade_none": "无需升级配置，当前版本为 {version}",
        "version_upgrade_failed": "升级配置时出错: {error}",
        "finish_upgrade": "升级流程结束, 总耗时: {time:.2f} 秒",
        "backup_used_version": "✅ 从备份文件读取配置版本: {backup_version}",
        "backup_read_error": "⚠️ 读取备份文件失败，使用默认版本 {version}。错误信息: {error}",
        "version_too_old": "🔁 检测到旧版本号 {found} 低于最低支持版本，已强制使用 {adjusted}",
        "checking_ahead_status": "🔍 正在检查是否存在未推送的本地提交...",
        "local_ahead": "🚨 你在 'main' 分支上有 {count} 个尚未推送到远程的本地 commit。",
        "push_blocked": (
            "⛔ 你没有权限推送到 'main' 分支。\n"
            "这些 commit 只保存在本地，无法同步到 GitHub。\n"
            "如果继续升级，可能会导致这些提交丢失或与远程版本发生冲突。"
        ),
        "backup_suggestion": (
            "🛟 为了安全保存你的本地提交，你可以选择以下任意方式：\n"
            "🔄 1. 撤销最近的提交（推荐）：\n"
            "   • GitHub Desktop：点击右下角的 “Undo” 按钮\n"
            "   • 终端命令：git reset --soft HEAD~1\n"
            "📦 2. 导出 patch 文件（保留提交记录）：\n"
            "   → 终端执行：git format-patch origin/main --stdout > backup.patch\n"
            "🌿 3. 创建一个备份分支（保存当前状态）：\n"
            "   → 终端执行：git checkout -b my-backup-before-upgrade\n"
            "💡 提示：撤销 commit 后，你可以新建分支或导出补丁以继续操作。"
        ),
        "abort_upgrade": "🛑 为保护本地提交，升级流程已中止。",
        "no_config_fatal": (
            "❌ 未找到配置文件 conf.yaml。\n"
            "请执行以下任一操作：\n"
            "👉 将旧版配置文件复制到当前目录\n"
            "👉 或运行 run_server.py 自动生成默认模板"
        ),
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
        "submodule_update_error": "❌ Submodule update failed.",
        "checking_remote": "Checking remote repository status...",
        "remote_ahead": "Local version is up to date",
        "remote_behind": "Found {count} new commits to pull",
        "config_backup_path": "Config backup path: {path}",
        "start_upgrade": "Starting upgrade process...",
        "version_upgrade_success": "Config version upgraded: {old} → {new}",
        "version_upgrade_none": "No upgrade needed. Current version is {version}",
        "version_upgrade_failed": "Failed to upgrade config version: {error}",
        "finish_upgrade": "Upgrade process completed, total time: {time:.2f} seconds",
        "backup_used_version": "✅ Loaded config version from backup: {backup_version}",
        "backup_read_error": "⚠️ Failed to read backup file. Falling back to default version {version}. Error: {error}",
        "version_too_old": "🔁 Detected old version {found} which is lower than the minimum supported version, forced to use {adjusted}",
        "checking_ahead_status": "🔍 Checking for unpushed local commits...",
        "local_ahead": "🚨 You have {count} local commit(s) on 'main' that are NOT pushed to remote.",
        "push_blocked": (
            "⛔ You do NOT have permission to push to the 'main' branch.\n"
            "Your commits are local only and will NOT be synced to GitHub.\n"
            "Continuing the upgrade may cause those commits to be lost or conflict with remote changes."
        ),
        "backup_suggestion": (
            "🛟 To keep your work safe, you can choose one of the following options:\n"
            "🔄 1. Undo the last commit:\n"
            "   • GitHub Desktop: Click the 'Undo' button at the bottom right.\n"
            "   • Terminal: Run: git reset --soft HEAD~1\n"
            "📦 2. Export your commit(s) as a patch file:\n"
            "   → Run: git format-patch origin/main --stdout > backup.patch\n"
            "🌿 3. Create a backup branch:\n"
            "   → Run: git checkout -b my-backup-before-upgrade\n"
            "💡 Recommendation: After undoing the commit, you can switch to a new branch or export changes as needed."
        ),
        "abort_upgrade": "🛑 Upgrade aborted to protect your local commits.",
        "no_config_fatal": (
            "❌ Config file conf.yaml not found.\n"
            "Please either:\n"
            "👉 Copy your old config file to the current directory\n"
            "👉 Or run run_server.py to generate a default template"
        ),
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
        "missing_keys": "用户配置缺少以下键，可能与默认配置不一致: {keys}",
        "extra_keys": "用户配置包含以下默认配置中不存在的键: {keys}",
        "up_to_date": "用户配置与默认配置一致。",
        "compare_passed": "{name} 对比通过。",
        "compare_failed": "{name} 配置不一致。",
        "compare_diff_item": "- {item}",
        "compare_error": "{name} 对比失败: {error}",
        "comments_up_to_date": "注释一致，跳过注释同步。",
        "extra_keys_deleted_count": "已删除 {count} 个额外键:",
        "extra_keys_deleted_item": "  - {key}",
        "comment_sync_success": "注释同步成功。",
        "comment_sync_error": "注释同步失败: {error}",
    },
    "en": {
        "missing_keys": "User config is missing the following keys, which may be out-of-date: {keys}",
        "extra_keys": "User config contains the following keys not present in default config: {keys}",
        "up_to_date": "User config is up-to-date with default config.",
        "compare_passed": "{name} comparison passed.",
        "compare_failed": "{name} comparison failed: configs differ.",
        "compare_diff_item": "- {item}",
        "compare_error": "{name} comparison error: {error}",
        "comments_up_to_date": "Comments are up to date, skipping comment sync.",
        "extra_keys_deleted_count": "Deleted {count} extra keys:",
        "extra_keys_deleted_item": "  - {key}",
        "comment_sync_success": "All comments synchronized successfully.",
        "comment_sync_error": "Failed to synchronize comments: {error}",
    },
}

UPGRADE_TEXTS = {
    "zh": {
        "model_dict_not_found": "⚠️ 未找到 model_dict.json，跳过升级。",
        "model_dict_read_error": "❌ 读取 model_dict.json 失败: {error}",
        "upgrade_success": "✅ model_dict.json 已成功升级至 v1.2.1 格式 ({language} 语言)",
        "already_latest": "model_dict.json 已是最新格式。",
        "upgrade_error": "❌ 升级 model_dict.json 失败: {error}",
        "no_upgrade_routine": "没有适用于版本 {version} 的升级程序",
        "upgrading_path": "⬆️ 正在升级配置: {from_version} → {to_version}",
    },
    "en": {
        "model_dict_not_found": "⚠️ model_dict.json not found. Skipping upgrade.",
        "model_dict_read_error": "❌ Failed to read model_dict.json: {error}",
        "upgrade_success": "✅ model_dict.json upgraded to v1.2.1 format ({language} language)",
        "already_latest": "model_dict.json already in latest format.",
        "upgrade_error": "❌ Failed to upgrade model_dict.json: {error}",
        "no_upgrade_routine": "No upgrade routine for version {version}",
        "upgrading_path": "⬆️ Upgrading config: {from_version} → {to_version}",
    },
}
