"""Unit tests for vendorscope.audit.build_report — Markdown rendering of a
profile-summary frame.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pandas as pd
import pytest

from vendorscope.audit import build_report


@pytest.mark.unit
def test_build_report_structure_and_ordering():
    df = pd.DataFrame(
        {
            "file": ["f", "f", "f"],
            "column": ["x", "y", "z"],
            "pct_missing": [10.0, 90.0, 50.0],
        }
    )
    out = build_report(df, top_n=2)

    assert out.startswith("# Data Audit Summary")
    assert "Completeness by File" in out
    assert "Top 2 Columns by Missingness" in out
    # highest-missingness column (y, 90%) is listed before the next (z, 50%)
    assert out.index("y") < out.index("z")
    assert "## Observations & Next Actions" in out
