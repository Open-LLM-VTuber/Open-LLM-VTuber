# config_manager/i18n.py
"""
i18n support for configuration management.

This module has been refactored to use JSON-based translations
instead of hardcoded language fields. This provides:
- Easy addition of new languages (just add JSON files)
- Separation of translation data from code
- Consistency with frontend i18n approach
"""

from typing import Dict, ClassVar, Optional
from pydantic import BaseModel, Field, ConfigDict

# Import the centralized I18nManager
from ..i18n_manager import I18nManager


class MultiLingualString(BaseModel):
    """
    Represents a string with translations in multiple languages.

    REFACTORED: Now uses translation keys instead of hardcoded language fields.
    """

    key: str = Field(..., description="Translation key")
    namespace: str = Field(default="config", description="Translation namespace")

    def get(self, lang_code: str) -> str:
        """
        Retrieves the translation for the specified language code.

        Args:
            lang_code: The language code (e.g., "en", "zh", "ko").

        Returns:
            The translation for the specified language code,
            or English fallback if not found.
        """
        return I18nManager.get(self.key, lang=lang_code, namespace=self.namespace)

    @classmethod
    def create(cls, key: str, namespace: str = "config") -> "MultiLingualString":
        """
        Factory method to create a MultiLingualString from a translation key.

        Args:
            key: Translation key (e.g., "conf_name")
            namespace: Translation namespace (e.g., "character", "system")

        Returns:
            A MultiLingualString instance
        """
        return cls(key=key, namespace=namespace)


class Description(MultiLingualString):
    """
    Represents a description with translations in multiple languages.

    REFACTORED: Simplified to just reference a translation key.

    BACKWARD COMPATIBILITY: Also supports old-style en/zh parameters.
    """

    notes_key: Optional[str] = Field(
        default=None, description="Translation key for additional notes"
    )

    # Old-style fields for backward compatibility
    en: Optional[str] = Field(default=None, description="English translation (legacy)")
    zh: Optional[str] = Field(default=None, description="Chinese translation (legacy)")

    def __init__(self, **data):
        """
        Initialize Description with backward compatibility.

        Supports both:
        - New style: Description(key="conf_name", namespace="character")
        - Old style: Description(en="Name...", zh="名称...")
        """
        # If old-style (en/zh) is provided, convert to new style
        if 'en' in data and 'key' not in data:
            # Create a hash-based key for legacy descriptions
            key = f"legacy_{abs(hash(data.get('en', '')))}"
            super().__init__(key=key, namespace="legacy", **data)
        else:
            super().__init__(**data)

    def get_text(self, lang_code: str) -> str:
        """
        Retrieves the main description text in the specified language.

        Args:
            lang_code: The language code (e.g., "en", "zh", "ko").

        Returns:
            The main description text in the specified language.
        """
        # If using old-style (en/zh fields), return those
        if self.en is not None:
            if lang_code == "zh" and self.zh is not None:
                return self.zh
            return self.en

        # Otherwise use new JSON-based system
        return self.get(lang_code)

    def get_notes(self, lang_code: str) -> str | None:
        """
        Retrieves the additional notes in the specified language.

        Args:
            lang_code: The language code (e.g., "en", "zh", "ko").

        Returns:
            The additional notes in the specified language,
            or None if no notes are available.
        """
        if self.notes_key:
            return I18nManager.get(
                self.notes_key, lang=lang_code, namespace=self.namespace
            )
        return None

    @classmethod
    def from_str(cls, text: str, notes: str | None = None) -> "Description":
        """
        Creates a Description instance from plain strings.

        DEPRECATED: For backward compatibility only.
        Prefer using Description.create() with translation keys.

        Args:
            text: The main description text.
            notes: Additional notes (optional).

        Returns:
            A Description instance (will just return the text as-is)
        """
        # For backward compatibility: create a temporary key
        return cls(key=f"legacy_{hash(text)}", namespace="legacy")

    @classmethod
    def create(
        cls,
        key: str,
        namespace: str = "config",
        notes_key: Optional[str] = None
    ) -> "Description":
        """
        Factory method to create a Description from translation keys.

        Args:
            key: Translation key for main description
            namespace: Translation namespace
            notes_key: Optional translation key for notes

        Returns:
            A Description instance

        Examples:
            >>> Description.create("conf_name", namespace="character")
            >>> Description.create("host", namespace="system", notes_key="host_notes")
        """
        return cls(key=key, namespace=namespace, notes_key=notes_key)


class I18nMixin(BaseModel):
    """
    A mixin class for Pydantic models that provides multilingual descriptions.

    REFACTORED: Now uses I18nManager for translations.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Class variable: maps field names to their translation keys
    # New format: {"field_name": "translation_key"}
    # Or: {"field_name": Description.create("key", "namespace")}
    DESCRIPTIONS: ClassVar[Dict[str, Description | str]] = {}

    # Namespace for this config class (e.g., "character", "system", "asr")
    I18N_NAMESPACE: ClassVar[str] = "config"

    @classmethod
    def get_field_description(
        cls, field_name: str, lang_code: str = "en"
    ) -> str | None:
        """
        Retrieves the description of a field in the specified language.

        Args:
            field_name: The name of the field.
            lang_code: The language code (e.g., "en", "zh", "ko").

        Returns:
            The description of the field in the specified language,
            or None if no description is available.
        """
        description = cls.DESCRIPTIONS.get(field_name)

        if description is None:
            return None

        # If it's a Description object
        if isinstance(description, Description):
            return description.get_text(lang_code)

        # If it's just a string key
        if isinstance(description, str):
            return I18nManager.get(
                description, lang=lang_code, namespace=cls.I18N_NAMESPACE
            )

        return None

    @classmethod
    def get_field_notes(cls, field_name: str, lang_code: str = "en") -> str | None:
        """
        Retrieves the additional notes for a field in the specified language.

        Args:
            field_name: The name of the field.
            lang_code: The language code (e.g., "en", "zh", "ko").

        Returns:
            The additional notes for the field in the specified language,
            or None if no notes are available.
        """
        description = cls.DESCRIPTIONS.get(field_name)

        if isinstance(description, Description):
            return description.get_notes(lang_code)

        return None

    @classmethod
    def get_field_options(cls, field_name: str) -> list | Dict | None:
        """
        Retrieves the options for a field, if any are defined.

        Args:
            field_name: The name of the field.

        Returns:
            The options for the field, which can be a list or a dictionary,
            or None if no options are defined.
        """
        field = cls.model_fields.get(field_name)
        if field:
            if hasattr(field, "options"):
                return field.options
        return None
