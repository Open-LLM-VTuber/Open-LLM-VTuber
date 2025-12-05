# config_manager/i18n.py
from typing import Dict, ClassVar
from pydantic import BaseModel, Field, ConfigDict


class MultiLingualString(BaseModel):
    """
    Represents a string with translations in multiple languages.
    """

    en: str = Field(..., description="English translation")
    zh: str = Field(..., description="Chinese translation")

    def get(self, lang_code: str) -> str:
        """
        Retrieves the translation for the specified language code.

        Args:
            lang_code: The language code (e.g., "en", "zh").

        Returns:
            The translation for the specified language code, or the English translation if the specified language is not found.
        """
        return getattr(self, lang_code, self.en)


class Description(MultiLingualString):
    """
    Represents a description with translations in multiple languages.
    """

    notes: MultiLingualString | None = Field(
        default=None, description="Additional notes"
    )

    def get_text(self, lang_code: str) -> str:
        """
        Retrieves the main description text in the specified language.

        Args:
            lang_code: The language code (e.g., "en", "zh").

        Returns:
            The main description text in the specified language.
        """
        return self.get(lang_code)

    def get_notes(self, lang_code: str) -> str | None:
        """
        Retrieves the additional notes in the specified language.

        Args:
            lang_code: The language code (e.g., "en", "zh").

        Returns:
            The additional notes in the specified language, or None if no notes are available.
        """
        return self.notes.get(lang_code) if self.notes else None

    @classmethod
    def from_str(cls, text: str, notes: str | None = None) -> "Description":
        """
        Creates a Description instance from plain strings, assuming English as the default language.

        Args:
            text: The main description text.
            notes: Additional notes (optional).

        Returns:
            A Description instance with the provided text and notes in English.
        """
        return cls(
            en=text,
            zh=text,
            notes=MultiLingualString(en=notes, zh=notes) if notes else None,
        )


class I18nMixin(BaseModel):
    """
    A mixin class for Pydantic models that provides multilingual descriptions for fields.
    """

    model_config = ConfigDict(populate_by_name=True)

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {}

    @classmethod
    def get_field_description(
        cls, field_name: str, lang_code: str = "en"
    ) -> str | None:
        """
        Retrieves the description of a field in the specified language.

        Args:
            field_name: The name of the field.
            lang_code: The language code (e.g., "en", "zh").

        Returns:
            The description of the field in the specified language, or None if no description is available.
        """
        description = cls.DESCRIPTIONS.get(field_name)
        if description:
            return description.get_text(lang_code)
        return None

    @classmethod
    def get_field_notes(cls, field_name: str, lang_code: str = "en") -> str | None:
        """
        Retrieves the additional notes for a field in the specified language.

        Args:
            field_name: The name of the field.
            lang_code: The language code (e.g., "en", "zh").

        Returns:
            The additional notes for the field in the specified language, or None if no notes are available.
        """
        description = cls.DESCRIPTIONS.get(field_name)
        if description:
            return description.get_notes(lang_code)
        return None

    @classmethod
    def get_field_options(cls, field_name: str) -> list | Dict | None:
        """
        Retrieves the options for a field, if any are defined.

        Args:
            field_name: The name of the field.

        Returns:
            The options for the field, which can be a list or a dictionary, or None if no options are defined.
        """
        field = cls.model_fields.get(field_name)
        if field:
            if hasattr(field, "options"):
                return field.options
        return None
