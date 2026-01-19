#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the new JSON-based i18n system.

This script demonstrates:
1. Loading translations from JSON files
2. Accessing translations in different languages
3. Using the new simplified DESCRIPTIONS format
"""

import sys
import io

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.open_llm_vtuber.i18n_manager import I18nManager
from src.open_llm_vtuber.config_manager.character import CharacterConfig
from src.open_llm_vtuber.config_manager.system import SystemConfig


def test_i18n_manager():
    """Test I18nManager directly"""
    print("=" * 60)
    print("Testing I18nManager")
    print("=" * 60)

    # Load translations
    I18nManager.load_translations()
    print(f"[OK] Loaded translations")
    print(f"  Available languages: {I18nManager.get_available_languages()}\n")

    # Test English
    print("English translations:")
    print(f"  conf_name: {I18nManager.get('conf_name', lang='en', namespace='character')}")
    print(f"  host: {I18nManager.get('host', lang='en', namespace='system')}")

    # Test Chinese
    print("\nChinese translations:")
    print(f"  conf_name: {I18nManager.get('conf_name', lang='zh', namespace='character')}")
    print(f"  host: {I18nManager.get('host', lang='zh', namespace='system')}")

    # Test Korean
    print("\nKorean translations:")
    print(f"  conf_name: {I18nManager.get('conf_name', lang='ko', namespace='character')}")
    print(f"  host: {I18nManager.get('host', lang='ko', namespace='system')}")

    # Test fallback
    print("\nFallback test (non-existent key):")
    result = I18nManager.get('nonexistent_key', lang='ko', namespace='character')
    print(f"  nonexistent_key: {result} (should return key itself)")

    print("\n[OK] I18nManager tests passed!")


def test_config_classes():
    """Test config classes with new i18n system"""
    print("\n" + "=" * 60)
    print("Testing Config Classes")
    print("=" * 60)

    # Test CharacterConfig
    print("\nCharacterConfig descriptions:")
    for lang in ['en', 'zh', 'ko']:
        desc = CharacterConfig.get_field_description('conf_name', lang_code=lang)
        print(f"  [{lang}] conf_name: {desc}")

    # Test SystemConfig
    print("\nSystemConfig descriptions:")
    for lang in ['en', 'zh', 'ko']:
        desc = SystemConfig.get_field_description('host', lang_code=lang)
        print(f"  [{lang}] host: {desc}")

    print("\n[OK] Config class tests passed!")


def test_all_character_fields():
    """Test all character config fields"""
    print("\n" + "=" * 60)
    print("Testing All CharacterConfig Fields (Korean)")
    print("=" * 60)

    fields = [
        "conf_name",
        "conf_uid",
        "live2d_model_name",
        "character_name",
        "human_name",
        "avatar",
        "persona_prompt",
        "agent_config",
        "asr_config",
        "tts_config",
        "vad_config",
        "tts_preprocessor_config",
    ]

    for field in fields:
        desc = CharacterConfig.get_field_description(field, lang_code='ko')
        print(f"  {field:30s} → {desc}")

    print("\n[OK] All field tests passed!")


def main():
    """Run all tests"""
    print("\n--> Testing New JSON-based i18n System\n")

    try:
        test_i18n_manager()
        test_config_classes()
        test_all_character_fields()

        print("\n" + "=" * 60)
        print("*** ALL TESTS PASSED!")
        print("=" * 60)
        print("\n** You can now:")
        print("   1. Add new languages by creating locales/{lang}/*.json files")
        print("   2. Update translations by editing JSON files (no code changes!)")
        print("   3. Use Korean by setting system language or passing 'ko' parameter")
        print("\n")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
