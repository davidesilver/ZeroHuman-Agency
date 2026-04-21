"""Pytest configuration — adds both python/ and python/src/ to sys.path so that:
  - `from content_engine.xxx import ...`     works (some older tests)
  - `from src.content_engine.xxx import ...` works (some newer tests)
"""
import sys
from pathlib import Path

_root = Path(__file__).parent.parent          # .../python/
_src  = _root / "src"                         # .../python/src/

for p in (_src, _root):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
