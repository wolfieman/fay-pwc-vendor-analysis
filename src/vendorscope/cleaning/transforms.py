"""Pure normalizers: ``(value) -> (normalized, error)``.

Each function takes one string and returns the normalized string plus an error
code or ``None``. On a contract breach the function reports the error and
returns the value unchanged: it never imputes a missing value and never
prefix-strips an identifier (report-don't-coerce, REQ-09). The engine supplies
row/column context and wraps an error into a ``Violation``.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from collections.abc import Mapping
from datetime import datetime

type Result = tuple[str, str | None]

# Strip zero-width / soft characters; fold the no-break space to a plain space.
# Keyed on code points so the source carries no ambiguous invisible glyphs.
_INVISIBLE: dict[int, int | None] = {
    0x200B: None,  # zero-width space
    0x200C: None,  # zero-width non-joiner
    0x200D: None,  # zero-width joiner
    0xFEFF: None,  # byte-order mark
    0x00AD: None,  # soft hyphen
    0x00A0: 0x20,  # no-break space -> plain space
}
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_LEGAL_SUFFIXES = frozenset(
    {"LLC", "INC", "LLP", "PLLC", "PA", "PC", "LTD", "CO", "CORP", "LP"}
)
# A NCLBGC uniform account-number type-sigil: a single capital letter + dot
# (L. license, Q. qualifier). A multi-letter prefix (WV, NC) is not a sigil.
_SIGIL = re.compile(r"^[A-Z]\.(.+)$")


def collapse_whitespace(value: str) -> Result:
    """Drop zero-width/soft characters, fold no-break space, collapse runs, strip."""
    cleaned = re.sub(r"\s+", " ", value.translate(_INVISIBLE)).strip()
    return cleaned, None


def business_name_case(value: str) -> Result:
    """Hybrid casing: title-case words, keep legal suffixes upper; digit-led tokens unchanged (REQ-10)."""  # noqa: E501
    if value == "":
        return "", None
    out: list[str] = []
    for token in value.split():
        if token[0].isdigit():  # carries no case signal (42YL, 51ST)
            out.append(token)
        elif token.upper() in _LEGAL_SUFFIXES:
            out.append(token.upper())
        else:
            out.append(token[:1].upper() + token[1:].lower())
    return " ".join(out), None


def normalize_email(value: str) -> Result:
    stripped = value.strip()
    if stripped == "":
        return "", None
    lowered = stripped.lower()
    if _EMAIL.fullmatch(lowered):
        return lowered, None
    return value, "invalid-email"


def normalize_phone(value: str) -> Result:
    if value.strip() == "":
        return "", None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}", None
    return value, "invalid-phone"


def normalize_date(value: str) -> Result:
    """Validate MM/DD/YYYY; keep the text either way (dates stay text, REQ-06)."""
    if value.strip() == "":
        return "", None
    try:
        datetime.strptime(value, "%m/%d/%Y")
    except ValueError:
        return value, "invalid-date"
    return value, None


def normalize_license(value: str) -> Result:
    """Pure digits or blank pass; anything else is flagged, never altered (REQ-09)."""
    if value == "":
        return "", None
    if value.isdigit():
        return value, None
    return value, "non-standard-license"


def normalize_list(value: str) -> Result:
    """Standardize a multi-value cell to ``'; '`` delimiting (REQ-17)."""
    if value.strip() == "":
        return "", None
    parts = [part.strip() for part in re.split(r"[;,|]", value)]
    return "; ".join(part for part in parts if part), None


def strip_sigils(value: str) -> Result:
    """Strip NCLBGC's uniform ``L.``/``Q.`` account-number type-sigil.

    Operates on one value; the engine applies it per ``'; '`` element on the
    packed ``Qualifier_Number`` (``multi=True``) and once on the single
    ``License_Number`` — the same packing mechanism as every other multi column.
    A meaningful multi-letter prefix (``WV``, ``NC``) is not a sigil and is left
    intact (REQ-09 scope: the strip normalizes a content-free sigil, not the
    silent prefix-stripping REQ-09 forbids). The change is the engine's audited
    correction.
    """
    if value.strip() == "":
        return "", None
    match = _SIGIL.match(value)
    return (match.group(1) if match else value), None


def map_vocabulary(
    value: str, *, allowed: tuple[str, ...], mapping: Mapping[str, str] | None = None
) -> Result:
    """Case-folded vocabulary map; blank stays blank (never imputed, REQ-08)."""
    stripped = value.strip()
    if mapping is not None:
        mapped = mapping.get(stripped.casefold())
        if mapped is not None:
            return mapped, None
    if stripped == "":
        return "", None
    if stripped in allowed:
        return stripped, None
    return value, "out-of-vocabulary"
