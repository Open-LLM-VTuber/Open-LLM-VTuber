#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the languages API endpoint

This script tests that the I18nManager.get_available_languages() method
works correctly and returns all available languages.
"""

import sys
import io

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.open_llm_vtuber.i18n_manager import I18nManager


def test_languages_api():
    """Test that the languages API returns expected results"""
    print("=" * 60)
    print("Testing Languages API")
    print("=" * 60)

    # Get available languages
    languages = I18nManager.get_available_languages()

    print(f"\nAvailable languages: {languages}")
    print(f"Number of languages: {len(languages)}")

    # Check expected languages
    expected_languages = ["en", "ko", "zh"]
    for lang in expected_languages:
        if lang in languages:
            print(f"  ✓ {lang} found")
        else:
            print(f"  ✗ {lang} NOT found")

    # Verify all expected languages are present
    all_present = all(lang in languages for lang in expected_languages)

    print("\n" + "=" * 60)
    if all_present:
        print("✅ All expected languages are available!")
        print("\nAPI response format:")
        print({
            "type": "api/languages",
            "count": len(languages),
            "languages": languages
        })
    else:
        print("❌ Some expected languages are missing!")
        return 1

    return 0


if __name__ == "__main__":
    exit(test_languages_api())
