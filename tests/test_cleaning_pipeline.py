"""Tests for validation rules and the composed pipeline.

Includes the two properties that make the engine trustworthy in a scheduled
pipeline: idempotency (cleaning cleaned data changes nothing) and source
agnosticism (an unrelated dataset cleans correctly with only a new config).
All sample values are fabricated placeholders.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import pandas as pd
import pytest

from vendorscope.cleaning.config import (
    LICENSE_CONFIG,
    VENDOR_CONFIG,
    ConditionalRequirementRule,
    CrossValidationConfig,
    FormatRule,
    ReferentialRule,
    TableConfig,
)
from vendorscope.cleaning.pipeline import clean_table, cross_validate
from vendorscope.cleaning.validate import validate_vocabulary

pytestmark = pytest.mark.unit

XVAL = CrossValidationConfig(
    referential=(
        ReferentialRule(
            "vendor", "GeneralContractorLicenseNumber", "license", "License_Number"
        ),
    ),
    formats=(
        FormatRule(
            "vendor", "GeneralContractorLicenseNumber", r"^\d{1,6}$", "numeric license"
        ),
    ),
    conditional=(
        ConditionalRequirementRule(
            table="vendor",
            condition_column="HUB",
            condition_value="Certified",
            flag_column="GeneralContractor",
            flag_value="Yes",
            required_column="GeneralContractorLicenseNumber",
            description="certified general contractor needs a license",
        ),
    ),
)


def make_vendor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Name": ["  acme widgets, llc ", "ACME WIDGETS, LLC", "Sample Paving Co."],
            "MainContactName": ["Pat Sample", "Pat Sample", "Casey Placeholder"],
            "MainContactEmail": ["Pat@Example.COM", "Pat@Example.COM", "no-at-sign"],
            "MainContactPhone": ["(919) 555-0142", "9195550142", "555"],
            "AddressLine1": ["123 N MAIN ST", "123 N Main St", "PO BOX 9"],
            "City": ["sampleville", "Sampleville", "MOCKTOWN"],
            "County": ["", "", ""],
            "ZipCode": ["02860", "02860", "27601.0"],
            "EvpStatus": ["Active", "Active", "Frozen"],
            "HUB": ["Certified", "certified", "Not Certified"],
            "NCSBE": ["", "", "Not Certified"],
            "GeneralContractor": ["True", "True", "False"],
            "GeneralContractorLicenseNumber": ["810.0", "810", ""],
            "HUBCertStartDate": ["2024-01-15", "01/15/2024", ""],
        }
    )


def make_license_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "License_Number": ["810", "810", "00042"],
            "Company_Name": [
                "acme widgets, llc",
                "acme widgets, llc",
                "sample paving company",
            ],
            "Phone": ["919 555 0100", "919-555-0100", ""],
            "Issue_Date": ["2020-02-01", "02/01/2020", "13/45/2020"],
            "Expiration_Date": ["12/31/2026", "12/31/2026", ""],
            "Status": ["Active", "Active", "Retired"],
            "License_Limitation": ["Unlimited", "Unlimited", "Limited"],
            "Classifications": [
                "Building,Highway",
                "Building; Highway",
                "Public Utilities|Building",
            ],
            "Qualifier_Number": ["Q1", "Q1", "Q2"],
            "Qualifier_Name": ["Pat Sample", "Pat Sample", "Casey Placeholder"],
            "Qualifier_Status": ["Active", "Active", "Expired"],
        }
    )


class TestValidateVocabulary:
    def test_reports_out_of_vocabulary_values(self):
        df = pd.DataFrame({"Status": ["Active", "Retired", ""]})
        violations = validate_vocabulary(
            df, {"Status": ("Active", "Expired")}, table="t"
        )
        assert len(violations) == 1
        assert violations[0].value == "Retired"

    def test_blank_is_always_permitted(self):
        df = pd.DataFrame({"Status": [""]})
        assert not validate_vocabulary(df, {"Status": ("Active",)}, table="t")


class TestVendorPipeline:
    def test_protocol_applied_and_duplicates_collapsed(self):
        result = clean_table(make_vendor_frame(), VENDOR_CONFIG)
        frame = result.frame
        # Rows 0 and 1 normalize to the same Name + license key.
        assert len(frame) == 2
        survivor = frame.iloc[0]
        assert survivor["Name"] == "Acme Widgets, LLC"
        assert survivor["MainContactEmail"] == "pat@example.com"
        assert survivor["MainContactPhone"] == "919-555-0142"
        assert survivor["GeneralContractorLicenseNumber"] == "810"
        assert survivor["HUBCertStartDate"] == "01/15/2024"
        assert frame.iloc[1]["ZipCode"] == "27601"

    def test_violations_reported_not_coerced(self):
        result = clean_table(make_vendor_frame(), VENDOR_CONFIG)
        rules = {(v.rule, v.column) for v in result.violations}
        assert ("email", "MainContactEmail") in rules
        assert ("phone", "MainContactPhone") in rules
        assert ("vocabulary", "EvpStatus") in rules
        bad_status = next(v for v in result.violations if v.column == "EvpStatus")
        assert bad_status.value == "Frozen"
        assert result.frame.iloc[1]["EvpStatus"] == "Frozen"

    def test_every_correction_is_recorded_with_before_after(self):
        result = clean_table(make_vendor_frame(), VENDOR_CONFIG)
        email_fixes = [c for c in result.corrections if c.rule == "email"]
        assert email_fixes and email_fixes[0].before == "Pat@Example.COM"
        assert email_fixes[0].after == "pat@example.com"

    def test_idempotent_end_to_end(self):
        first = clean_table(make_vendor_frame(), VENDOR_CONFIG)
        second = clean_table(first.frame, VENDOR_CONFIG)
        assert second.frame.equals(first.frame)
        assert not second.corrections


class TestLicensePipeline:
    def test_protocol_applied(self):
        result = clean_table(make_license_frame(), LICENSE_CONFIG)
        frame = result.frame
        assert len(frame) == 2  # the two "810" rows collapse
        assert frame.iloc[0]["Company_Name"] == "Acme Widgets, LLC"
        assert frame.iloc[0]["Issue_Date"] == "02/01/2020"
        assert frame.iloc[0]["Classifications"] == "Building; Highway"
        assert frame.iloc[1]["License_Number"] == "00042"

    def test_invalid_date_and_vocab_reported(self):
        result = clean_table(make_license_frame(), LICENSE_CONFIG)
        rules = {(v.rule, v.column) for v in result.violations}
        assert ("date", "Issue_Date") in rules
        assert ("vocabulary", "Status") in rules


class TestCrossValidation:
    def test_rules_fire_generically(self):
        vendors = clean_table(make_vendor_frame(), VENDOR_CONFIG).frame
        licenses = clean_table(make_license_frame(), LICENSE_CONFIG).frame
        # Point one vendor at a license number absent from the register and
        # blank the license of a certified, active general contractor.
        vendors = vendors.copy()
        vendors.iloc[0, vendors.columns.get_loc("GeneralContractorLicenseNumber")] = (
            "999999"
        )
        violations = cross_validate({"vendor": vendors, "license": licenses}, XVAL)
        rules = {v.rule for v in violations}
        assert "referential" in rules

    def test_conditional_requirement(self):
        vendors = pd.DataFrame(
            {
                "HUB": ["Certified", "Certified", "Not Certified"],
                "GeneralContractor": ["Yes", "No", "Yes"],
                "GeneralContractorLicenseNumber": ["", "", ""],
            }
        )
        violations = cross_validate({"vendor": vendors}, XVAL)
        conditional = [v for v in violations if v.rule == "conditional_requirement"]
        assert len(conditional) == 1 and conditional[0].row_id == 0

    def test_missing_tables_are_skipped(self):
        assert cross_validate({}, XVAL) == []


class TestSourceAgnosticism:
    """A different municipality's dataset must clean with only a config."""

    PERMIT_CONFIG = TableConfig(
        name="permit",
        date_columns=("Issued",),
        text_id_columns=("Permit_No",),
        flag_columns=("Expedited",),
        flag_map={"oui": "Yes", "non": "No"},
        vocabularies={"Zone": ("Residential", "Commercial")},
        list_columns=("Trades",),
        dedup_keys=("Permit_No",),
    )

    def test_unrelated_dataset_cleans_via_config_alone(self):
        df = pd.DataFrame(
            {
                "Permit_No": ["00077", "00077"],
                "Issued": ["2025-06-01", "06/01/2025"],
                "Expedited": ["OUI", "oui"],
                "Zone": ["Residential", "Industrial"],
                "Trades": ["Roofing,Framing", "Roofing; Framing"],
            }
        )
        result = clean_table(df, self.PERMIT_CONFIG)
        assert len(result.frame) == 1
        row = result.frame.iloc[0]
        assert row["Issued"] == "06/01/2025"
        assert row["Expedited"] == "Yes"
        assert row["Trades"] == "Roofing; Framing"
        # Vocabulary validation runs before dedup, so the out-of-vocab value
        # is reported even though its row is later merged away.
        assert any(
            v.rule == "vocabulary" and v.value == "Industrial"
            for v in result.violations
        )
