import sys
from pathlib import Path

# Add the scrapers/ directory to sys.path so that _common and the parser
# packages can be imported without installing the package.
_scrapers_root = str(Path(__file__).resolve().parents[2])
if _scrapers_root not in sys.path:
    sys.path.insert(0, _scrapers_root)
