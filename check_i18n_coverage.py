#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Translation Coverage Checker for i18n System

This script checks translation coverage by comparing all languages against
the base language (English). It reports:
- Missing translation keys in each language
- Extra keys that don't exist in the base language
- Translation coverage percentage

Exit codes:
- 0: All languages have complete coverage
- 1: One or more languages have missing translations

Usage:
    python check_i18n_coverage.py

Optional arguments:
    --base-lang LANG    Base language to compare against (default: en)
    --fail-on-missing   Exit with code 1 if any missing keys found
    --verbose           Show detailed key-by-key comparison

For CI/CD integration:
    python check_i18n_coverage.py --fail-on-missing
"""

import json
import sys
import io
import argparse
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict

# Force UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_translations(locales_dir: Path) -> Dict[str, Dict[str, Set[str]]]:
    """
    Load all translations from the locales directory.

    Args:
        locales_dir: Path to locales directory

    Returns:
        Dictionary: {lang_code: {namespace: set(keys)}}
    """
    translations = defaultdict(lambda: defaultdict(set))

    if not locales_dir.exists():
        return translations

    for lang_dir in locales_dir.iterdir():
        if not lang_dir.is_dir():
            continue

        lang_code = lang_dir.name

        for json_file in lang_dir.glob("*.json"):
            namespace = json_file.stem

            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        translations[lang_code][namespace] = set(data.keys())
            except Exception as e:
                print(f"Warning: Failed to load {json_file}: {e}")

    return dict(translations)


def compare_translations(
    base_lang: str,
    translations: Dict[str, Dict[str, Set[str]]]
) -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    """
    Compare all languages against the base language.

    Args:
        base_lang: Base language code (e.g., "en")
        translations: All loaded translations

    Returns:
        Dictionary with comparison results:
        {
            lang_code: {
                namespace: {
                    "missing": [keys missing in this language],
                    "extra": [keys not in base language]
                }
            }
        }
    """
    if base_lang not in translations:
        return {}

    base_translations = translations[base_lang]
    results = {}

    for lang_code, lang_translations in translations.items():
        if lang_code == base_lang:
            continue

        results[lang_code] = {}

        # Get all namespaces from both base and target language
        all_namespaces = set(base_translations.keys()) | set(lang_translations.keys())

        for namespace in all_namespaces:
            base_keys = base_translations.get(namespace, set())
            lang_keys = lang_translations.get(namespace, set())

            missing_keys = base_keys - lang_keys
            extra_keys = lang_keys - base_keys

            if missing_keys or extra_keys:
                results[lang_code][namespace] = {
                    "missing": sorted(missing_keys),
                    "extra": sorted(extra_keys)
                }

    return results


def calculate_coverage(
    base_translations: Dict[str, Set[str]],
    lang_translations: Dict[str, Set[str]]
) -> float:
    """
    Calculate translation coverage percentage.

    Args:
        base_translations: Base language translations
        lang_translations: Target language translations

    Returns:
        Coverage percentage (0.0 to 100.0)
    """
    total_keys = sum(len(keys) for keys in base_translations.values())
    if total_keys == 0:
        return 100.0

    covered_keys = 0
    for namespace, base_keys in base_translations.items():
        lang_keys = lang_translations.get(namespace, set())
        covered_keys += len(base_keys & lang_keys)

    return (covered_keys / total_keys) * 100.0


def print_report(
    base_lang: str,
    translations: Dict[str, Dict[str, Set[str]]],
    comparison: Dict[str, Dict[str, Dict[str, List[str]]]],
    verbose: bool = False
) -> bool:
    """
    Print a detailed coverage report.

    Args:
        base_lang: Base language code
        translations: All loaded translations
        comparison: Comparison results
        verbose: Show detailed key-by-key comparison

    Returns:
        True if all languages have complete coverage, False otherwise
    """
    print("=" * 60)
    print("i18n Translation Coverage Report")
    print("=" * 60)
    print(f"Base language: {base_lang}")
    print(f"Languages: {', '.join(sorted(translations.keys()))}\n")

    # Calculate base language statistics
    base_translations = translations[base_lang]
    total_namespaces = len(base_translations)
    total_base_keys = sum(len(keys) for keys in base_translations.values())

    print(f"Base language ({base_lang}) has:")
    print(f"  - {total_namespaces} namespaces")
    print(f"  - {total_base_keys} total keys\n")

    # Check each language
    all_complete = True
    for lang_code in sorted(translations.keys()):
        if lang_code == base_lang:
            continue

        print("-" * 60)
        print(f"Language: {lang_code}")
        print("-" * 60)

        # Calculate coverage
        coverage = calculate_coverage(
            base_translations,
            translations[lang_code]
        )
        print(f"Coverage: {coverage:.1f}%")

        if lang_code not in comparison or not comparison[lang_code]:
            print("Status: ✅ Complete (all keys translated)\n")
            continue

        all_complete = False
        print("Status: ⚠️ Incomplete\n")

        # Report issues by namespace
        for namespace in sorted(comparison[lang_code].keys()):
            issues = comparison[lang_code][namespace]
            missing = issues.get("missing", [])
            extra = issues.get("extra", [])

            if missing or extra:
                print(f"Namespace: {namespace}")

                if missing:
                    print(f"  Missing keys: {len(missing)}")
                    if verbose:
                        for key in missing:
                            print(f"    - {key}")

                if extra:
                    print(f"  Extra keys: {len(extra)}")
                    if verbose:
                        for key in extra:
                            print(f"    + {key}")

                print()

    # Final summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    if all_complete:
        print("✅ All languages have complete translation coverage!")
    else:
        print("⚠️ Some languages have incomplete translations.")
        print("   Run with --verbose to see detailed key lists.")

    return all_complete


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Check i18n translation coverage"
    )
    parser.add_argument(
        "--base-lang",
        default="en",
        help="Base language to compare against (default: en)"
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit with code 1 if any missing keys found"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed key-by-key comparison"
    )

    args = parser.parse_args()

    # Determine locales directory path
    script_dir = Path(__file__).parent
    locales_dir = script_dir / "src" / "open_llm_vtuber" / "locales"

    if not locales_dir.exists():
        print(f"ERROR: Locales directory not found: {locales_dir}")
        return 1

    # Load all translations
    translations = load_translations(locales_dir)

    if not translations:
        print("ERROR: No translations found")
        return 1

    if args.base_lang not in translations:
        print(f"ERROR: Base language '{args.base_lang}' not found")
        print(f"Available languages: {', '.join(translations.keys())}")
        return 1

    # Compare translations
    comparison = compare_translations(args.base_lang, translations)

    # Print report
    all_complete = print_report(
        args.base_lang,
        translations,
        comparison,
        args.verbose
    )

    # Determine exit code
    if args.fail_on_missing and not all_complete:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
