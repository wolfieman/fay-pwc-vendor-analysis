"""Import-smoke tests: every module imports cleanly (no import-time errors,
no side effects). Cheap and portable; catches breakage a full run would miss.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import importlib
import sys
from pathlib import Path

import pytest

# The acquisition/cleaning scripts are run by file path, not installed; add their
# directories so they can be imported by module name for the smoke check.
_ROOT = Path(__file__).resolve().parents[1]
for _sub in ("src/cleaning", "src/acquisition"):
    _path = str(_ROOT / _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)

PACKAGE_MODULES = [
    "vendorscope",
    "vendorscope.text",
    "vendorscope.columns",
    "vendorscope.profiling",
    "vendorscope.audit",
    "vendorscope.pipeline",
    "vendorscope.cleaning",
    "vendorscope.cleaning.transforms",
    "vendorscope.cleaning.config",
    "vendorscope.cleaning.validate",
    "vendorscope.cleaning.pipeline",
    "vendorscope.cleaning.cli",
]
SCRIPT_MODULES = [
    "clean_data",
    "merge_vendors",
    "profile_data",
    "make_audit",
    "list_columns",
    "nclbgc_licenses_acquisition",
    "nclbgc_license_details_acquisition",
]


@pytest.mark.unit
@pytest.mark.parametrize("name", PACKAGE_MODULES + SCRIPT_MODULES)
def test_module_imports(name):
    assert importlib.import_module(name) is not None
