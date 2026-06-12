"""Profiling is pure and values-free for red columns (4.3, REQ-16).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pytest

from vendorscope import profiling


@pytest.mark.unit
def test_profile_counts_and_blank_missingness() -> None:
    records = [
        {"EvpStatus": "Active", "HUB": "", "MainContactEmail": "a@example.com"},
        {"EvpStatus": "Active", "HUB": "Certified", "MainContactEmail": ""},
    ]
    report = profiling.profile(
        records, vocab_columns=("EvpStatus", "HUB"), red_columns=("MainContactEmail",)
    )
    assert report["record_count"] == 2
    assert report["vocabularies"]["EvpStatus"] == {"Active": 2}
    assert report["vocabularies"]["HUB"] == {"": 1, "Certified": 1}
    assert report["blank_counts"]["HUB"] == 1


@pytest.mark.unit
def test_red_columns_are_counts_only_never_values() -> None:
    records = [
        {"MainContactEmail": "a@example.com"},
        {"MainContactEmail": ""},
    ]
    report = profiling.profile(
        records, vocab_columns=(), red_columns=("MainContactEmail",)
    )
    # red columns appear only as nonblank/blank counts; no value list anywhere
    assert report["red_columns"]["MainContactEmail"] == {"nonblank": 1, "blank": 1}
    assert "MainContactEmail" not in report["vocabularies"]
    assert "a@example.com" not in repr(report)
