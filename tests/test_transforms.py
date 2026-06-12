"""Pure normalizer contracts: the carried-forward findings as test cases.

Each transform is ``(value) -> (normalized, error)``: it reports a contract
breach as an error code and leaves the value unchanged (report-don't-coerce),
never imputing or prefix-stripping. Synthetic email/phone literals live here in
the test source, never under ``tests/fixtures/`` (REQ-16 sweep).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pytest

from vendorscope.cleaning import transforms as t


@pytest.mark.unit
def test_collapse_whitespace_trims_collapses_and_strips_invisibles() -> None:
    assert t.collapse_whitespace("  a​ b\tc  ") == ("a b c", None)
    assert t.collapse_whitespace("﻿plain") == ("plain", None)
    assert t.collapse_whitespace("") == ("", None)


@pytest.mark.unit
def test_business_name_hybrid_casing() -> None:
    # all-caps title-cased, legal suffix preserved
    assert t.business_name_case("ACME PLUMBING LLC") == ("Acme Plumbing LLC", None)
    # digit-led tokens carry no case signal: left unchanged (REQ-10)
    assert t.business_name_case("42YL CONSTRUCTION") == ("42YL Construction", None)
    assert t.business_name_case("51ST STREET BUILDERS") == (
        "51ST Street Builders",
        None,
    )
    assert t.business_name_case("") == ("", None)


@pytest.mark.unit
def test_email_lowercases_or_flags() -> None:
    assert t.normalize_email("Contact@Example.COM") == ("contact@example.com", None)
    bad, err = t.normalize_email("not-an-email")
    assert bad == "not-an-email" and err == "invalid-email"
    assert t.normalize_email("") == ("", None)


@pytest.mark.unit
def test_phone_formats_or_flags() -> None:
    assert t.normalize_phone("9195550100") == ("919-555-0100", None)
    assert t.normalize_phone("(919) 555.0100") == ("919-555-0100", None)
    short, err = t.normalize_phone("5550100")
    assert short == "5550100" and err == "invalid-phone"
    assert t.normalize_phone("") == ("", None)


@pytest.mark.unit
def test_date_keeps_text_or_flags() -> None:
    assert t.normalize_date("01/15/2026") == ("01/15/2026", None)
    bad, err = t.normalize_date("2026-01-15")
    assert bad == "2026-01-15" and err == "invalid-date"
    assert t.normalize_date("") == ("", None)


@pytest.mark.unit
def test_license_id_never_prefix_stripped() -> None:
    # pure digits pass; blank passes; anything else is flagged but left intact (REQ-09)
    assert t.normalize_license("67579") == ("67579", None)
    assert t.normalize_license("") == ("", None)
    for raw in ("WV063716", "L.106057", "67579; NC67579", "NY Lic: 2045482"):
        out, err = t.normalize_license(raw)
        assert out == raw and err == "non-standard-license"


@pytest.mark.unit
def test_list_standardizes_to_semicolon_space() -> None:
    assert t.normalize_list("Building, Highway;Water") == (
        "Building; Highway; Water",
        None,
    )
    assert t.normalize_list("Single") == ("Single", None)
    assert t.normalize_list("") == ("", None)


@pytest.mark.unit
def test_vocabulary_map_is_case_folded_and_blank_tolerant() -> None:
    flag = {"true": "Yes", "false": "No"}
    assert t.map_vocabulary("True", allowed=("Yes", "No"), mapping=flag) == (
        "Yes",
        None,
    )
    assert t.map_vocabulary("FALSE", allowed=("Yes", "No"), mapping=flag) == (
        "No",
        None,
    )
    # blank is unevaluated, never imputed
    assert t.map_vocabulary("", allowed=("Certified", "Not Certified")) == ("", None)
    assert t.map_vocabulary("Certified", allowed=("Certified", "Not Certified")) == (
        "Certified",
        None,
    )
    bad, err = t.map_vocabulary("Maybe", allowed=("Certified", "Not Certified"))
    assert bad == "Maybe" and err == "out-of-vocabulary"
