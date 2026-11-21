import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BilibiliImportTests(unittest.TestCase):
    def test_missing_optional_dependency_reports_original_error(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import builtins
original_import = builtins.__import__
def without_blivedm(name, *args, **kwargs):
    if name == 'blivedm':
        raise ModuleNotFoundError("No module named 'brotli'", name='brotli')
    return original_import(name, *args, **kwargs)
builtins.__import__ = without_blivedm
from src.open_llm_vtuber.live.bilibili_live import BiliBiliLivePlatform
try:
    BiliBiliLivePlatform([123])
except ImportError as error:
    assert isinstance(error.__cause__, ModuleNotFoundError)
    assert error.__cause__.name == 'brotli'
else:
    raise AssertionError('Missing dependency must prevent client creation')
""",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
