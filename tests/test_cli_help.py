"""CLI-smoke: every script's argparse parser builds and `--help` exits 0.

Catches argparse-construction regressions (e.g. an unescaped '%' in a help
string, which Python 3.14 rejects) that import-smoke misses because the parser
is only built when the script runs, not on import.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    _ROOT / "src" / "cleaning" / "clean_data.py",
    _ROOT / "src" / "cleaning" / "merge_vendors.py",
    _ROOT / "src" / "cleaning" / "profile_data.py",
    _ROOT / "src" / "cleaning" / "make_audit.py",
    _ROOT / "src" / "cleaning" / "list_columns.py",
    _ROOT / "src" / "acquisition" / "nclbgc_licenses_acquisition.py",
    _ROOT / "src" / "acquisition" / "nclbgc_license_details_acquisition.py",
]


@pytest.mark.unit
@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.stem)
def test_script_help_builds(script):
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
