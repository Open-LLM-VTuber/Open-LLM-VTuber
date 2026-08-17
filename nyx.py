#!/usr/bin/env python3
"""Bootstrap entry point for the local Nyx runtime."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from open_llm_vtuber.nyx.cli import main


if __name__ == "__main__":
    main()
