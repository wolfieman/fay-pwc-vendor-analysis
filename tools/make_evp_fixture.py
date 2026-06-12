"""Build the committed eVP test fixtures from the frozen raw snapshot.

This is checked-in tooling, run by hand, never imported by a test (no test reads
``data/``; tests read only ``tests/fixtures/``). It produces, under
``tests/fixtures/evp/``:

- ``vendordetails-clean.html`` — fixture (a), the contract of record: the real
  page's load-bearing fragments (the filter-summary block and the ``var data``
  script wrapper, verbatim) carrying a coverage-core subset of real records. The
  three red columns are replaced with non-pattern sentinels and every field is
  swept for stray email/phone patterns, so nothing under ``tests/fixtures/``
  matches a PII pattern. Record count is sized by code-path coverage (every
  observed vocabulary value and quirk appears at least once), not by a sample.
- ``vendordetails-synthetic.html`` — fixture (b), fully synthetic records for
  structural variety the live pull does not contain (a county literally named
  "NA", a leading-zero ZIP, a seeded non-blank duplicate for the conservation
  test, business-name casing edge cases).
- ``vendordetails-drift-nonactive.html`` — a record whose status is not Active.
- ``vendordetails-drift-addedclause.html`` — an extra filter clause in the summary.
- ``vendordetails-drift-singlecategoryhub.html`` — HUB collapsed to one state.
- ``template-miss.html`` — the page with the ``var data`` variable removed.

The encoding the source uses is ``"`` to ``&quot;`` (the page's own JavaScript
un-replaces only ``&quot;``); this script reproduces it and asserts the fixture
parses back to the sanitized records before writing.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "evp"
OUT_DIR = ROOT / "tests" / "fixtures" / "evp"

DATA_RE = re.compile(r'var\s+data\s*=\s*"(\[.*?\])"\s*;?', re.S)
SUMMARY_P_RE = re.compile(r'<p style="margin: 0; padding-top:60px">.*?</p>', re.S)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

RED_COLUMNS = ("MainContactName", "MainContactEmail", "MainContactPhone")
EXPECTED_CLAUSES = ("Status: Active", "WorkLicense Classifications: Public Utilities")

# Coverage-core selection: indices into the frozen decoded extract, chosen so the
# subset contains every observed vocabulary value and every quirk at least once.
# Each index is annotated with what it is here for; the script asserts coverage
# below, so a future re-pull that drops a case fails loudly rather than silently.
COVERAGE_INDICES = (
    0,  # zip len 5; GC limitation None; Electrical level blank; HUB blank;
    # NCeProcurement Active; NCSBE blank; GeneralContractor True
    1,  # GC limitation Limited; NCeProcurement Inactive; Architectural/Engineering True
    2,  # blank State; GC limitation Unlimited; Electrical Unlimited;
    # Electrical/Plumbing/Mechanical/TradesSub True
    3,  # zip len 10 (ZIP+4); HUB Certified; HUBCategory Black
    4,  # GC license "other": prefixed (L.######)
    5,  # GC license "other": out-of-state (WV######)
    6,  # HUBCategory Female; NCSBE Not Certified
    7,  # HUB Not Certified; NCeProcurement Not Applicable
    16,  # Electrical level None (literal member, new this vintage)
    17,  # blank MainContactPhone
    51,  # HUBCategory Hispanic
    53,  # NCSBE Certified
    55,  # GC limitation Intermediate
    61,  # Electrical level Limited
    107,  # GC license "other": multi-value ("#####; NC#####")
    122,  # GeneralContractor False
    130,  # HUBCategory American Indian
    147,  # HUBCategory Disabled
    166,  # GC license "other": free-text ("NY Lic: #######")
    238,  # Electrical level Intermediate
    284,  # GC limitation blank
    361,  # zip len 7 (quirk); blank State
    560,  # dedup blank-key pair member (same name, blank GC license)
    561,  # dedup blank-key pair member -> must NOT merge with 560 (REQ-11)
)

# Columns whose full observed value-set must appear in the coverage subset.
COVERAGE_VOCAB = (
    "HUB",
    "HUBCategory",
    "NCeProcurement",
    "NCSBE",
    "GeneralContractorLimitation",
    "ElectricalLicenseLevel",
)


def find_raw() -> Path:
    runs = sorted(p for p in RAW_DIR.glob("*-evp") if p.is_dir())
    if not runs:
        raise SystemExit(f"no frozen raw run under {RAW_DIR}")
    return runs[-1] / "vendordetails-page-1.html"


def decode_records(page: str) -> list[dict]:
    m = DATA_RE.search(page)
    if m is None:
        raise SystemExit("var data not found in raw page")
    return json.loads(html.unescape(m.group(1)))


def sweep_value(value: object) -> object:
    """Replace any stray email/phone pattern in a free-text value (REQ-16)."""
    if not isinstance(value, str):
        return value
    swept = EMAIL_RE.sub("redacted-email", value)
    swept = PHONE_RE.sub("redacted-phone", swept)
    return swept


def sanitize(record: dict, ordinal: int) -> dict:
    out: dict = {}
    for key, value in record.items():
        if key == "MainContactName":
            out[key] = f"Sample Contact {ordinal:03d}"
        elif key == "MainContactEmail":
            out[key] = f"contact-{ordinal:03d}-redacted"
        elif key == "MainContactPhone":
            out[key] = "" if value in ("", None) else "redacted-phone-no"
        else:
            out[key] = sweep_value(value)
    return out


def encode_payload(records: list[dict]) -> str:
    """Re-encode records the way the source does: JSON, then "\" -> &quot;."""
    return json.dumps(records, ensure_ascii=False).replace('"', "&quot;")


def summary_paragraph(count: int, clauses: tuple[str, ...]) -> str:
    body = "".join(f"{c}<br>" for c in clauses)
    return (
        '<p style="margin: 0; padding-top:60px">\n'
        f"        <strong>{count} Records</strong> for the following filter "
        f"criteria:<br>{body}\n"
        "      </p>"
    )


def build_page(
    records: list[dict],
    script_open: str,
    script_tail: str,
    *,
    count: int | None = None,
    clauses: tuple[str, ...] = EXPECTED_CLAUSES,
    include_var_data: bool = True,
) -> str:
    n = count if count is not None else len(records)
    if include_var_data:
        script = f"{script_open}{encode_payload(records)}{script_tail}"
    else:  # template-miss fixture: the var data variable is gone
        script = "<script>\n  // export handler without the embedded dataset\n</script>"
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head><meta charset="utf-8">'
        "<title>Vendor Details (fixture)</title></head>\n<body>\n"
        '<div class="row" style="margin: 0;">\n'
        '    <div class="col-md-2 d-flex align-items-start">\n      '
        f"{summary_paragraph(n, clauses)}\n    </div>\n</div>\n"
        f"{script}\n</body>\n</html>\n"
    )


def synthetic_records() -> list[dict]:
    keys = SOURCE_KEYS

    def blank_record(**over: object) -> dict:
        rec: dict[str, object] = dict.fromkeys(keys, "")
        for flag in FLAG_KEYS:
            rec[flag] = False
        rec.update(over)
        return rec

    base = dict(
        AddressLine1="100 Test Way",
        City="Raleigh",
        State="NC",
        ZipCode="27601",
        Country="USA",
        EvpStatus="Active",
        NCeProcurement="Active",
        HUB="",
        HUBCategory="",
        GeneralContractor=True,
        GeneralContractorLimitation="Unlimited",
        GeneralContractorWorkClassification="Building",
        GeneralContractorLicenseNumber="900001",
    )
    return [
        blank_record(
            **{
                **base,
                "Name": "Synthetic NA County Co",
                "County": "NA",
                "GeneralContractorLicenseNumber": "900010",
            }
        ),
        blank_record(
            **{
                **base,
                "Name": "Leading Zero Zip LLC",
                "ZipCode": "02134",
                "GeneralContractorLicenseNumber": "900011",
            }
        ),
        blank_record(
            **{
                **base,
                "Name": "ACME PLUMBING LLC",
                "GeneralContractorLicenseNumber": "900012",
            }
        ),
        blank_record(
            **{
                **base,
                "Name": "42YL CONSTRUCTION",
                "GeneralContractorLicenseNumber": "900013",
            }
        ),
        blank_record(
            **{
                **base,
                "Name": "51ST STREET BUILDERS",
                "GeneralContractorLicenseNumber": "900014",
            }
        ),
        # seeded non-blank duplicate: same Name + same GC license -> one drop
        blank_record(
            **{
                **base,
                "Name": "Seeded Dedup Co",
                "GeneralContractorLicenseNumber": "900015",
            }
        ),
        blank_record(
            **{
                **base,
                "Name": "Seeded Dedup Co",
                "GeneralContractorLicenseNumber": "900015",
                "URL": "",
                "City": "Durham",
            }
        ),
        # literal None members
        blank_record(
            **{
                **base,
                "Name": "None Limitation Co",
                "GeneralContractorLimitation": "None",
                "GeneralContractorLicenseNumber": "900016",
            }
        ),
    ]


def assert_no_pii(text: str, label: str) -> None:
    if EMAIL_RE.search(text):
        raise SystemExit(f"{label}: email pattern present after sanitization")
    if PHONE_RE.search(text):
        raise SystemExit(f"{label}: phone pattern present after sanitization")


# Filled in main() from the raw page so synthetic records match the live keyset.
SOURCE_KEYS: tuple[str, ...] = ()
FLAG_KEYS = (
    "SmallBusiness",
    "DBE",
    "NPWC",
    "GeneralContractor",
    "ElectricalContractor",
    "PlumbingFireSprinklerContractor",
    "MechanicalHeating",
    "TradesSubContractor",
    "ArchitecturalServices",
    "EngineeringServices",
)


def main() -> None:
    global SOURCE_KEYS
    raw_page = find_raw().read_text(encoding="utf-8", errors="replace")
    records = decode_records(raw_page)
    SOURCE_KEYS = tuple(records[0].keys())

    # real load-bearing fragments, verbatim (sliced at the regex group bounds).
    # Anchor the opener at the immediate ``var data`` context rather than the whole
    # <script> block, so the unrelated button-wiring (which embeds the saved-search
    # GUID, a phone-shaped string) stays out of the fixture.
    m = DATA_RE.search(raw_page)
    if m is None:
        raise SystemExit("var data not found in raw page")
    anchor = raw_page.rfind("// Convert Object to JSON", 0, m.start())
    if anchor == -1:
        anchor = raw_page.rfind("var data", 0, m.start())
    script_open = "<script>\n      " + raw_page[anchor : m.start(1)]  # ... var data= "
    tail_end = raw_page.index("</script>", m.end(1)) + len("</script>")
    script_tail = raw_page[m.end(1) : tail_end]  # ";  ... </script>

    subset = [sanitize(records[i], n) for n, i in enumerate(COVERAGE_INDICES)]

    # coverage assertion: every observed vocab value must be in the subset
    for col in COVERAGE_VOCAB:
        full = {str(r.get(col, "")) for r in records}
        got = {str(r.get(col, "")) for r in subset}
        missing = full - got
        if missing:
            raise SystemExit(f"coverage gap in {col}: missing {sorted(missing)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    clean = build_page(subset, script_open, script_tail)
    # self-check: the fixture parses back to exactly the sanitized records
    if decode_records(clean) != subset:
        raise SystemExit("round-trip mismatch: fixture does not decode to subset")
    written["vendordetails-clean.html"] = clean

    written["vendordetails-synthetic.html"] = build_page(
        synthetic_records(), script_open, script_tail
    )

    nonactive = [dict(r) for r in subset]
    nonactive[0] = {**nonactive[0], "EvpStatus": "Pending"}
    written["vendordetails-drift-nonactive.html"] = build_page(
        nonactive, script_open, script_tail
    )

    written["vendordetails-drift-addedclause.html"] = build_page(
        subset,
        script_open,
        script_tail,
        clauses=(*EXPECTED_CLAUSES, "HUB Certification Status: Certified"),
    )

    single_hub = [{**r, "HUB": "Certified"} for r in subset]
    written["vendordetails-drift-singlecategoryhub.html"] = build_page(
        single_hub, script_open, script_tail
    )

    written["template-miss.html"] = build_page(
        subset, script_open, script_tail, include_var_data=False
    )

    for name, text in written.items():
        assert_no_pii(text, name)
        (OUT_DIR / name).write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {name:42s} {len(text):>8d} bytes")

    print(f"\ncoverage subset: {len(subset)} records, all vocab covered")
    print(f"fixtures -> {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
