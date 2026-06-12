"""CLI drift path: nonzero exit naming the runbook, offline (REQ-04).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from pathlib import Path

import httpx
import pytest

from vendorscope import cli

FIXTURES = Path(__file__).parent / "fixtures" / "evp"


def _transport(name: str) -> httpx.MockTransport:
    body = (FIXTURES / name).read_bytes()
    return httpx.MockTransport(lambda _r: httpx.Response(200, content=body))


@pytest.mark.contract
def test_acquire_evp_clean_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = cli.run(
        ["acquire-evp", "--floor", "20"],
        transport=_transport("vendordetails-clean.html"),
        data_raw=tmp_path,
    )
    assert code == 0
    assert "24" in capsys.readouterr().out


@pytest.mark.contract
def test_acquire_evp_drift_exits_nonzero_and_names_runbook(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = cli.run(
        ["acquire-evp", "--floor", "20"],
        transport=_transport("vendordetails-drift-nonactive.html"),
        data_raw=tmp_path,
    )
    assert code != 0
    assert "runbook-evp-drift.md" in capsys.readouterr().err
