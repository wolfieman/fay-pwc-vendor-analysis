"""Build the committed NCLBGC test fixtures from the frozen spike capture.

Checked-in tooling, run by hand, never imported by a test. It produces, under
``tests/fixtures/nclbgc/``, the fragment shapes the parser must handle:

- ``search-result.html`` — a resolving search, the opaque key swapped for a
  synthetic token, pattern-swept (the result row carries no red column).
- ``search-empty.html`` — a search that resolves to nothing (the R4 "flag it"
  path), verbatim (carries no data).
- ``detail.html`` — a real public license record with the red ``Phone`` swept;
  the business license fields are kept (they are public by the portal's design),
  including the ``L.``-prefixed license-number quirk.
- ``qualifiers.html`` / ``qualifiers-quirk.html`` — **synthetic**: the real
  table structure (``Name`` / ``Qualifier #`` / ``Status``) with synthetic names,
  so no real qualifier name (a red column the pattern sweep cannot catch) can
  appear. The quirk fixture seeds the known ``Status`` header-bleed artifact and a
  multi-qualifier license.
- ``matters-empty.html`` — the empty public-matters fragment, verbatim.

The permanent ``tests/test_fixtures_no_pii.py`` sweep (slice 1) covers this
directory automatically; this script also asserts no email/phone pattern before
writing.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nclbgc"
OUT = ROOT / "tests" / "fixtures" / "nclbgc"

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
KEY = re.compile(r"(ShowAccountDetails\(\s*')([^']+)('\s*\))")

SYNTH_KEY = "SYNTHETICKEY0001%3d%3d"

QUALIFIERS_HTML = """<fieldset>
    <legend>Qualifiers</legend>
    <table>
        <thead>
            <tr>
                <td style="color:blue;">Name</td>
                <td style="color:blue;">Qualifier #</td>
                <td style="color:blue;">Status</td>
            </tr>
        </thead>
        <tbody>
                    <tr>
                        <td>Sample Qualifier One</td>
                        <td>900001</td>
                        <td>Active</td>
                    </tr>
                    <tr>
                        <td>Sample Qualifier Two</td>
                        <td>900002</td>
                        <td>Active</td>
                    </tr>
        </tbody>
    </table>
</fieldset>
"""

# Quirk fixture: the known 'Status' header-bleed (a body row echoing the header
# label) plus a third qualifier (a multi-qualifier license).
QUALIFIERS_QUIRK_HTML = """<fieldset>
    <legend>Qualifiers</legend>
    <table>
        <thead>
            <tr>
                <td style="color:blue;">Name</td>
                <td style="color:blue;">Qualifier #</td>
                <td style="color:blue;">Status</td>
            </tr>
        </thead>
        <tbody>
                    <tr>
                        <td>Sample Qualifier Three</td>
                        <td>900003</td>
                        <td>Active</td>
                    </tr>
                    <tr>
                        <td>Name</td>
                        <td>Qualifier #</td>
                        <td>Status</td>
                    </tr>
                    <tr>
                        <td>Sample Qualifier Four</td>
                        <td>900004</td>
                        <td>Inactive</td>
                    </tr>
        </tbody>
    </table>
</fieldset>
"""


def sweep(text: str) -> str:
    text = EMAIL.sub("redacted-email", text)
    return PHONE.sub("redacted-phone", text)


def latest_run() -> Path:
    runs = sorted(p for p in RAW.glob("*-nclbgc") if p.is_dir())
    if not runs:
        raise SystemExit(f"no frozen NCLBGC raw under {RAW}")
    return runs[-1]


def assert_clean(text: str, label: str) -> None:
    if EMAIL.search(text):
        raise SystemExit(f"{label}: email pattern present")
    if PHONE.search(text):
        raise SystemExit(f"{label}: phone pattern present")


def main() -> None:
    run = latest_run()
    searches = sorted(run.glob("search-*.html"), key=lambda p: p.stat().st_size)
    empty_search = searches[0]  # the smallest = the no-result page
    resolving_search = searches[-1]  # the largest = a real result row
    detail = sorted(run.glob("detail-*.html"), key=lambda p: -p.stat().st_size)[0]
    matters = sorted(run.glob("matters-*.html"))[0]

    OUT.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    # search-result: swap the opaque key for a synthetic token, then sweep
    raw_search = resolving_search.read_text(encoding="utf-8")
    written["search-result.html"] = sweep(
        KEY.sub(rf"\g<1>{SYNTH_KEY}\g<3>", raw_search)
    )
    written["search-empty.html"] = sweep(empty_search.read_text(encoding="utf-8"))
    written["detail.html"] = sweep(detail.read_text(encoding="utf-8"))
    written["qualifiers.html"] = QUALIFIERS_HTML
    written["qualifiers-quirk.html"] = QUALIFIERS_QUIRK_HTML
    written["matters-empty.html"] = sweep(matters.read_text(encoding="utf-8"))

    for name, text in written.items():
        assert_clean(text, name)
        (OUT / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {name:24s} {len(text):>6d} bytes")

    print(f"\nfixtures -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
