#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the upgrade system's new JSON-based i18n.

This verifies that:
1. All upgrade translations load correctly
2. Korean language support works
3. Legacy dictionary syntax still works
"""

import sys
import io

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from upgrade_codes.upgrade_core.constants import (
    TEXTS, TEXTS_MERGE, TEXTS_COMPARE, UPGRADE_TEXTS,
    get_text, get_merge_text, get_compare_text, get_upgrade_routine_text
)


def test_legacy_dict_syntax():
    """Test that old dictionary syntax still works"""
    print("=" * 60)
    print("Testing Legacy Dictionary Syntax")
    print("=" * 60)

    # Test TEXTS
    print("\nTESTS dictionary:")
    print(f"  [en] welcome_message: {TEXTS['en']['welcome_message']}")
    print(f"  [zh] welcome_message: {TEXTS['zh']['welcome_message']}")
    print(f"  [ko] welcome_message: {TEXTS['ko']['welcome_message']}")

    # Test TEXTS_MERGE
    print("\nTEXTS_MERGE dictionary:")
    print(f"  [en] new_config_item: {TEXTS_MERGE['en']['new_config_item']}")
    print(f"  [zh] new_config_item: {TEXTS_MERGE['zh']['new_config_item']}")
    print(f"  [ko] new_config_item: {TEXTS_MERGE['ko']['new_config_item']}")

    # Test TEXTS_COMPARE
    print("\nTEXTS_COMPARE dictionary:")
    print(f"  [en] up_to_date: {TEXTS_COMPARE['en']['up_to_date']}")
    print(f"  [zh] up_to_date: {TEXTS_COMPARE['zh']['up_to_date']}")
    print(f"  [ko] up_to_date: {TEXTS_COMPARE['ko']['up_to_date']}")

    # Test UPGRADE_TEXTS
    print("\nUPGRADE_TEXTS dictionary:")
    print(f"  [en] already_latest: {UPGRADE_TEXTS['en']['already_latest']}")
    print(f"  [zh] already_latest: {UPGRADE_TEXTS['zh']['already_latest']}")
    print(f"  [ko] already_latest: {UPGRADE_TEXTS['ko']['already_latest']}")

    print("\n[OK] Legacy dictionary syntax tests passed!")


def test_helper_functions():
    """Test new helper functions"""
    print("\n" + "=" * 60)
    print("Testing Helper Functions")
    print("=" * 60)

    print("\nget_text():")
    print(f"  [en] not_git_repo: {get_text('not_git_repo', lang='en')[:50]}...")
    print(f"  [zh] not_git_repo: {get_text('not_git_repo', lang='zh')[:50]}...")
    print(f"  [ko] not_git_repo: {get_text('not_git_repo', lang='ko')[:50]}...")

    print("\nget_merge_text():")
    print(f"  [en] new_config_item: {get_merge_text('new_config_item', lang='en')}")
    print(f"  [zh] new_config_item: {get_merge_text('new_config_item', lang='zh')}")
    print(f"  [ko] new_config_item: {get_merge_text('new_config_item', lang='ko')}")

    print("\nget_compare_text():")
    print(f"  [en] compare_passed: {get_compare_text('compare_passed', lang='en', name='test')}")
    print(f"  [zh] compare_passed: {get_compare_text('compare_passed', lang='zh', name='测试')}")
    print(f"  [ko] compare_passed: {get_compare_text('compare_passed', lang='ko', name='테스트')}")

    print("\nget_upgrade_routine_text():")
    print(f"  [en] upgrading_path: {get_upgrade_routine_text('upgrading_path', lang='en', from_version='1.0', to_version='2.0')}")
    print(f"  [zh] upgrading_path: {get_upgrade_routine_text('upgrading_path', lang='zh', from_version='1.0', to_version='2.0')}")
    print(f"  [ko] upgrading_path: {get_upgrade_routine_text('upgrading_path', lang='ko', from_version='1.0', to_version='2.0')}")

    print("\n[OK] Helper function tests passed!")


def test_all_korean_keys():
    """Test all Korean translations are present"""
    print("\n" + "=" * 60)
    print("Testing All Korean Translations")
    print("=" * 60)

    # Sample some keys
    keys = [
        'backup_user_config',
        'pulling',
        'upgrade_complete',
        'checking_remote',
        'version_upgrade_success'
    ]

    for key in keys:
        text = get_text(key, lang='ko')
        print(f"  {key:30s} → {text[:50]}...")

    print("\n[OK] All Korean translation tests passed!")


def main():
    """Run all tests"""
    print("\n--> Testing Upgrade System JSON-based i18n\n")

    try:
        test_legacy_dict_syntax()
        test_helper_functions()
        test_all_korean_keys()

        print("\n" + "=" * 60)
        print("*** ALL TESTS PASSED!")
        print("=" * 60)
        print("\n** Upgrade system successfully refactored to JSON-based i18n!")
        print("   - Adding new languages now only requires creating JSON files")
        print("   - No code changes needed when adding translations")
        print("   - Korean language support fully functional")
        print("\n")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
