# Data Cleaning Protocol — PWC Vendor & Licensing Data

The repeatable standardization protocol applied to the PWC vendor and licensing datasets.
Controlled vocabularies and terminology live in
[master-data-documentation.md](master-data-documentation.md); the column-level schema is in
[`../data/DATA_DICTIONARY.md`](../data/DATA_DICTIONARY.md). The general rules are implemented in
[`../src/cleaning/clean_data.py`](../src/cleaning/clean_data.py).

## General rules (both tables)

1. Trim leading/trailing whitespace from every text field.
2. Lowercase all email addresses; require a single `@`.
3. Format phone numbers as `###-###-####`.
4. Business names: hybrid capitalization (Title Case, preserving acronyms) with standardized
   legal suffixes (LLC, Inc., Co., Corp., Ltd.).
5. Dates: `MM/DD/YYYY`.
6. Store license numbers and ZIP codes as **text** — never coerce to numeric (preserves leading zeros).
7. Keep the vendor table and the licensing table **separate** (joined only on `License_Number`).
8. Document every correction; apply no imputation (missing stays missing).

## Vendor table — cleaning sequence

1. Trim whitespace.
2. Lowercase emails.
3. Regex-format phones (`###-###-####`).
4. Normalize `Vendor_Name` (hybrid case + legal-suffix standardization).
5. Proper-case the address fields.
6. Validate HUB to the controlled vocabulary (Certified / Not Certified / Unknown).
7. Keep license-number fields as text.
8. De-duplicate on `Vendor_Name` + `License_Number`.

## Licensing table — cleaning sequence

1. Trim whitespace.
2. Enforce `MM/DD/YYYY` for `Issue_Date` and `Expiration_Date`.
3. Format phones.
4. Normalize `Company_Name` (hybrid case + legal suffixes).
5. Standardize the `Classifications` delimiter to a semicolon (`;`).
6. Validate `Status` and `License_Limitation` against their controlled vocabularies.
7. De-duplicate on `License_Number`.

## Cross-validation

- Every vendor `License_Number` must exist in the licensing table.
- Subcontractor license formats must match their classification types.
- HUB-certified vendors must hold appropriate licenses for their listed trades.

## File naming & versioning

- `vendor-details-evp-nc-v##.xlsx`, `nclbgc-license-details-v##.xlsx`.
- Increment the version suffix on every update; never overwrite a prior version in place.
