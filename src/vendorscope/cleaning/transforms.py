"""Pure cleaning transforms for the VendorScope pipeline.

Every function here is pure: no file IO, no globals, no mutation of inputs.
Value-level normalizers share one contract — they return
``(normalized_value, error_message_or_None)`` — so frame-level appliers can
treat "always succeeds" and "validated" normalizers uniformly, logging a
Correction when a value changes and a Violation when one fails validation.
Failed values are reported and left unchanged, never silently coerced.

All transforms are idempotent: applying one twice yields the first result.
The test suite asserts this property because the pipeline must be safe to
re-run over its own output.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import cast

import pandas as pd

ValueResult = tuple[str, str | None]
ValueFn = Callable[[str], ValueResult]

# Invisible characters that survive copy/paste from web portals and Excel and
# defeat literal equality joins, hence stripped during whitespace cleanup.
_INVISIBLE = dict.fromkeys(map(ord, "\u00a0\u200b\u200c\u200d\ufeff"), " ")

_ACCEPTED_DATE_FORMATS = (
    # %m/%d/%Y is listed first so canonical values round-trip unchanged;
    # the rest cover common Excel and ISO export shapes seen upstream.
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%Y-%m-%d",
    "%m/%d/%y",
    "%B %d, %Y",
    "%d-%b-%Y",
)


@dataclass(frozen=True)
class Correction:
    """One recorded change to one cell, for the provenance log."""

    table: str
    row_id: Hashable
    column: str
    before: str
    after: str
    rule: str


@dataclass(frozen=True)
class Violation:
    """One detected rule violation; the offending value is left in place."""

    table: str
    row_id: Hashable
    column: str
    value: str
    rule: str
    message: str


# --------------------------------------------------------------------------
# Value-level normalizers
# --------------------------------------------------------------------------


def clean_whitespace(value: str) -> ValueResult:
    """Trim, collapse runs of whitespace, and drop invisible characters."""
    cleaned = re.sub(r"\s+", " ", value.translate(_INVISIBLE)).strip()
    return cleaned, None


def normalize_email(value: str) -> ValueResult:
    """Lowercase an email address; reject anything without exactly one @.

    Invalid addresses are reported, not lowercased: corrections should only
    ever touch values the pipeline considers well-formed.
    """
    if not value:
        return value, None
    if value.count("@") != 1:
        return value, "email must contain exactly one @"
    return value.lower(), None


def normalize_phone(value: str) -> ValueResult:
    """Format a US phone number as ###-###-####.

    Accepts ten digits in any punctuation, or eleven digits with a leading
    country code 1. Anything else (extensions, international, short numbers)
    is reported unchanged rather than guessed at.
    """
    if not value:
        return value, None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return value, "phone is not a 10-digit US number"
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}", None


def _capitalize_token(token: str) -> str:
    """Capitalize one word without ``str.title``'s apostrophe splitting."""
    for index, char in enumerate(token):
        if char.isalpha():
            return token[:index] + char.upper() + token[index + 1 :].lower()
    return token


def hybrid_title_case(
    value: str,
    *,
    suffixes: Mapping[str, str] | None = None,
    preserve_upper: frozenset[str] = frozenset(),
) -> ValueResult:
    """Title-case a name while preserving acronyms and CamelCase.

    Mixed-case input is trusted: only all-lowercase tokens are capitalized,
    so acronyms (``ABC``) and intentional casing (``McDonald``) survive.
    ALL-CAPS input carries no per-token case signal, so every token is
    capitalized except those in ``preserve_upper``. When ``suffixes`` is
    given, the final token is rewritten to its canonical legal form.
    """
    if not value:
        return value, None
    tokens = value.split(" ")
    if value.isupper():
        # Tokens led by a digit ("42YL", "51ST") carry no usable case
        # signal and are routinely brand spellings or ordinals: leave them.
        tokens = [
            token.upper()
            if token.strip(".,").casefold() in preserve_upper
            else _capitalize_token(token)
            if token[:1].isalpha()
            else token
            for token in tokens
        ]
    else:
        tokens = [
            _capitalize_token(token)
            if token.islower() and token[:1].isalpha()
            else token
            for token in tokens
        ]
    if suffixes and tokens:
        last = tokens[-1]
        canonical = suffixes.get(last.strip(".,").casefold())
        if canonical:
            tokens[-1] = canonical
    return " ".join(tokens), None


def normalize_date(value: str) -> ValueResult:
    """Render a date as MM/DD/YYYY text, or report it if unparseable.

    Output is text by design: the protocol stores dates as strings to keep
    CSV round-trips and leading-zero formats stable across tools.
    """
    if not value:
        return value, None
    for fmt in _ACCEPTED_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%m/%d/%Y"), None
        except ValueError:
            continue
    return value, "unrecognized or invalid calendar date"


def normalize_text_id(value: str) -> ValueResult:
    """Repair numeric coercion of text identifiers (e.g. ``810.0`` -> ``810``).

    Upstream Excel handling routinely converts license numbers and ZIPs to
    floats; the trailing ``.0`` is an artifact, not data. Leading zeros are
    preserved because the value never becomes numeric here.
    """
    if value.endswith(".0") and value[:-2].isdigit():
        return value[:-2], None
    return value, None


def standardize_list(value: str, *, delimiters: str = ";,|") -> ValueResult:
    """Rewrite a delimited list as ``token; token; ...``.

    Slash is deliberately not a delimiter because it appears inside
    legitimate tokens (e.g. ``Plumbing/Fire Sprinkler``).
    """
    if not value:
        return value, None
    tokens = [t.strip() for t in re.split(f"[{re.escape(delimiters)}]", value)]
    return "; ".join(t for t in tokens if t), None


def map_vocabulary(value: str, mapping: Mapping[str, str]) -> ValueResult:
    """Translate a raw value into a controlled vocabulary via ``mapping``.

    Unmapped non-blank values are violations: inventing a category would be
    imputation, which the protocol forbids.
    """
    if not value:
        return value, None
    mapped = mapping.get(value.casefold())
    if mapped is None:
        return value, "value not in expected source vocabulary"
    return mapped, None


# --------------------------------------------------------------------------
# Frame-level appliers (pure: copy in, copy out)
# --------------------------------------------------------------------------


def apply_to_columns(
    df: pd.DataFrame,
    columns: Sequence[str],
    fn: ValueFn,
    *,
    table: str,
    rule: str,
) -> tuple[pd.DataFrame, list[Correction], list[Violation]]:
    """Apply a value normalizer to columns, logging changes and failures.

    Columns absent from ``df`` are skipped so one configuration can serve
    partial extracts. Non-string cells are passed through untouched; the
    orchestrator reads everything as text precisely to avoid that case.
    """
    out = df.copy()
    corrections: list[Correction] = []
    violations: list[Violation] = []
    for column in columns:
        if column not in out.columns:
            continue
        for row_id, original in out[column].items():
            if not isinstance(original, str):
                continue
            new_value, error = fn(original)
            if error is not None:
                violations.append(
                    Violation(
                        table=table,
                        row_id=row_id,
                        column=column,
                        value=original,
                        rule=rule,
                        message=error,
                    )
                )
            elif new_value != original:
                corrections.append(
                    Correction(
                        table=table,
                        row_id=row_id,
                        column=column,
                        before=original,
                        after=new_value,
                        rule=rule,
                    )
                )
                out.loc[row_id, column] = new_value
    return out, corrections, violations


def trim_all_text(
    df: pd.DataFrame,
    *,
    table: str,
) -> tuple[pd.DataFrame, list[Correction], list[Violation]]:
    """Apply whitespace cleanup to every column of the frame."""
    return apply_to_columns(
        df,
        list(df.columns),
        clean_whitespace,
        table=table,
        rule="trim",
    )


def deduplicate(
    df: pd.DataFrame,
    keys: Sequence[str],
    *,
    table: str,
) -> tuple[pd.DataFrame, list[Correction]]:
    """Drop duplicate rows on ``keys``, keeping the most complete row.

    Rows with any blank key value never match each other: two unnamed or
    unlicensed records are not evidence of the same entity. Ties on
    completeness break by original row order, making the result
    deterministic. Each drop is logged with the surviving row's id.
    """
    out = df.copy()
    key_frame = out[list(keys)].astype(str)
    # all(axis=1) yields a Series here; the pandas stubs over-broaden to Series|bool.
    eligible = cast("pd.Series", key_frame.ne("").all(axis=1))
    completeness = out.astype(str).ne("").sum(axis=1)

    survivors_by_key: dict[tuple[str, ...], tuple[int, Hashable]] = {}
    drops: list[Hashable] = []
    corrections: list[Correction] = []
    for row_id in out.index:
        if not eligible.loc[row_id]:
            continue
        key = tuple(key_frame.loc[row_id])
        score = int(completeness.loc[row_id])
        if key not in survivors_by_key:
            survivors_by_key[key] = (score, row_id)
            continue
        best_score, best_row = survivors_by_key[key]
        if score > best_score:
            survivors_by_key[key] = (score, row_id)
            loser, winner = best_row, row_id
        else:
            loser, winner = row_id, survivors_by_key[key][1]
        drops.append(loser)
        corrections.append(
            Correction(
                table=table,
                row_id=loser,
                column="|".join(keys),
                before="duplicate row",
                after=f"merged into row {winner}",
                rule="dedup",
            )
        )
    return out.drop(index=drops), corrections


def split_pii(
    df: pd.DataFrame,
    pii_columns: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate PII columns from a frame for a publishable export.

    Returns ``(public_frame, pii_frame)``; the PII frame keeps the original
    index so the two can be rejoined privately when needed.
    """
    present = [c for c in pii_columns if c in df.columns]
    public_frame = df.drop(columns=present)
    pii_frame = df.loc[:, present].copy()
    return public_frame, pii_frame
