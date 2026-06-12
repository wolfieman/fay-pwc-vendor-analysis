"""The eVP table configuration: roles, vocabularies, keys, and the manifest.

``EXPECTED_COLUMNS`` is the single source of the field manifest (REQ-13): tests
assert against it, never a literal count. ``SNAKE_CASE`` is the rename contract
(applied once at processed-write, REQ-13/4.2); its values are unique so two
source columns can never silently merge. The vocabularies are encoded from the
slice-1 profile and pinned to the data dictionary by the agreement test.

Acquisition constants live here, not inline in the client (REQ-02).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

# ---- acquisition (REQ-01, REQ-02, REQ-03) ----
RECORD_ID = "20199579-3165-f111-a824-001dd812e0a9"
RESULTS_URL = f"https://evp.nc.gov/vendors/vendordetails/?id={RECORD_ID}&page=1"
# Numeric optionset codes echoed by the form, recorded for the repair runbook.
FILTER_STATUS_CODE = "1"  # Active
FILTER_CLASSIFICATION_CODE = "790550003"  # Public Utilities
RECORD_FLOOR = 500  # confirmed at the slice-1 owner checkpoint (documented pull ~570)

# ---- vocabularies (read from the source, never assumed; REQ-08) ----
FLAG_MAP: dict[str, str] = {"true": "Yes", "false": "No"}
FLAG_ALLOWED = ("Yes", "No")
HUB_STATES = ("Certified", "Not Certified")
HUB_CATEGORIES = (
    "Black",
    "Female",
    "Hispanic",
    "American Indian",
    "Disabled",
    "Asian American",
    "Socially and Economically Disadvantaged",
)
GC_LIMITATIONS = ("Unlimited", "None", "Limited", "Intermediate")
ELECTRICAL_LEVELS = ("None", "Unlimited", "Limited", "Intermediate")


@dataclass(frozen=True, slots=True)
class ColumnRule:
    """One column's cleaning role plus, for vocabulary roles, its allowed set."""

    role: str
    allowed: tuple[str, ...] = ()
    mapping: Mapping[str, str] | None = None


@dataclass(frozen=True, slots=True)
class TableConfig:
    name: str
    columns: dict[str, ColumnRule]
    dedup_key: tuple[str, ...]
    red_columns: tuple[str, ...] = field(default_factory=tuple)


def _vocab(allowed: tuple[str, ...]) -> ColumnRule:
    return ColumnRule("vocab", allowed=allowed)


def _flag() -> ColumnRule:
    return ColumnRule("flag", allowed=FLAG_ALLOWED, mapping=FLAG_MAP)


# Column roles, in observed source order. This ordered mapping *is* the manifest.
_COLUMNS: dict[str, ColumnRule] = {
    "Name": ColumnRule("name"),
    "MainContactName": ColumnRule("whitespace"),
    "MainContactEmail": ColumnRule("email"),
    "MainContactPhone": ColumnRule("phone"),
    "AddressLine1": ColumnRule("whitespace"),
    "City": ColumnRule("whitespace"),
    "State": ColumnRule("whitespace"),
    "ZipCode": ColumnRule("whitespace"),
    "County": ColumnRule("whitespace"),
    "Country": ColumnRule("whitespace"),
    "URL": ColumnRule("whitespace"),
    "EvpStatus": _vocab(("Active", "Pending", "Debarred")),
    "NCeProcurement": _vocab(("Active", "Inactive", "Not Applicable")),
    "HUB": _vocab(HUB_STATES),
    "HUBCategory": _vocab(HUB_CATEGORIES),
    "HUBCertStartDate": ColumnRule("date"),
    "HUBCertEndDate": ColumnRule("date"),
    "NCSBE": _vocab(HUB_STATES),
    "NCSBECertStartDate": ColumnRule("date"),
    "NCSBECertEndDate": ColumnRule("date"),
    "SmallBusiness": _flag(),
    "DBE": _flag(),
    "NPWC": _flag(),
    "GeneralContractor": _flag(),
    "GeneralContractorLimitation": _vocab(GC_LIMITATIONS),
    "GeneralContractorWorkClassification": ColumnRule("whitespace"),
    "GeneralContractorLicenseNumber": ColumnRule("license"),
    "ElectricalContractor": _flag(),
    "ElectricalLicenseSpecialties": ColumnRule("whitespace"),
    "ElectricalLicenseLevel": _vocab(ELECTRICAL_LEVELS),
    "ElectricalLicenseNumber": ColumnRule("license"),
    "PlumbingFireSprinklerContractor": _flag(),
    "PlumbingFireSprinklerLicenseClassifications": ColumnRule("whitespace"),
    "PlumbingFireSprinklerLicenseNumber": ColumnRule("license"),
    "MechanicalHeating": _flag(),
    "MechanicalHeatingLicenseClassifications": ColumnRule("whitespace"),
    "MechanicalHeatingLicenseNumber": ColumnRule("license"),
    "TradesSubContractor": _flag(),
    "TradesSubContractorLicenseNumber": ColumnRule("license"),
    "ArchitecturalServices": _flag(),
    "EngineeringServices": _flag(),
}

EXPECTED_COLUMNS: tuple[str, ...] = tuple(_COLUMNS)

# The rename contract (4.2): explicit per-column because concatenated-capital
# headers are not algorithmically derivable (HUBCertStartDate, NCeProcurement).
SNAKE_CASE: dict[str, str] = {
    "Name": "name",
    "MainContactName": "main_contact_name",
    "MainContactEmail": "main_contact_email",
    "MainContactPhone": "main_contact_phone",
    "AddressLine1": "address_line_1",
    "City": "city",
    "State": "state",
    "ZipCode": "zip_code",
    "County": "county",
    "Country": "country",
    "URL": "url",
    "EvpStatus": "evp_status",
    "NCeProcurement": "nc_eprocurement",
    "HUB": "hub",
    "HUBCategory": "hub_category",
    "HUBCertStartDate": "hub_cert_start_date",
    "HUBCertEndDate": "hub_cert_end_date",
    "NCSBE": "ncsbe",
    "NCSBECertStartDate": "ncsbe_cert_start_date",
    "NCSBECertEndDate": "ncsbe_cert_end_date",
    "SmallBusiness": "small_business",
    "DBE": "dbe",
    "NPWC": "npwc",
    "GeneralContractor": "general_contractor",
    "GeneralContractorLimitation": "general_contractor_limitation",
    "GeneralContractorWorkClassification": "general_contractor_work_classification",
    "GeneralContractorLicenseNumber": "general_contractor_license_number",
    "ElectricalContractor": "electrical_contractor",
    "ElectricalLicenseSpecialties": "electrical_license_specialties",
    "ElectricalLicenseLevel": "electrical_license_level",
    "ElectricalLicenseNumber": "electrical_license_number",
    "PlumbingFireSprinklerContractor": "plumbing_fire_sprinkler_contractor",
    "PlumbingFireSprinklerLicenseClassifications": "plumbing_fire_sprinkler_license_classifications",  # noqa: E501
    "PlumbingFireSprinklerLicenseNumber": "plumbing_fire_sprinkler_license_number",
    "MechanicalHeating": "mechanical_heating",
    "MechanicalHeatingLicenseClassifications": "mechanical_heating_license_classifications",  # noqa: E501
    "MechanicalHeatingLicenseNumber": "mechanical_heating_license_number",
    "TradesSubContractor": "trades_sub_contractor",
    "TradesSubContractorLicenseNumber": "trades_sub_contractor_license_number",
    "ArchitecturalServices": "architectural_services",
    "EngineeringServices": "engineering_services",
}

RED_COLUMNS = ("MainContactName", "MainContactEmail", "MainContactPhone")

VENDOR_CONFIG = TableConfig(
    name="evp-vendor-master",
    columns=_COLUMNS,
    dedup_key=("Name", "GeneralContractorLicenseNumber"),
    red_columns=RED_COLUMNS,
)
