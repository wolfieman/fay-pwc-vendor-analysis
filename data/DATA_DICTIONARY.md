# Data Dictionary

Schema reference for the two source datasets used in this project. **The raw data files
are not included in this repository** — they contain real vendor/contact information and
are gitignored (`data/raw/`). An **anonymized version** (the five PII columns removed, plus stray
emails scrubbed) is published in [`sample/`](sample/) so reviewers can reproduce the analysis.

- **Provenance:** vendor records from the NC electronic Vendor Portal (eVP, `evp.nc.gov`);
  license details scraped from the NC Licensing Board for General Contractors
  (NCLBGC, `nclbgc.org`) via the scripts in `src/acquisition/`.
- **Scale:** 295 vendor rows × 44 columns; 295 license rows × 12 columns.
- **Conventions:** license numbers and ZIP codes stored as **text** (leading zeros
  preserved); dates `MM/DD/YYYY`; phones `###-###-####`; emails lowercased. See
  `docs/data-cleaning-protocol` for the full standardization protocol.

**Sensitivity legend:** 🔴 PII (excluded from any public/anonymized release) ·
🟡 business identifier · ⚪ non-sensitive.

---

## `vendor-details-evp-nc.xlsx` — vendor master (44 columns)

| # | Column | Type | Description | Sensitivity |
|---|---|---|---|---|
| 1 | Vendor_Name | text | Legal business name (hybrid case, standardized legal suffix) | 🟡 |
| 2 | License_Number | text | Primary NCLBGC contractor license number | 🟡 |
| 3 | Contact_Name | text | Vendor contact person | 🔴 |
| 4 | Contact_Email | text | Contact email (lowercased) | 🔴 |
| 5 | Contact_Phone | text | Contact phone (`###-###-####`) | 🔴 |
| 6 | Address | text | Street address | 🟡 |
| 7 | City | text | City | ⚪ |
| 8 | State | text | State | ⚪ |
| 9 | ZipCode | text | ZIP code (text; leading zeros preserved) | ⚪ |
| 10 | County | text | County | ⚪ |
| 11 | Country | text | Country | ⚪ |
| 12 | URL | text | Company website | 🟡 |
| 13 | Evp_Status | category | NC electronic Vendor Portal status | ⚪ |
| 14 | NC_eProcurement | category | NC eProcurement status (Active / Inactive / Not Applicable) | ⚪ |
| 15 | HUB | category | HUB status (Certified / Not Certified; blank = unevaluated) | ⚪ |
| 16 | HUB_Category | category | HUB demographic category (e.g., Female, Black, Hispanic) | ⚪ |
| 17 | HUB_Cert_Start_Date | date | HUB certification start (`MM/DD/YYYY`) | ⚪ |
| 18 | HUB_Cert_End_Date | date | HUB certification end | ⚪ |
| 19 | HUB_Active | bool | HUB certification currently active | ⚪ |
| 20 | PWC_Active | bool | Active vendor relationship with PWC | ⚪ |
| 21 | NCSBE | category | NCSBE status (Certified / Not Certified; blank = unevaluated) | ⚪ |
| 22 | NCSBE_Cert_Start_Date | date | NCSBE certification start | ⚪ |
| 23 | NCSBE_Cert_End_Date | date | NCSBE certification end | ⚪ |
| 24 | Small_Business | bool | Small-business flag | ⚪ |
| 25 | DBE | bool | Disadvantaged Business Enterprise flag | ⚪ |
| 26 | NPWC | category | Internal PWC vendor classification | ⚪ |
| 27 | General_Contractor | bool | Holds a general-contractor license | ⚪ |
| 28 | General_Contractor_Limitation | category | GC limitation (Unlimited / Limited / Intermediate / None) | ⚪ |
| 29 | General_Contractor_Work_Classification | text | GC work classifications | ⚪ |
| 30 | General_Contractor_License_Number | text | GC license number | 🟡 |
| 31 | Electrical_Contractor | bool | Holds an electrical license | ⚪ |
| 32 | Electrical_License_Specialties | text | Electrical specialties | ⚪ |
| 33 | Electrical_License_Level | category | Electrical level (Unlimited/Limited/Intermediate) | ⚪ |
| 34 | Electrical_License_Number | text | Electrical license number | 🟡 |
| 35 | Plumbing_Fire_Sprinkler_Contractor | bool | Holds a plumbing/fire-sprinkler license | ⚪ |
| 36 | Plumbing_Fire_Sprinkler_License_Classifications | text | P/FS classifications | ⚪ |
| 37 | Plumbing_Fire_Sprinkler_LicenseNumber | text | P/FS license number | 🟡 |
| 38 | Mechanical_Heating | bool | Holds a mechanical/heating license | ⚪ |
| 39 | Mechanical_Heating_License_Classifications | text | Mechanical/heating classifications | ⚪ |
| 40 | Mechanical_Heating_License_Number | text | Mechanical/heating license number | 🟡 |
| 41 | Trades_Sub-Contractor | bool | Trades subcontractor flag | ⚪ |
| 42 | Trades_Sub_Contractor_License_Number | text | Trades subcontractor license number | 🟡 |
| 43 | Architectural_Services | bool | Offers architectural services (Yes/No) | ⚪ |
| 44 | Engineering_Services | bool | Offers engineering services (Yes/No) | ⚪ |

## `nclbgc-license-details.xlsx` — license details (12 columns)

| # | Column | Type | Description | Sensitivity |
|---|---|---|---|---|
| 1 | License_Number | text | NCLBGC license number (primary key) | 🟡 |
| 2 | Company_Name | text | Licensed company (hybrid case, standardized suffix) | 🟡 |
| 3 | Address | text | Business address | 🟡 |
| 4 | Phone | text | Business phone (`###-###-####`) | 🔴 |
| 5 | Issue_Date | date | License issue date (`MM/DD/YYYY`) | ⚪ |
| 6 | Expiration_Date | date | License expiration date | ⚪ |
| 7 | Status | category | Active / Expired / Suspended / Revoked / Inactive / Pending | ⚪ |
| 8 | License_Limitation | category | Limited / Intermediate / Unlimited | ⚪ |
| 9 | Classifications | text | Semicolon-delimited (e.g., `Building; Highway; PU(Water Lines & Sewer Lines)`) | ⚪ |
| 10 | Qualifier_Number | text | Qualifier (licensed individual) identifier | 🟡 |
| 11 | Qualifier_Name | text | Name of the licensed qualifier (an individual) | 🔴 |
| 12 | Qualifier_Status | category | Qualifier status (Active / Inactive) | ⚪ |

---

### Handling of sensitive columns
The 🔴 columns (`Contact_Name`, `Contact_Email`, `Contact_Phone`, `Phone`, `Qualifier_Name`)
identify individuals and are **never committed**. The published [`sample/`](sample/) datasets
have these five columns removed (and stray emails scrubbed from free-text fields); business-identifying
🟡 fields and all ⚪ fields are retained, so the analysis fully reproduces from the sample.
