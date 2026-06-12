"""Permanent structural guard: no PII pattern anywhere under tests/fixtures/.

The fixture family is known to carry stray emails in free-text fields outside
the declared red columns, so this sweeps every byte of every fixture, not just
the red columns (REQ-16, fixture rule 3).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")


@pytest.mark.unit
def test_no_email_or_phone_pattern_in_any_fixture() -> None:
    offenders: list[str] = []
    for path in FIXTURES.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if EMAIL.search(text):
            offenders.append(f"email pattern in {path.name}")
        if PHONE.search(text):
            offenders.append(f"phone pattern in {path.name}")
    assert offenders == []
