"""Import smoke: every package module imports cleanly.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import importlib
import importlib.metadata
import pkgutil

import pytest

import vendorscope


@pytest.mark.unit
def test_every_module_imports() -> None:
    found = {
        module.name
        for module in pkgutil.walk_packages(vendorscope.__path__, prefix="vendorscope.")
    }
    for name in found:
        importlib.import_module(name)
    assert "vendorscope.paths" in found


@pytest.mark.unit
def test_version_matches_distribution_metadata() -> None:
    assert vendorscope.__version__ == importlib.metadata.version("vendorscope")
