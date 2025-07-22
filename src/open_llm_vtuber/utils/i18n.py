"""
This module provides internationalization(i18n) support for the Open-LLM-VTuber project.
It includes a Translator class that loads translations based on the specified language.

Usage:
```python
# 'translator' is the singleton of the Translator class.
from src.open_llm_vtuber.utils.i18n import translator

# At the start of your application, you can set the language:
# You can find the translation files in the 'i18n' directory.
# Also the filename represents the language code, e.g., 'en' of 'en.json' for English.
translator.set_language("en")

# To get a translated string, use the 'translate' method:
translated_string = translator.get("info-project-some_thing_else")

# Or the simplified version:
translated_string = translator("info-project-some_thing_else")

# If the translated string required some formatting, you can just pass the arguments:
translated_string = translator.get("info-project-some_thing_else", "arg1", "arg2")
# Also keywords arguments are supported:
translated_string = translator.get("info-project-some_thing_else", arg1="value1", arg2="value2")

# Simplified version with formatting:
translated_string = translator("info-project-some_thing_else", "arg1", arg2="value2")
```

For a translation file, you can create a `JSON file(.json)` in the `i18n` directory with the following structure:
```
{
    "info-project-some_thing_else": "Some message.",
    "error-llm-some_error": "An error occurred while LLM processing.",
    "...": "..."
}
```
Or you can extend the existed translation file with more keys as needed.
Be aware that the filename **should be** the language code, and extension **must be** `.json`.

We recommend use the "level-part-conclusion_of_msg" format for the keys, where:
- `level`: The severity level (e.g., info, error, warning).
- `part`: The part of the application (e.g., asr, llm(specified like 'ollama_llm'), tts, etc.).
- `conclusion_of_msg`: A brief description of the message.
This should be consistent across the project, which helps in organizing and identifying messages easily.

Example:
In the code, you might have:
```python
logger.info(translator("info-project-some_thing_else"))
```
In the translation file, you should have:
```
{
    "...": "...",
    "info-project-some_thing_else": "Some message."
}
```
If translation is not found, it will return the key itself, like:
```python
logger.error(translator("something-not_found"))
```
You will see the output as(just an example):
> 2025-6-11 12:00:00,000 - ERROR - something-not_found

TODO:
- Don't need to set a key for every message
    - This will require a eazier way to manage translations
    - possibly with a GUI or a web interface.
"""

from pathlib import Path

ROOT_PATH = Path(__file__).parents[3]
I18N_DIR = ROOT_PATH / "i18n"


class Translator:
    """
    A class to handle translations for the Open-LLM-VTuber project.
    Use the singleton instance `translator` to access translation methods.
    """

    def __init__(self):
        """
        This would not take any parameters.
        Remember to set the language before using the translator.
        """
        self.language: str = None
        self.translations: dict[str, str] = None
        self.current_file: Path = None
        self.available_languages: list[str] = self.__search_available_languages()

    def __search_available_languages(self) -> list[str]:
        """
        Search for available language files in the i18n directory.
        Returns a list of language codes found in the i18n directory.
        """
        return [f.stem for f in I18N_DIR.glob("*.json")]

    def load_translation(self) -> None:
        """
        Load the translation file for the current language.
        It could also be used to reload translations if needed.

        Raises:
            ValueError: If the language is not set.
            FileNotFoundError: If the translation file for the current language does not exist.
        """
        if self.language is None:
            raise ValueError(
                "Language is not set. Please set the language before loading translations."
            )
        self.current_file = I18N_DIR / f"{self.language}.json"
        if not self.current_file.exists():
            raise FileNotFoundError(
                f"Translation file for language '{self.language}' not found at {self.current_file}"
            )
        with open(self.current_file, "r", encoding="utf-8") as file:
            import json

            self.translations = json.load(file)

    def set_language(self, language: str) -> None:
        """
        Set the language for translations.
        It will also load the translation file for the specified language.

        Args:
            language (str): The language code to set (e.g., 'en', 'zh', etc.).

        Raises:
            ValueError: If the specified language is not available.
            FileNotFoundError: If the translation file for the specified language does not exist.
        """
        self.language = language
        if self.language not in self.available_languages:
            raise ValueError(
                f"Language '{self.language}' is not available. Available languages: {self.available_languages}"
            )
        self.load_translation()

    def get(self, key: str, *args, **kwargs) -> str:
        """
        Get the translated string for the given key.
        Also supports formatting with args and kwargs.
        If the key is not found, it returns the key itself.

        Args:
            key (str): The key for the translation.
            *args: Positional arguments for formatting the translation.
            **kwargs: Keyword arguments for formatting the translation.

        Returns:
            str: The translated string, formatted with args and kwargs if provided.
                if the key is not found, it returns the key itself.
        """
        if not args and not kwargs:
            return self.translations.get(key, key)
        cache = self.translations.get(key, key)
        if cache == key:
            return key
        return cache.format(*args, **kwargs)

    def __call__(self, key: str, *args, **kwargs) -> str:
        return self.get(key, *args, **kwargs)


translator = Translator()

if __name__ == "__main__":
    print(I18N_DIR)
