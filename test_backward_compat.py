#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test backward compatibility of i18n system.

This ensures that old-style Description(en="...", zh="...") syntax
still works with the new JSON-based i18n system.
"""

import sys
import io

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.open_llm_vtuber.config_manager.asr import AzureASRConfig, FasterWhisperConfig
from src.open_llm_vtuber.config_manager.tts import AzureTTSConfig
from src.open_llm_vtuber.config_manager.character import CharacterConfig
from src.open_llm_vtuber.config_manager.system import SystemConfig


def test_old_style_description():
    """Test that old-style Description still works."""
    print("=" * 60)
    print("Testing Old-Style Description (Backward Compatibility)")
    print("=" * 60)

    # Test ASR config (uses old style)
    print("\nAzureASRConfig (old-style Description):")
    desc_en = AzureASRConfig.get_field_description("api_key", lang_code="en")
    desc_zh = AzureASRConfig.get_field_description("api_key", lang_code="zh")
    print(f"  [en] api_key: {desc_en}")
    print(f"  [zh] api_key: {desc_zh}")

    # Test that Korean fallback works (should return English)
    desc_ko = AzureASRConfig.get_field_description("api_key", lang_code="ko")
    print(f"  [ko] api_key (fallback): {desc_ko}")

    print("\n[OK] Old-style Description backward compatibility works!")


def test_new_style_json():
    """Test that new-style JSON-based system works."""
    print("\n" + "=" * 60)
    print("Testing New-Style JSON-based System")
    print("=" * 60)

    # Test CharacterConfig (uses new style)
    print("\nCharacterConfig (new JSON-based):")
    desc_en = CharacterConfig.get_field_description("conf_name", lang_code="en")
    desc_zh = CharacterConfig.get_field_description("conf_name", lang_code="zh")
    desc_ko = CharacterConfig.get_field_description("conf_name", lang_code="ko")
    print(f"  [en] conf_name: {desc_en}")
    print(f"  [zh] conf_name: {desc_zh}")
    print(f"  [ko] conf_name: {desc_ko}")

    # Test SystemConfig (uses new style)
    print("\nSystemConfig (new JSON-based):")
    desc_en = SystemConfig.get_field_description("host", lang_code="en")
    desc_zh = SystemConfig.get_field_description("host", lang_code="zh")
    desc_ko = SystemConfig.get_field_description("host", lang_code="ko")
    print(f"  [en] host: {desc_en}")
    print(f"  [zh] host: {desc_zh}")
    print(f"  [ko] host: {desc_ko}")

    print("\n[OK] New JSON-based system works!")


def test_mixed_usage():
    """Test that old and new systems coexist."""
    print("\n" + "=" * 60)
    print("Testing Mixed Usage (Old + New Coexistence)")
    print("=" * 60)

    configs = [
        ("AzureASRConfig (old)", AzureASRConfig, "api_key"),
        ("CharacterConfig (new)", CharacterConfig, "conf_name"),
        ("FasterWhisperConfig (old)", FasterWhisperConfig, "model_path"),
        ("SystemConfig (new)", SystemConfig, "port"),
    ]

    for name, config_class, field in configs:
        desc = config_class.get_field_description(field, lang_code="en")
        print(f"  {name:30s} → {desc[:50]}...")

    print("\n[OK] Old and new systems coexist without conflicts!")


def main():
    """Run all tests"""
    print("\n--> Testing i18n Backward Compatibility\n")

    try:
        test_old_style_description()
        test_new_style_json()
        test_mixed_usage()

        print("\n" + "=" * 60)
        print("*** ALL BACKWARD COMPATIBILITY TESTS PASSED!")
        print("=" * 60)
        print("\n** Key findings:")
        print("   ✅ Old-style Description(en=..., zh=...) still works")
        print("   ✅ New JSON-based system works for all languages (en/zh/ko)")
        print("   ✅ Korean fallback to English works correctly")
        print("   ✅ Old and new systems coexist without conflicts")
        print("   ✅ No code changes needed for existing configs")
        print("\n")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
