"""Unit tests for vendorscope.profiling — normalize() and the pure
profile_dataframe() core extracted from profile_data.profile_one.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pandas as pd
import pytest

from vendorscope.profiling import normalize, profile_dataframe


@pytest.mark.unit
def test_normalize_headers_booleans_and_flags():
    df = pd.DataFrame(
        {"HUB Status": ["Y", "N", "Y"], "Count": [0, 5, 3], " Name ": [" a ", " b ", " c "]}
    )
    out = normalize(df)

    # headers snake-cased
    assert {"hub_status", "count", "name"} <= set(out.columns)
    # Y/N mapped to booleans
    assert out["hub_status"].tolist() == [True, False, True]
    # numeric column gains missing/zero flags
    assert "count_is_missing" in out.columns
    assert "count_is_zero" in out.columns
    assert out["count_is_zero"].tolist() == [True, False, False]
    # strings trimmed
    assert out["name"].iloc[0] == "a"


@pytest.mark.unit
def test_normalize_does_not_mutate_input():
    df = pd.DataFrame({"A B": [1, 2]})
    _ = normalize(df)
    assert list(df.columns) == ["A B"]  # original untouched


@pytest.mark.unit
def test_profile_dataframe_summary_and_meta():
    df = pd.DataFrame({"a": [1, 2], "b": [None, None]})
    summary, info = profile_dataframe(df, name="sample.csv")

    assert info == {"file": "sample.csv", "rows": 2, "columns": 2}
    # a fully-missing column reports 100% missing
    assert summary.loc["b", "n_missing"] == 2
    assert summary.loc["b", "pct_missing"] == 100.0


@pytest.mark.unit
def test_profile_dataframe_counts_unique_ids():
    df = pd.DataFrame({"id": [1, 1, 2]})
    _, info = profile_dataframe(df, id_col="id")
    assert info["unique_ids"] == 2
