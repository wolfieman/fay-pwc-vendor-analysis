"""Unit tests for vendorscope.text — the pure string/normalization helpers.
These lock current behavior (regression-first) ahead of later refactors.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import math

import pytest

from vendorscope.text import canon_vendor, normalize_license, normalize_name, snake


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HUB Status", "hub_status"),
        ("License #", "license"),
        ("Active_Status", "active_status"),
        ("Vendor__Name", "vendor_name"),
        ("  A  B  ", "a_b"),
    ],
)
def test_snake(raw, expected):
    assert snake(raw) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Acme Contracting, LLC", "Acme"),
        ("A & B Co.", "A & B"),
        ("  multi   space  ", "multi space"),
        (None, ""),
    ],
)
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (85168.0, "85168"),
        (85168, "85168"),
        ("85168.0", "85168"),
        ("L.27348", "27348"),
        (12.34, "1234"),
        (None, None),
        ("abc", None),
    ],
)
def test_normalize_license(raw, expected):
    assert normalize_license(raw) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Acme, Inc.", "ACME INC"),
        ("  a   b ", "A B"),
        (math.nan, ""),
        (None, ""),
    ],
)
def test_canon_vendor(raw, expected):
    assert canon_vendor(raw) == expected
