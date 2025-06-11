from src.open_llm_vtuber.utils.i18n import translator

# Get all available languages
print(translator.available_languages)

# Set the language to 'test'
translator.set_language("test")

# Normal message
print(translator("test-a_message"))
# Formatted message
print(translator("test-formatted_message", "Alice", "Bob"))
# Non-existent key
print(translator("non_existent_key"))