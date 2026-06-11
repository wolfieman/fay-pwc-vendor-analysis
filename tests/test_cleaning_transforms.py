"""Unit tests for the pure value- and frame-level transforms.

All sample values are fabricated placeholders (example.com addresses,
555-prefixed phone numbers, invented company names).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from typing import ClassVar

import pandas as pd
import pytest

from vendorscope.cleaning.transforms import (
    apply_to_columns,
    clean_whitespace,
    deduplicate,
    hybrid_title_case,
    map_vocabulary,
    normalize_date,
    normalize_email,
    normalize_phone,
    normalize_text_id,
    split_pii,
    standardize_list,
    trim_all_text,
)

pytestmark = pytest.mark.unit

SUFFIXES = {"llc": "LLC", "incorporated": "Inc.", "inc": "Inc."}
PRESERVE = frozenset({"po", "nc", "llc"})


class TestCleanWhitespace:
    def test_trims_and_collapses(self):
        assert clean_whitespace("  Acme   Widgets  ") == ("Acme Widgets", None)

    def test_removes_invisible_characters(self):
        value = "Acme\u00a0Widgets\u200b"
        assert clean_whitespace(value) == ("Acme Widgets", None)

    def test_idempotent(self):
        once, _ = clean_whitespace("  a  b ")
        assert clean_whitespace(once) == (once, None)


class TestNormalizeEmail:
    def test_lowercases_valid_address(self):
        assert normalize_email("Pat.Sample@Example.COM") == (
            "pat.sample@example.com",
            None,
        )

    def test_rejects_missing_at(self):
        value, error = normalize_email("pat.sample.example.com")
        assert value == "pat.sample.example.com"
        assert error is not None

    def test_rejects_multiple_at(self):
        _, error = normalize_email("a@b@example.com")
        assert error is not None

    def test_blank_passes_through(self):
        assert normalize_email("") == ("", None)


class TestNormalizePhone:
    @pytest.mark.parametrize(
        "raw",
        [
            "(919) 555-0142",
            "919.555.0142",
            "9195550142",
            "1-919-555-0142",
        ],
    )
    def test_formats_us_numbers(self, raw):
        assert normalize_phone(raw) == ("919-555-0142", None)

    def test_rejects_short_number(self):
        value, error = normalize_phone("555-0142")
        assert value == "555-0142"
        assert error is not None

    def test_blank_passes_through(self):
        assert normalize_phone("") == ("", None)

    def test_idempotent(self):
        once, _ = normalize_phone("9195550142")
        assert normalize_phone(once) == (once, None)


class TestHybridTitleCase:
    def test_capitalizes_lowercase_name(self):
        value, _ = hybrid_title_case("acme widgets, llc", suffixes=SUFFIXES)
        assert value == "Acme Widgets, LLC"

    def test_preserves_acronyms_in_mixed_case(self):
        value, _ = hybrid_title_case("ABC Paving of raleigh", suffixes=SUFFIXES)
        assert value == "ABC Paving Of Raleigh"

    def test_preserves_camel_case(self):
        value, _ = hybrid_title_case("McDonald BuildRight", suffixes=SUFFIXES)
        assert value == "McDonald BuildRight"

    def test_all_caps_input_with_preserve_list(self):
        value, _ = hybrid_title_case("PO BOX 12 NC", preserve_upper=PRESERVE)
        assert value == "PO Box 12 NC"

    def test_standardizes_suffix_variants(self):
        value, _ = hybrid_title_case("Tarheel Plumbing Incorporated", suffixes=SUFFIXES)
        assert value == "Tarheel Plumbing Inc."

    def test_digit_leading_tokens_are_untouched(self):
        # Regression: ordinals and digit-led brand names must not become
        # "51St" / "42Yl".
        value, _ = hybrid_title_case("51st State inc.", suffixes=SUFFIXES)
        assert value == "51st State Inc."
        value, _ = hybrid_title_case("42yl", suffixes=SUFFIXES)
        assert value == "42yl"

    def test_idempotent(self):
        once, _ = hybrid_title_case(
            "ACME WIDGETS, LLC", suffixes=SUFFIXES, preserve_upper=PRESERVE
        )
        twice, _ = hybrid_title_case(once, suffixes=SUFFIXES, preserve_upper=PRESERVE)
        assert once == twice == "Acme Widgets, LLC"


class TestNormalizeDate:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("2024-01-15", "01/15/2024"),
            ("1/5/2024", "01/05/2024"),
            ("January 5, 2024", "01/05/2024"),
            ("01/15/2024", "01/15/2024"),
        ],
    )
    def test_accepted_formats(self, raw, expected):
        assert normalize_date(raw) == (expected, None)

    def test_rejects_impossible_calendar_date(self):
        value, error = normalize_date("02/30/2024")
        assert value == "02/30/2024"
        assert error is not None

    def test_rejects_garbage(self):
        _, error = normalize_date("next Tuesday")
        assert error is not None

    def test_blank_passes_through(self):
        assert normalize_date("") == ("", None)


class TestNormalizeTextId:
    def test_repairs_float_artifact(self):
        assert normalize_text_id("810.0") == ("810", None)

    def test_preserves_leading_zeros(self):
        assert normalize_text_id("02860") == ("02860", None)

    def test_leaves_alphanumeric_ids_alone(self):
        assert normalize_text_id("U-1234") == ("U-1234", None)


class TestStandardizeList:
    def test_rewrites_commas_and_pipes(self):
        value, _ = standardize_list("Building,Highway| Public Utilities")
        assert value == "Building; Highway; Public Utilities"

    def test_preserves_slash_inside_tokens(self):
        value, _ = standardize_list("Plumbing/Fire Sprinkler, Highway")
        assert value == "Plumbing/Fire Sprinkler; Highway"

    def test_idempotent(self):
        once, _ = standardize_list("A,B; C")
        assert standardize_list(once) == (once, None)


class TestMapVocabulary:
    MAP: ClassVar[dict[str, str]] = {
        "true": "Yes",
        "false": "No",
        "certified": "Certified",
    }

    def test_maps_case_insensitively(self):
        assert map_vocabulary("TRUE", self.MAP) == ("Yes", None)

    def test_canonical_value_is_stable(self):
        assert map_vocabulary("Certified", self.MAP) == ("Certified", None)

    def test_unmapped_value_is_violation(self):
        value, error = map_vocabulary("Maybe", self.MAP)
        assert value == "Maybe"
        assert error is not None

    def test_blank_passes_through(self):
        assert map_vocabulary("", self.MAP) == ("", None)


class TestFrameAppliers:
    def test_apply_logs_corrections_and_violations(self):
        df = pd.DataFrame(
            {
                "Email": ["Pat@Example.COM", "broken-address", ""],
            }
        )
        out, corrections, violations = apply_to_columns(
            df,
            ["Email"],
            lambda v: __import__(
                "vendorscope.cleaning.transforms", fromlist=["normalize_email"]
            ).normalize_email(v),
            table="t",
            rule="email",
        )
        assert out.loc[0, "Email"] == "pat@example.com"
        assert out.loc[1, "Email"] == "broken-address"
        assert len(corrections) == 1 and corrections[0].before.startswith("Pat")
        assert len(violations) == 1 and violations[0].row_id == 1

    def test_missing_columns_are_skipped(self):
        df = pd.DataFrame({"A": ["x"]})
        out, corrections, violations = apply_to_columns(
            df, ["Nope"], lambda v: (v, None), table="t", rule="r"
        )
        assert out.equals(df) and not corrections and not violations

    def test_trim_all_text_covers_every_column(self):
        df = pd.DataFrame({"A": [" x "], "B": [" y"]})
        out, corrections, _ = trim_all_text(df, table="t")
        assert list(out.iloc[0]) == ["x", "y"]
        assert len(corrections) == 2

    def test_input_frame_is_not_mutated(self):
        df = pd.DataFrame({"A": [" x "]})
        trim_all_text(df, table="t")
        assert df.loc[0, "A"] == " x "


class TestDeduplicate:
    def test_keeps_most_complete_row(self):
        df = pd.DataFrame(
            {
                "Name": ["Acme Widgets, LLC", "Acme Widgets, LLC"],
                "License": ["810", "810"],
                "City": ["", "Sampleville"],
            }
        )
        out, dropped = deduplicate(df, ["Name", "License"], table="t")
        assert len(out) == 1
        assert out.iloc[0]["City"] == "Sampleville"
        assert len(dropped) == 1 and dropped[0].rule == "dedup"

    def test_blank_keys_never_match_each_other(self):
        df = pd.DataFrame(
            {
                "Name": ["Acme Widgets, LLC", "Sample Paving Co."],
                "License": ["", ""],
            }
        )
        out, dropped = deduplicate(df, ["Name", "License"], table="t")
        assert len(out) == 2 and not dropped

    def test_tie_breaks_to_first_row(self):
        df = pd.DataFrame(
            {
                "Name": ["Acme Widgets, LLC"] * 2,
                "License": ["810"] * 2,
                "City": ["Sampleville", "Mocktown"],
            }
        )
        out, _ = deduplicate(df, ["Name", "License"], table="t")
        assert out.index.tolist() == [0]


class TestSplitPii:
    def test_separates_and_preserves_index(self):
        df = pd.DataFrame(
            {
                "Name": ["Acme Widgets, LLC"],
                "MainContactEmail": ["pat@example.com"],
            },
            index=[7],
        )
        public, pii = split_pii(df, ["MainContactEmail", "Missing"])
        assert "MainContactEmail" not in public.columns
        assert pii.columns.tolist() == ["MainContactEmail"]
        assert pii.index.tolist() == [7]
