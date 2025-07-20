import os
import sys
import ctypes
import locale
import platform
import subprocess


def get_system_language():
    """Get system language using a combination of methods."""

    os_name = platform.system()

    if os_name == "Windows":
        try:
            # Use Windows API to get the UI language
            windll = ctypes.windll.kernel32  # type: ignore
            ui_lang = windll.GetUserDefaultUILanguage()
            lang_code = locale.windows_locale.get(ui_lang)
            if lang_code:
                lang = lang_code.split("_")[0]
                if lang.startswith("zh"):
                    return "zh"
        except Exception:
            pass

    elif os_name == "Darwin":  # macOS
        try:
            # Use defaults command to get the AppleLocale
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleLocale"],
                capture_output=True,
                text=True,
            )
            lang = result.stdout.strip().split("_")[0]
            if lang.startswith("zh"):
                return "zh"
        except Exception:
            pass

    elif os_name == "Linux":
        # Check the LANG environment variable
        lang = os.environ.get("LANG")
        if lang:
            lang = lang.split("_")[0]
            if lang.startswith("zh"):
                return "zh"

    # Fallback to using locale.getpreferredencoding()
    encoding = locale.getpreferredencoding()
    if encoding.lower() in ("cp936", "gbk", "big5"):
        return "zh"

    return "en"


def select_language():
    """Select language based on command-line argument or system language"""
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["zh", "en"]:
        return sys.argv[1].lower()
    return get_system_language()
