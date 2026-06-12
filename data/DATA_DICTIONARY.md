# Data Dictionary

> **DRAFT pending the slice-1 owner checkpoint** (plan section 8.2, phase 3).
> Finalized as a slice-1 gate artifact; a unit test asserts this document agrees
> with the executable column manifest and vocabulary config.

**Last updated:** 2026-06-12

## Provenance

- **Source:** NC electronic Vendor Portal (eVP, `evp.nc.gov`), the saved-search
  results page (record id `20199579-3165-f111-a824-001dd812e0a9`, page 1), whose
  embedded dataset is decoded verbatim (entity unescape + JSON parse). The record
  id is public by the portal's design; drift detection, not secrecy, is the defense.
- **Filters (client parity):** status Active (code `1`), classification Public
  Utilities (code `790550003`), HUB certification deliberately blank so certified,
  not-certified, and unevaluated vendors all return.
- **Profiled pull:** run `20260612T144403-evp`, 570 records × 41 fields, uniform
  keyset. Raw bytes, decoded JSON, and checksums frozen under `data/raw/evp/`
  (gitignored).
- **Vocabulary provenance tags:** `observed` = present in the profiled pull;
  `prior-vintage` = observed in the previous verified pull but absent now;
  `portal` = documented portal knowledge not observable under the locked filter.

## Conventions

Identifiers and ZIP codes are text (leading zeros preserved); dates are
`MM/DD/YYYY` text; phones `###-###-####`; emails lowercased; blank means
missing/unevaluated and is never imputed; trade flags arrive as JSON booleans and
land as canonical `Yes`/`No`. Raw artifacts keep the source's field names; the
processed deliverable uses the snake_case targets below (the rename contract is
this table, applied once at processed-write with a uniqueness assertion).

## Keys

- **Row identity (per run):** `row_key`, the record's zero-padded ordinal in the
  decoded raw extract; joins the deliverable/contacts file pair; keys all audit
  records.
- **Dedup key (cross-run identity):** `Name` + `GeneralContractorLicenseNumber`
  (one exact duplicate pair observed in the profiled pull).
- **NCLBGC join key (slice 2):** `GeneralContractorLicenseNumber`.

## Columns (41)

Sensitivity: red = identifies an individual (never tracked, split to the contacts
sibling); yellow = business identifier; white = non-sensitive.

| # | Source field | snake_case target | Type | Sensitivity | Notes / observed vocabulary |
|---|---|---|---|---|---|
| 1 | Name | name | text | yellow | legal business name; dedup key part |
| 2 | MainContactName | main_contact_name | text | red | contacts file only |
| 3 | MainContactEmail | main_contact_email | text | red | contacts file only |
| 4 | MainContactPhone | main_contact_phone | text | red | contacts file only; 8 blank |
| 5 | AddressLine1 | address_line_1 | text | yellow | street address |
| 6 | City | city | text | white | |
| 7 | State | state | text | white | |
| 8 | ZipCode | zip_code | text | white | observed lengths: 5 (547), 10 (22, ZIP+4), 7 (1, quirk to flag) |
| 9 | County | county | text | white | a county literally named "NA" is data |
| 10 | Country | country | text | white | |
| 11 | URL | url | text | yellow | |
| 12 | EvpStatus | evp_status | category | white | observed: Active (570, locked filter); portal: Pending, Debarred |
| 13 | NCeProcurement | nc_eprocurement | category | white | observed: Active (241), Inactive (214), Not Applicable (115) |
| 14 | HUB | hub | category | white | observed: blank (378), Certified (135), Not Certified (57); blank = unevaluated |
| 15 | HUBCategory | hub_category | category | white | observed: blank (427), Black (67), Female (56), Hispanic (9), American Indian (8), Disabled (3); prior-vintage: Asian American, Socially and Economically Disadvantaged |
| 16 | HUBCertStartDate | hub_cert_start_date | date | white | MM/DD/YYYY text |
| 17 | HUBCertEndDate | hub_cert_end_date | date | white | MM/DD/YYYY text |
| 18 | NCSBE | ncsbe | category | white | NC Small Business Enterprise; observed: blank (513), Not Certified (32), Certified (25) |
| 19 | NCSBECertStartDate | ncsbe_cert_start_date | date | white | |
| 20 | NCSBECertEndDate | ncsbe_cert_end_date | date | white | |
| 21 | SmallBusiness | small_business | flag | white | observed: False (570); degenerate in this vintage |
| 22 | DBE | dbe | flag | white | observed: False (570); degenerate in this vintage |
| 23 | NPWC | npwc | flag | white | observed: False (570); degenerate in this vintage |
| 24 | GeneralContractor | general_contractor | flag | white | observed: True (563), False (7) |
| 25 | GeneralContractorLimitation | general_contractor_limitation | category | white | observed: Unlimited (264), None (152, literal member), Limited (126), Intermediate (21), blank (7) |
| 26 | GeneralContractorWorkClassification | general_contractor_work_classification | text | white | free text |
| 27 | GeneralContractorLicenseNumber | general_contractor_license_number | text | yellow | observed classes: digits (379), blank (157), other (34: out-of-state, prefixed, multi-value; violations, never coerced) |
| 28 | ElectricalContractor | electrical_contractor | flag | white | observed: False (477), True (93) |
| 29 | ElectricalLicenseSpecialties | electrical_license_specialties | text | white | free text |
| 30 | ElectricalLicenseLevel | electrical_license_level | category | white | observed: blank (471), None (69, literal member, NEW finding this pull), Unlimited (20), Limited (8), Intermediate (2) |
| 31 | ElectricalLicenseNumber | electrical_license_number | text | yellow | |
| 32 | PlumbingFireSprinklerContractor | plumbing_fire_sprinkler_contractor | flag | white | observed: False (520), True (50) |
| 33 | PlumbingFireSprinklerLicenseClassifications | plumbing_fire_sprinkler_license_classifications | text | white | free text |
| 34 | PlumbingFireSprinklerLicenseNumber | plumbing_fire_sprinkler_license_number | text | yellow | |
| 35 | MechanicalHeating | mechanical_heating | flag | white | observed: False (531), True (39) |
| 36 | MechanicalHeatingLicenseClassifications | mechanical_heating_license_classifications | text | white | free text |
| 37 | MechanicalHeatingLicenseNumber | mechanical_heating_license_number | text | yellow | |
| 38 | TradesSubContractor | trades_sub_contractor | flag | white | observed: False (344), True (226) |
| 39 | TradesSubContractorLicenseNumber | trades_sub_contractor_license_number | text | yellow | |
| 40 | ArchitecturalServices | architectural_services | flag | white | observed: False (479), True (91) |
| 41 | EngineeringServices | engineering_services | flag | white | observed: False (453), True (117) |

## Red set (this source)

`MainContactName`, `MainContactEmail`, `MainContactPhone`. Values never appear in
any tracked artifact, fixture, or board text; the columns live only in the
gitignored contacts sibling file, keyed by `row_key`.
