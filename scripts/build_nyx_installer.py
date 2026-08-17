#!/usr/bin/env python3
"""Build a single-file Windows installer for Nyx.

This script is intentionally conservative: it packages the local runtime and
keeps the configuration in the working tree. The actual production installer
should be extended with signing, version metadata, and the full dependency set.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
WORK = ROOT / ".nyx_build"
ENTRY = ROOT / "nyx.py"
DEFAULT_ICON = ROOT / "scripts" / "nyx_icon.ico"
LOG_PATH = ROOT / "build_nyx.log"


def _run_build(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    """Run the build command and persist the output to build_nyx.log.

    Stream stdout/stderr incrementally to the terminal and to the log file so
    long-running builds don't buffer large outputs in memory and users see
    progress as it happens.
    """
    # Open the log file in append mode so incremental runs accumulate output.
    with LOG_PATH.open("a", encoding="utf-8") as logf:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        captured_lines: list[str] = []
        assert process.stdout is not None
        for line in iter(process.stdout.readline, ""):
            # Write to terminal and log incrementally
            print(line, end="")
            logf.write(line)
            logf.flush()
            captured_lines.append(line)

        process.wait()
        combined_output = "".join(captured_lines)

        if process.returncode != 0:
            # Raise with captured output for callers/tests
            raise subprocess.CalledProcessError(process.returncode, command, output=combined_output)


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Nyx Windows installer builds must run on Windows; PyInstaller is not a cross-compiler.")

    parser = argparse.ArgumentParser(description="Build a single-file Windows installer for Nyx.")
    parser.add_argument("--icon", default=str(DEFAULT_ICON), help="Path to a Windows .ico icon file.")
    parser.add_argument("--console", action="store_true", help="Keep the console window open for debugging.")
    args = parser.parse_args()

    icon_path = Path(args.icon)
    if not icon_path.is_absolute():
        icon_path = (ROOT / icon_path).resolve()
    else:
        icon_path = icon_path.resolve()

    if not icon_path.is_file():
        # If a user explicitly supplied a path that is not a regular file, reject it.
        if args.icon != str(DEFAULT_ICON):
            parser.error(f"Icon file does not exist or is not a file: {icon_path}")
        # For the default missing icon, generate a default safely and use it.
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_nyx_icon.py")], check=True, cwd=str(ROOT))
        icon_path = DEFAULT_ICON.resolve()

    DIST.mkdir(exist_ok=True)
    WORK.mkdir(exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")

    hidden_imports = [
        "pycparser.lextab",
        "pycparser.yacctab",
        "tzdata",
        "scipy.special._cdflib",
    ]
    available_hidden_imports: list[str] = []
    for module_name in hidden_imports:
        try:
            spec = importlib.util.find_spec(module_name)
        except ModuleNotFoundError:
            # A missing parent package can cause find_spec on a dotted name to
            # raise ModuleNotFoundError; treat as unavailable and continue.
            spec = None
        if spec is not None:
            available_hidden_imports.extend(["--hidden-import", module_name])

    # Make the console/windowed mode explicit: default to windowed and enable
    # console mode only when requested.
    mode_args = ["--console"] if args.console else ["--windowed"]

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--noupx",
        "--onefile",
        *mode_args,
        "--name",
        "Nyx",
        "--icon",
        str(icon_path),
        *available_hidden_imports,
        "--distpath",
        str(DIST),
        "--workpath",
        str(WORK),
        "--specpath",
        str(WORK),
        str(ENTRY),
    ]

    _run_build(command, cwd=ROOT, env=env)
    print(f"Installer built in {DIST}")
    print(f"Build log written to {LOG_PATH}")


if __name__ == "__main__":
    main()
