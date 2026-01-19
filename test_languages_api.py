#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the languages API endpoint

This script tests that the I18nManager.get_available_languages_with_labels() method
works correctly and returns all available languages with their labels.
"""

import sys
import io
import json

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.open_llm_vtuber.i18n_manager import I18nManager


def test_languages_api():
    """Test that the languages API returns expected results"""
    print("=" * 60)
    print("Testing Languages API (with labels)")
    print("=" * 60)

    # Test 1: Get available languages (simple list)
    print("\n[Test 1] Simple language codes:")
    languages = I18nManager.get_available_languages()
    print(f"Available languages: {languages}")
    print(f"Number of languages: {len(languages)}")

    # Test 2: Get available languages with labels (new format)
    print("\n[Test 2] Languages with labels:")
    languages_with_labels = I18nManager.get_available_languages_with_labels()
    print(f"Languages with labels:")
    for lang_info in languages_with_labels:
        print(f"  • {lang_info['code']:3s} → {lang_info['label']}")

    # Test 3: Verify language label mapping
    print("\n[Test 3] Label mapping verification:")
    expected_mappings = {
        "en": "English",
        "zh": "中文",
        "ko": "한국어"
    }

    all_mappings_correct = True
    for code, expected_label in expected_mappings.items():
        actual_label = I18nManager.get_language_label(code)
        if actual_label == expected_label:
            print(f"  ✓ {code} → {actual_label}")
        else:
            print(f"  ✗ {code} → {actual_label} (expected: {expected_label})")
            all_mappings_correct = False

    # Test 4: Test unmapped language (should return uppercase)
    print("\n[Test 4] Unmapped language fallback:")
    unmapped_label = I18nManager.get_language_label("unknown")
    expected_unmapped = "UNKNOWN"
    if unmapped_label == expected_unmapped:
        print(f"  ✓ unknown → {unmapped_label} (uppercase fallback works)")
    else:
        print(f"  ✗ unknown → {unmapped_label} (expected: {expected_unmapped})")
        all_mappings_correct = False

    # Test 5: Check expected languages are present
    print("\n[Test 5] Expected languages check:")
    expected_languages = ["en", "ko", "zh"]
    all_present = True
    for lang in expected_languages:
        if lang in languages:
            print(f"  ✓ {lang} found")
        else:
            print(f"  ✗ {lang} NOT found")
            all_present = False

    # Final result
    print("\n" + "=" * 60)
    if all_present and all_mappings_correct:
        print("✅ All tests passed!")
        print("\nAPI response format (new):")
        api_response = {
            "type": "available_languages",
            "count": len(languages_with_labels),
            "languages": languages_with_labels
        }
        print(json.dumps(api_response, indent=2, ensure_ascii=False))
    else:
        print("❌ Some tests failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit(test_languages_api())
