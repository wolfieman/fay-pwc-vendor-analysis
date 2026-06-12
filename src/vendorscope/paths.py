"""Repository paths: the single root-finder and the data-zone constants.

Every module that needs a filesystem location imports it from here; nothing
else in the package walks parents of ``__file__`` or hardcodes a path. The
data directories are gitignored and may be absent on a fresh clone; the
acquire step creates them at runtime.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_PROCESSED = DATA_DIR / "processed"
DATA_SAMPLE = DATA_DIR / "sample"
