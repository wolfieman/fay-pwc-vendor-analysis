"""The root-finder resolves to the repository and the data zones hang off it.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pytest

from vendorscope import paths


@pytest.mark.unit
def test_project_root_is_the_repository() -> None:
    assert (paths.PROJECT_ROOT / "pyproject.toml").is_file()


@pytest.mark.unit
def test_data_zones_are_children_of_the_root() -> None:
    assert paths.DATA_DIR.parent == paths.PROJECT_ROOT
    for zone in (paths.DATA_RAW, paths.DATA_PROCESSED, paths.DATA_SAMPLE):
        assert zone.parent == paths.DATA_DIR
