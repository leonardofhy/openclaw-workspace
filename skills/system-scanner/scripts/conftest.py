import sys
from pathlib import Path
# Ensure correct module resolution when pytest runs from workspace root
_here = str(Path(__file__).resolve().parent)
_lib = str(Path(__file__).resolve().parent.parent.parent / 'lib')
for p in [_here, _lib]:
    if p not in sys.path:
        sys.path.insert(0, p)
