# upgrade/constants.py
"""
Constants for the upgrade system.

REFACTORED: Now uses JSON-based i18n system via I18nManager.
All upgrade texts are loaded from locales/{lang}/upgrade*.json files.
"""
from ruamel.yaml import YAML
from src.open_llm_vtuber.config_manager.utils import load_text_file_with_guess_encoding
from src.open_llm_vtuber.i18n_manager import I18nManager
import os

USER_CONF = "conf.yaml"
BACKUP_CONF = "conf.yaml.backup"

ZH_DEFAULT_CONF = "config_templates/conf.ZH.default.yaml"
EN_DEFAULT_CONF = "config_templates/conf.default.yaml"

yaml = YAML()


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

# Load translations when module is imported
I18nManager.load_translations()


# Helper functions to get translations from JSON files
def _get_translated_text(
    key: str,
    namespace: str,
    lang: str = "en",
    **kwargs
) -> str:
    """
    Internal helper to get translated text from I18nManager.

    Args:
        key: Translation key
        namespace: Translation namespace
        lang: Language code (en, zh, ko)
        **kwargs: Format parameters for string interpolation

    Returns:
        Translated and formatted text

    Note:
        Formatting is delegated to I18nManager.get() - no double formatting.
    """
    return I18nManager.get(key, lang=lang, namespace=namespace, **kwargs)


def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """
    Get upgrade text translation.

    Args:
        key: Translation key
        lang: Language code (en, zh, ko)
        **kwargs: Format parameters (e.g., version=CURRENT_SCRIPT_VERSION)

    Returns:
        Translated and formatted text
    """
    return _get_translated_text(key, "upgrade", lang, **kwargs)


def get_merge_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get merge config text translation."""
    return _get_translated_text(key, "upgrade_merge", lang, **kwargs)


def get_compare_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get compare config text translation."""
    return _get_translated_text(key, "upgrade_compare", lang, **kwargs)


def get_upgrade_routine_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get upgrade routine text translation."""
    return _get_translated_text(key, "upgrade_routines", lang, **kwargs)


# Legacy dictionaries - DEPRECATED but kept for backward compatibility
# These delegate to I18nManager for translations
class TextDict(dict):
    """Dictionary that fetches translations from I18nManager on-the-fly."""

    def __init__(self, namespace: str):
        super().__init__()
        self.namespace = namespace
        # Populate with all supported languages
        for lang in ["en", "zh", "ko"]:
            self[lang] = LanguageDict(lang, namespace)

    def __missing__(self, key):
        # If language not found, default to English
        return self["en"]


class LanguageDict(dict):
    """Dictionary that fetches translations for a specific language."""

    def __init__(self, lang: str, namespace: str):
        super().__init__()
        self.lang = lang
        self.namespace = namespace

    def __getitem__(self, key: str) -> str:
        text = I18nManager.get(key, lang=self.lang, namespace=self.namespace)
        # Handle dynamic version insertion for welcome_message
        if key == "welcome_message" and "{version}" in text:
            text = text.format(version=CURRENT_SCRIPT_VERSION)
        return text

    def __missing__(self, key):
        # If key not found, return the key itself as fallback
        return key


# Create legacy dictionary objects for backward compatibility
# Existing code can still use TEXTS[lang][key] syntax
TEXTS = TextDict("upgrade")
TEXTS_MERGE = TextDict("upgrade_merge")
TEXTS_COMPARE = TextDict("upgrade_compare")
UPGRADE_TEXTS = TextDict("upgrade_routines")
