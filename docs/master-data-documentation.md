# Master Data Documentation

Reference standards, controlled vocabularies, and terminology for the PWC vendor & licensing
datasets. The cleaning steps that enforce these standards are in
[data-cleaning-protocol.md](data-cleaning-protocol.md); the per-column schema is in
[`../data/DATA_DICTIONARY.md`](../data/DATA_DICTIONARY.md).

## Tables

| Table | Source | Grain | Key |
|---|---|---|---|
| Vendor master | NC electronic Vendor Portal (eVP) | one row per vendor | `Vendor_Name` + `License_Number` |
| License details | NC Licensing Board for General Contractors (NCLBGC) | one row per license | `License_Number` |

The tables are maintained separately and joined on `License_Number`.

## Controlled vocabularies

- **HUB status:** Certified · Not Certified · Unknown
- **License status:** Active · Expired · Suspended · Revoked · Inactive · Pending
- **License limitation:** Unlimited · Limited · Intermediate
- **Classifications:** semicolon-delimited (e.g., `Building; Highway; PU(Water Lines & Sewer Lines)`)

## Field conventions

- License numbers & ZIP codes: text (leading zeros preserved).
- Dates: `MM/DD/YYYY` · Phones: `###-###-####` · Emails: lowercase.
- Business names: hybrid case with standardized legal suffixes.

## Glossary

- **PWC** — Fayetteville Public Works Commission, a municipal power & water utility (the client).
- **HUB** — Historically Underutilized Business; certification for businesses owned by
  underrepresented groups, used in public-sector economic-inclusion programs.
- **MBE / WBE** — Minority / Women Business Enterprise (subsets of HUB designations).
- **eVP** — NC electronic Vendor Portal (`evp.nc.gov`), the state vendor registration system.
- **NCLBGC** — NC Licensing Board for General Contractors (`nclbgc.org`), the contractor-license authority.
- **NCSBE** — NC Small Business Enterprise certification.
- **DBE** — Disadvantaged Business Enterprise (federal designation).
- **Qualifier** — the licensed individual responsible for work performed under a contractor's license.
- **License limitation** — the scope tier of a contractor license: Unlimited, Limited, or Intermediate.
- **PU** — Public Utilities classification (e.g., water and sewer lines).
