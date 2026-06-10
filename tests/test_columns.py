"""Unit tests for vendorscope.columns — license-column detection and
column-letter/header index resolution.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pandas as pd
import pytest

from vendorscope.columns import autodetect_license_column, get_col_indices


@pytest.mark.unit
def test_autodetect_prefers_exact_candidate():
    df = pd.DataFrame(columns=["x", "License_Number", "y"])
    assert autodetect_license_column(df) == "License_Number"


@pytest.mark.unit
def test_autodetect_falls_back_to_regex():
    df = pd.DataFrame(columns=["foo", "my account id"])
    assert autodetect_license_column(df) == "my account id"


@pytest.mark.unit
def test_autodetect_returns_none_when_absent():
    df = pd.DataFrame(columns=["alpha", "beta"])
    assert autodetect_license_column(df) is None


@pytest.mark.unit
def test_get_col_indices_by_letter_header_and_int():
    df = pd.DataFrame(columns=["name", "lic"])
    assert get_col_indices(df, "A", "B") == (0, 1)
    assert get_col_indices(df, "name", "lic") == (0, 1)
    assert get_col_indices(df, 0, 1) == (0, 1)


@pytest.mark.unit
def test_get_col_indices_unresolvable_raises():
    df = pd.DataFrame(columns=["name", "lic"])
    with pytest.raises(ValueError, match="resolve column"):
        get_col_indices(df, "zzz", "lic")
