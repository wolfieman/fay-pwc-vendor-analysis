# Methodology

How the vendor dataset was assembled, cleaned, audited, and analyzed. This is the detailed
companion to the overview in the [project README](../README.md).

```
Acquisition  →  Cleaning  →  Profiling  →  Audit  →  Descriptive analytics
```

## 1. Acquisition (`src/acquisition/`)

- **License-number resolution** (`nclbgc_licenses_acquisition.py`, Playwright): for each vendor
  company name, query the NCLBGC portal and fill in the contractor license account number
  (`L.xxxxx`, `PENDING`, or `NA`), with normalized-name retries.
- **License-detail scraping** (`nclbgc_license_details_acquisition.py`, Selenium): for each
  license number, pull status, issue/expiration dates, limitation, classifications, and
  qualifier (split into separate columns).
- **Vendor/HUB attributes** come from the NC electronic Vendor Portal (eVP) export.

Result: a vendor master (295 × 44) and a license-details table (295 × 12).

## 2. Cleaning (`src/cleaning/clean_data.py`)

A documented, repeatable standardization protocol (see [`../docs/`](../docs/)):

- Trim whitespace; standardize headers to `snake_case`.
- Lowercase emails; format phones as `###-###-####`.
- Hybrid-case business names; standardize legal suffixes (LLC, Inc., Co., Corp., Ltd.).
- Dates as `MM/DD/YYYY`.
- Store **license numbers and ZIP codes as text** (leading zeros preserved — no numeric coercion).
- Normalize HUB to a controlled vocabulary (Certified / Not Certified / Unknown).
- De-duplicate: vendors on `Vendor_Name + License_Number`; licenses on `License_Number`.
- Add `*_is_missing` / `*_is_zero` flags on numeric columns (no imputation).

## 3. Cross-validation

Every vendor `License_Number` is checked against the NCLBGC license table; HUB-certified vendors
are confirmed to hold appropriate licenses for their listed trades. This catches typos, stale
numbers, and mismatched classifications before analysis.

## 4. Profiling (`src/cleaning/profile_data.py`)

Per-column counts, missingness, zero counts, and basic numeric stats for every file, written as
per-file and combined summary CSVs plus a metadata JSON.

## 5. Audit (`src/cleaning/make_audit.py`)

Consumes the profile summary and emits a Markdown data-quality report: average missingness per
file and the most-incomplete columns, with observations and next actions.

## 6. Descriptive analytics

HUB distribution, license levels/limitations, and geographic concentration were analyzed and
delivered as an infographic and a video overview. See [`findings-summary.md`](findings-summary.md)
for the numbers.

## Tooling

Python 3.11+ (pandas, openpyxl, tqdm); Selenium + Playwright + webdriver-manager for acquisition;
SAS Viya and Excel for descriptive analytics; **uv** for environment management and locking.
