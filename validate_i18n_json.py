#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON Structure Validation Script for i18n System

This script validates all JSON translation files in the locales directory.
It checks for:
- Valid JSON syntax
- File readability
- Proper UTF-8 encoding

Exit codes:
- 0: All JSON files are valid
- 1: One or more JSON files have errors

Usage:
    python validate_i18n_json.py

For CI/CD integration:
    python validate_i18n_json.py && echo "All translations valid!"
"""

import json
import sys
import io
from pathlib import Path
from typing import List, Tuple

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def validate_json_file(json_file: Path) -> Tuple[bool, str]:
    """
    Validate a single JSON file.

    Args:
        json_file: Path to the JSON file

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            json.load(f)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"JSON syntax error: {e}"
    except UnicodeDecodeError as e:
        return False, f"UTF-8 encoding error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


def find_all_json_files(locales_dir: Path) -> List[Path]:
    """
    Find all JSON files in the locales directory.

    Args:
        locales_dir: Path to locales directory

    Returns:
        List of JSON file paths
    """
    json_files = []
    if not locales_dir.exists():
        return json_files

    for lang_dir in locales_dir.iterdir():
        if not lang_dir.is_dir():
            continue

        for json_file in lang_dir.glob("*.json"):
            json_files.append(json_file)

    return sorted(json_files)


def main() -> int:
    """
    Main validation function.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Determine locales directory path
    script_dir = Path(__file__).parent
    locales_dir = script_dir / "src" / "open_llm_vtuber" / "locales"

    if not locales_dir.exists():
        print(f"ERROR: Locales directory not found: {locales_dir}")
        return 1

    print("=" * 60)
    print("Validating i18n JSON files")
    print("=" * 60)
    print(f"Locales directory: {locales_dir}\n")

    # Find all JSON files
    json_files = find_all_json_files(locales_dir)

    if not json_files:
        print("WARNING: No JSON files found in locales directory")
        return 1

    print(f"Found {len(json_files)} JSON files\n")

    # Validate each file
    errors = []
    valid_count = 0

    for json_file in json_files:
        relative_path = json_file.relative_to(locales_dir)
        is_valid, error_msg = validate_json_file(json_file)

        if is_valid:
            print(f"✓ {relative_path}")
            valid_count += 1
        else:
            print(f"✗ {relative_path}")
            print(f"  {error_msg}")
            errors.append((relative_path, error_msg))

    # Print summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    print(f"Total files: {len(json_files)}")
    print(f"Valid files: {valid_count}")
    print(f"Invalid files: {len(errors)}")

    if errors:
        print("\nErrors found:")
        for file_path, error_msg in errors:
            print(f"  - {file_path}: {error_msg}")
        print("\n❌ Validation FAILED")
        return 1
    else:
        print("\n✅ All JSON files are valid!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
