import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("HF_HOME", str(Path(__file__).parent.parent / "models"))
os.environ.setdefault("MODELSCOPE_CACHE", str(Path(__file__).parent.parent / "models"))
