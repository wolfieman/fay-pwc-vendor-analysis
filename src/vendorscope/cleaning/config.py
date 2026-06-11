"""Configuration objects for the VendorScope cleaning engine.

The engine in ``transforms.py``, ``validate.py``, and ``pipeline.py`` is
source-agnostic: it knows nothing about any particular dataset. Everything
dataset-specific — column roles, controlled vocabularies, value mappings,
dedup keys, PII designation, cross-table rules — is carried by the config
objects defined here. Cleaning a different source is a config change, not a
code change.

The module ends with one worked example: the configuration for a public
vendor-master / contractor-license case study. Its vocabularies and value
mappings were derived from the source's observed raw values rather than
assumed.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Engine defaults (plain data; any config may override them)
# ---------------------------------------------------------------------------

# Canonical legal-suffix spellings, keyed by the case-folded final token of a
# business name (punctuation stripped). Variants collapse onto one canonical
# form because downstream joins and dedup compare names literally.
DEFAULT_LEGAL_SUFFIXES: Mapping[str, str] = {
    "llc": "LLC",
    "l.l.c": "LLC",
    "llc.": "LLC",
    "inc": "Inc.",
    "inc.": "Inc.",
    "incorporated": "Inc.",
    "co": "Co.",
    "co.": "Co.",
    "company": "Co.",
    "corp": "Corp.",
    "corp.": "Corp.",
    "corporation": "Corp.",
    "ltd": "Ltd.",
    "ltd.": "Ltd.",
    "limited": "Ltd.",
}

# Tokens kept fully uppercase when a source string arrives in ALL CAPS and
# per-token case information is therefore unrecoverable.
DEFAULT_UPPERCASE_TOKENS: frozenset[str] = frozenset(
    {
        "llc",
        "po",
        "us",
        "usa",
        "ne",
        "nw",
        "se",
        "sw",
        "ii",
        "iii",
        "iv",
        "dba",
        "pa",
        "pc",
        "pllc",
    }
)

# Case-folded source flag value -> canonical flag. Covers the common ways
# tabular sources spell booleans; a config may supply its own map instead.
DEFAULT_FLAG_MAP: Mapping[str, str] = {
    "yes": "Yes",
    "y": "Yes",
    "true": "Yes",
    "1": "Yes",
    "x": "Yes",
    "no": "No",
    "n": "No",
    "false": "No",
    "0": "No",
}


@dataclass(frozen=True)
class TableConfig:
    """Cleaning configuration for one tabular dataset.

    Every attribute defaults to "not applicable", so a config only declares
    the column roles its dataset actually has; the pipeline skips the rest.

    Attributes:
        name: Table identifier used in correction/violation records.
        email_columns: Columns normalized as email addresses.
        phone_columns: Columns normalized to ###-###-#### format.
        business_name_columns: Columns receiving hybrid title case plus
            legal-suffix standardization.
        address_columns: Columns receiving proper-case treatment only.
        date_columns: Columns enforced to MM/DD/YYYY, stored as text.
        text_id_columns: Identifier columns that must stay text (license
            numbers, ZIP codes); numeric-coercion artifacts are repaired.
        flag_columns: Boolean-ish columns normalized through ``flag_map``.
        flag_map: Case-folded raw value -> canonical flag value.
        mapped_vocab_columns: Column -> mapping used to translate raw values
            into that column's controlled vocabulary.
        vocabularies: Column -> allowed values; validated and reported,
            never coerced. Blank means missing and is always permitted.
        list_columns: Multi-value columns standardized to "; " delimiting.
        list_delimiters: Characters accepted as input delimiters.
        dedup_keys: Columns forming the duplicate-detection key.
        pii_columns: Columns split out of public exports.
        name_suffixes: Legal-suffix canonicalization map for name columns.
        preserve_upper: Tokens kept uppercase in ALL-CAPS inputs.
    """

    name: str
    email_columns: tuple[str, ...] = ()
    phone_columns: tuple[str, ...] = ()
    business_name_columns: tuple[str, ...] = ()
    address_columns: tuple[str, ...] = ()
    date_columns: tuple[str, ...] = ()
    text_id_columns: tuple[str, ...] = ()
    flag_columns: tuple[str, ...] = ()
    flag_map: Mapping[str, str] = field(default_factory=lambda: dict(DEFAULT_FLAG_MAP))
    mapped_vocab_columns: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    vocabularies: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    list_columns: tuple[str, ...] = ()
    list_delimiters: str = ";,|"
    dedup_keys: tuple[str, ...] = ()
    pii_columns: tuple[str, ...] = ()
    name_suffixes: Mapping[str, str] = field(
        default_factory=lambda: dict(DEFAULT_LEGAL_SUFFIXES)
    )
    preserve_upper: frozenset[str] = DEFAULT_UPPERCASE_TOKENS


# ---------------------------------------------------------------------------
# Cross-table validation rules (generic shapes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReferentialRule:
    """Every non-blank ``left_table.left_key`` must exist in
    ``right_table.right_key``. Reported, never dropped: orphan handling is
    an analytical decision that belongs downstream, not in cleaning."""

    left_table: str
    left_key: str
    right_table: str
    right_key: str


@dataclass(frozen=True)
class FormatRule:
    """Non-blank values of ``table.column`` must match ``pattern``."""

    table: str
    column: str
    pattern: str
    description: str = ""


@dataclass(frozen=True)
class ConditionalRequirementRule:
    """When ``condition_column == condition_value`` and
    ``flag_column == flag_value``, ``required_column`` must be non-blank.

    Expresses rules of the form "certified vendors active in a trade must
    hold that trade's license" without naming any dataset in engine code.
    """

    table: str
    condition_column: str
    condition_value: str
    flag_column: str
    flag_value: str
    required_column: str
    description: str = ""


@dataclass(frozen=True)
class CrossValidationConfig:
    """All cross-table rules for one engine run."""

    referential: tuple[ReferentialRule, ...] = ()
    formats: tuple[FormatRule, ...] = ()
    conditional: tuple[ConditionalRequirementRule, ...] = ()


# ---------------------------------------------------------------------------
# CASE STUDY: public vendor master + contractor license register
# ---------------------------------------------------------------------------
# Vocabularies below were read from the source's actual raw values, not
# assumed. Notably, the vendor source publishes HUB and NCSBE as
# Certified / Not Certified (blank when unevaluated), trade-participation
# flags as True/False, and a literal "None" limitation alongside
# Limited / Intermediate / Unlimited.

_CERTIFICATION_MAP: Mapping[str, str] = {
    "certified": "Certified",
    "not certified": "Not Certified",
}

VENDOR_CONFIG = TableConfig(
    name="vendor",
    email_columns=("MainContactEmail",),
    phone_columns=("MainContactPhone",),
    business_name_columns=("Name",),
    address_columns=("AddressLine1", "City", "County"),
    date_columns=(
        "HUBCertStartDate",
        "HUBCertEndDate",
        "NCSBECertStartDate",
        "NCSBECertEndDate",
    ),
    text_id_columns=(
        "ZipCode",
        "GeneralContractorLicenseNumber",
        "ElectricalLicenseNumber",
        "PlumbingFireSprinklerLicenseNumber",
        "MechanicalHeatingLicenseNumber",
        "TradesSubContractorLicenseNumber",
    ),
    flag_columns=(
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
    ),
    mapped_vocab_columns={
        "HUB": _CERTIFICATION_MAP,
        "NCSBE": _CERTIFICATION_MAP,
    },
    vocabularies={
        "HUB": ("Certified", "Not Certified"),
        "NCSBE": ("Certified", "Not Certified"),
        "EvpStatus": ("Active", "Pending", "Debarred"),
        "NCeProcurement": ("Active", "Inactive", "Not Applicable"),
        "HUBCategory": (
            "American Indian",
            "Asian",
            "Black",
            "Disabled",
            "Female",
            "Hispanic",
            "Socially and Economically Disadvantaged",
        ),
        "GeneralContractorLimitation": ("Limited", "Intermediate", "Unlimited", "None"),
    },
    dedup_keys=("Name", "GeneralContractorLicenseNumber"),
    pii_columns=("MainContactName", "MainContactEmail", "MainContactPhone"),
)

LICENSE_CONFIG = TableConfig(
    name="license",
    phone_columns=("Phone",),
    business_name_columns=("Company_Name", "Qualifier_Name"),
    address_columns=("Address",),
    date_columns=("Issue_Date", "Expiration_Date"),
    text_id_columns=("License_Number", "Qualifier_Number"),
    vocabularies={
        "Status": ("Active", "Expired", "Suspended", "Revoked", "Inactive", "Pending"),
        "License_Limitation": ("Limited", "Intermediate", "Unlimited"),
        "Qualifier_Status": ("Active", "Inactive", "Expired"),
    },
    list_columns=("Classifications",),
    dedup_keys=("License_Number",),
    pii_columns=("Phone", "Qualifier_Name"),
)

# License-number shapes are configurable because the issuing board's format
# is not formally documented in the source; bounds reflect observed data.
CROSS_VALIDATION_CONFIG = CrossValidationConfig(
    referential=(
        ReferentialRule(
            left_table="vendor",
            left_key="GeneralContractorLicenseNumber",
            right_table="license",
            right_key="License_Number",
        ),
    ),
    formats=(
        FormatRule(
            "vendor",
            "GeneralContractorLicenseNumber",
            r"^\d{1,6}$",
            "general contractor license is numeric",
        ),
        FormatRule(
            "vendor",
            "ElectricalLicenseNumber",
            r"^[A-Za-z]?\d{1,6}(-[A-Za-z]{1,3})?$",
            "electrical license is numeric with optional level code",
        ),
        FormatRule(
            "vendor",
            "PlumbingFireSprinklerLicenseNumber",
            r"^\d{1,6}$",
            "plumbing license is numeric",
        ),
        FormatRule(
            "vendor",
            "MechanicalHeatingLicenseNumber",
            r"^\d{1,6}$",
            "mechanical license is numeric",
        ),
        FormatRule(
            "vendor",
            "TradesSubContractorLicenseNumber",
            r"^[A-Za-z0-9-]{1,12}$",
            "subcontractor license is a short alphanumeric code",
        ),
    ),
    conditional=tuple(
        ConditionalRequirementRule(
            table="vendor",
            condition_column="HUB",
            condition_value="Certified",
            flag_column=flag,
            flag_value="Yes",
            required_column=license_column,
            description=f"HUB-certified vendor active as {flag} "
            "must hold that trade's license",
        )
        for flag, license_column in (
            ("GeneralContractor", "GeneralContractorLicenseNumber"),
            ("ElectricalContractor", "ElectricalLicenseNumber"),
            ("PlumbingFireSprinklerContractor", "PlumbingFireSprinklerLicenseNumber"),
            ("MechanicalHeating", "MechanicalHeatingLicenseNumber"),
            ("TradesSubContractor", "TradesSubContractorLicenseNumber"),
        )
    ),
)
