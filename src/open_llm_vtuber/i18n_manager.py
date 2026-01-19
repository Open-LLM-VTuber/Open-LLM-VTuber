"""
I18n Manager for Open-LLM-VTuber

This module provides a centralized i18n (internationalization) system
that loads translations from JSON files instead of hardcoding them in Python classes.

This follows the same pattern as the frontend (i18next) for consistency.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class I18nManager:
    """
    Manages internationalization by loading translations from JSON files.

    This replaces the old hardcoded MultiLingualString approach with a
    more scalable, maintainable solution that separates translation data
    from business logic.
    """

    # Class-level storage for all translations
    # Structure: {lang_code: {namespace: {key: value}}}
    _translations: Dict[str, Dict[str, Dict[str, str]]] = {}
    _loaded: bool = False
    _default_lang: str = "en"
    _available_languages: List[str] = []

    @classmethod
    def load_translations(cls, locales_dir: Optional[Path] = None) -> None:
        """
        Load all translation files from the locales directory.

        Args:
            locales_dir: Path to locales directory. If None, uses default location.
        """
        if cls._loaded:
            return

        if locales_dir is None:
            # Default location: src/open_llm_vtuber/locales/
            locales_dir = Path(__file__).parent / "locales"

        if not locales_dir.exists():
            raise FileNotFoundError(
                f"Locales directory not found: {locales_dir}\n"
                f"Please create translation files in this directory."
            )

        # Load each language directory
        for lang_dir in locales_dir.iterdir():
            if not lang_dir.is_dir():
                continue

            lang_code = lang_dir.name
            cls._translations[lang_code] = {}
            cls._available_languages.append(lang_code)

            # Load all JSON files in this language directory
            for json_file in lang_dir.glob("*.json"):
                namespace = json_file.stem  # filename without .json

                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        cls._translations[lang_code][namespace] = json.load(f)
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse translation file {json_file}: {e}. "
                        f"Skipping this file."
                    )
                except Exception as e:
                    logger.warning(f"Error loading translation file {json_file}: {e}")

        cls._loaded = True
        logger.info(
            f"I18n loaded: {len(cls._available_languages)} languages "
            f"({', '.join(cls._available_languages)})"
        )

    @classmethod
    def get(
        cls,
        key: str,
        lang: str = "en",
        namespace: str = "config",
        **kwargs
    ) -> str:
        """
        Get a translation for the specified key.

        Args:
            key: Translation key (e.g., "conf_name")
            lang: Language code (e.g., "en", "zh", "ko")
            namespace: Translation namespace/category (e.g., "config", "errors")
            **kwargs: Optional format variables for string interpolation

        Returns:
            Translated string, or English fallback, or key itself if not found

        Examples:
            >>> I18nManager.get("conf_name", lang="ko", namespace="character")
            "캐릭터 설정 이름"

            >>> I18nManager.get("welcome", lang="en", name="John")
            "Welcome, John!"
        """
        if not cls._loaded:
            cls.load_translations()

        # Try requested language
        translation = (
            cls._translations
            .get(lang, {})
            .get(namespace, {})
            .get(key)
        )

        # Fallback to default language (English)
        if translation is None and lang != cls._default_lang:
            translation = (
                cls._translations
                .get(cls._default_lang, {})
                .get(namespace, {})
                .get(key)
            )

        # Last resort: return the key itself
        if translation is None:
            return key

        # Apply string interpolation if kwargs provided
        if kwargs:
            try:
                return translation.format(**kwargs)
            except KeyError:
                return translation

        return translation

    @classmethod
    def get_available_languages(cls) -> List[str]:
        """Get list of available language codes."""
        if not cls._loaded:
            cls.load_translations()
        return cls._available_languages.copy()

    @classmethod
    def set_default_language(cls, lang_code: str) -> None:
        """
        Set the default fallback language.

        Args:
            lang_code: Language code (e.g., "en", "zh", "ko")
        """
        if lang_code not in cls._available_languages:
            logger.warning(
                f"Language '{lang_code}' not available. "
                f"Available languages: {cls._available_languages}"
            )
            return
        cls._default_lang = lang_code

    @classmethod
    def reload(cls) -> None:
        """Reload all translations from disk (useful for hot-reloading)."""
        cls._loaded = False
        cls._translations = {}
        cls._available_languages = []
        cls.load_translations()

    @classmethod
    def get_namespace(cls, namespace: str, lang: str = "en") -> Dict[str, str]:
        """
        Get all translations for a specific namespace.

        Args:
            namespace: Namespace name (e.g., "character", "system")
            lang: Language code

        Returns:
            Dictionary of all translations in that namespace
        """
        if not cls._loaded:
            cls.load_translations()

        return cls._translations.get(lang, {}).get(namespace, {}).copy()
