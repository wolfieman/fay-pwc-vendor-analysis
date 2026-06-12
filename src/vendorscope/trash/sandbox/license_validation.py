"""Validate vendor general-contractor licenses against NCLBGC (live oracle).

A vendor's eVP ``GeneralContractorLicenseNumber`` is dirty: blank, sentinels
like ``0000``, ``L.``-prefixed, out-of-state (``WV…``), or multi-value. This
module decides whether a vendor holds a *verifiable* NCLBGC general-contractor
license. It (1) cleans and classifies the number into a search route, (2) looks
it up at the board by number, falling back to exact then phonetic company-name
search, and (3) confirms the board's owner matches the vendor. The board is used
**only as a validation oracle** — no license detail is ingested.

Experimental (see ``vendorscope.sandbox``): the approach is still being vetted
against real data and may move into the package proper once locked.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from dataclasses import dataclass

# US state codes EXCEPT NC. An NC license carries no state prefix, so any of
# these as a prefix flags an out-of-state number that must not be number-searched.
OTHER_STATES = frozenset(
    {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
        "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
        "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "ND", "OH", "OK", "OR",
        "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI",
        "WY", "DC",
    }
)

# Legal-form tokens dropped before comparing company names.
NAME_SUFFIXES = frozenset(
    {
        "llc", "inc", "co", "corp", "ltd", "pa", "pllc", "lp", "llp", "dba",
        "the", "incorporated", "company", "corporation",
    }
)


@dataclass(frozen=True)
class Validation:
    """Outcome of validating one vendor's GC license against the board."""

    verdict: str  # 'valid' | 'invalid'
    via: str  # 'number' | 'name' | 'name_soundex' | 'none'
    category: str  # Stage-A class (blank/numeric/out_of_state/...)
    gc_clean: str  # the cleaned license number (digits) when applicable
    board_account: str  # the matched NCLBGC account number, when found
    board_owner: str  # the owner the board returned (matching or not)


def clean_gc_number(raw: str) -> tuple[str, str, str]:
    """Return ``(cleaned, category, route)`` for a raw GC license number.

    ``route`` is ``'number'`` when the value is a usable NC license number and
    ``'name'`` otherwise (blank, sentinel, out-of-state, or messy). Nothing is
    discarded — the route only decides how the board is searched.
    """
    s = (raw or "").strip()
    if s == "":
        return "", "blank", "name"
    # Strip an NC "L"/"L." prefix only when it precedes digits (L.106057, L83991).
    su = re.sub(r"^[Ll]\.?(?=\d)", "", s)
    if re.fullmatch(r"0+", su):
        return su, "zero_sentinel", "name"
    if re.fullmatch(r"\d+", su):
        return su, "numeric", "number"
    m = re.match(r"^([A-Za-z]{2})[\s.\-]*\d", s)
    if m and m.group(1).upper() in OTHER_STATES:
        return s, "out_of_state", "name"
    return s, "other_nonnumeric", "name"


def _name_tokens(name: str) -> tuple[str, set[str]]:
    """Return ``(squashed, token_set)`` for a company name.

    ``&`` becomes ``and``, punctuation is dropped, and legal-form suffixes are
    removed — so ``'B&N Grading, Inc.'`` and ``'B & N Grading, Inc.'`` both
    reduce to the same squashed string ``'bandngrading'`` and token set.
    """
    s = name.lower().replace("&", " and ")
    toks = [t for t in re.split(r"[^a-z0-9]+", s) if t and t not in NAME_SUFFIXES]
    return "".join(toks), set(toks)


def normalize_company(name: str) -> str:
    """Squashed, suffix-stripped form of a company name (for display/keys)."""
    return _name_tokens(name)[0]


def owner_match(a: str, b: str) -> bool:
    """Whether two company names refer to the same business.

    Tolerant of ``&``-spacing, punctuation, legal-suffix differences, and the
    board's ``AKA: …`` trailers: equal squashed forms, a substring relationship,
    or strong token overlap all count as a match.
    """
    sa, ta = _name_tokens(a)
    sb, tb = _name_tokens(b)
    if not sa or not sb:
        return False
    if sa == sb or sa in sb or sb in sa:
        return True
    return bool(ta & tb) and len(ta & tb) / min(len(ta), len(tb)) >= 0.7


def validate_vendor(client, vendor_name: str, raw_gc: str) -> Validation:
    """Validate one vendor's GC license against NCLBGC.

    Tries, in order: the cleaned license number, an exact company-name search,
    then the board's phonetic ("like sounding") search. The first owner-matched
    hit wins. If none match, the verdict is ``invalid``, carrying the board's
    nearest non-matching result (if any) for the audit. ``client`` is an
    :class:`~vendorscope.nclbgc_client.NCLBGCClient`.
    """
    cleaned, category, route = clean_gc_number(raw_gc)
    top: dict[str, str] | None = None

    if route == "number":
        for r in client.search(license_number=cleaned):
            top = top or r
            if owner_match(vendor_name, r["company_name"]):
                return Validation("valid", "number", category, cleaned,
                                  r["license_number"], r["company_name"])

    for fuzzy, via in ((False, "name"), (True, "name_soundex")):
        for r in client.search(company=vendor_name, like_sounding=fuzzy):
            top = top or r
            if owner_match(vendor_name, r["company_name"]):
                return Validation("valid", via, category, cleaned,
                                  r["license_number"], r["company_name"])

    return Validation(
        "invalid", "none", category, cleaned,
        top["license_number"] if top else "",
        top["company_name"] if top else "",
    )
