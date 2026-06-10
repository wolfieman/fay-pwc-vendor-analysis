# VendorScope

**Vendor readiness & availability analytics.** VendorScope turns fragmented public vendor and licensing data into an audited, decision-ready view of who is registered, licensed, available, and ready for public-sector procurement, built on a documented and reusable data-quality pipeline.

[![CI](https://github.com/wolfieman/vendorscope/actions/workflows/ci.yml/badge.svg)](https://github.com/wolfieman/vendorscope/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/env-uv-261230?logo=astral&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-3.0-150458?logo=pandas&logoColor=white)
![License](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-orange)

---

## TL;DR: flagship case study (Fayetteville PWC)

VendorScope's first real-world application. The **Fayetteville Public Works Commission (PWC)**, a municipal power & water utility, needed
to understand its contractor/vendor base for supply-chain planning and economic-inclusion goals,
but the vendor data was incomplete and unverified. I assembled the data from two public sources,
built a documented cleaning-and-audit pipeline, and produced descriptive analytics across **295 vendors**.

**Headline results:**
- **65.4%** of vendors (193 of 295) had **missing HUB (Historically Underutilized Business) status**, the single biggest data-quality gap.
- Of vendors with known status, **80 are HUB-certified** and **22 are explicitly not certified**.
- **Recommendation:** prioritize outreach to the **22 non-HUB-certified vendors** for economic-inclusion conversations, and close the HUB-status gap at vendor intake.

![From Data to Decisions: PWC's Vendor Readiness Analysis](assets/pwc-infographic.png)

▶️ **[Watch the video overview](assets/unlocking-opportunity.mp4)** (≈3 min).

---

## Business context

PWC works with hundreds of contractors but lacked a single, trustworthy view of *who* its vendors
are, *what they're licensed to do*, and *which qualify for economic-inclusion programs*. The source
records were spread across systems, inconsistently formatted, and full of gaps, which made any
downstream analytics unreliable. The goal: a clean, auditable vendor source-of-truth plus a
**reusable data-quality protocol** that PWC could keep applying.

## Data

Two public sources, **295 records each**. The raw files contain contact PII and are **not committed**;
an **anonymized version** (PII columns removed) ships in [`data/sample/`](data/sample/), with the full
schema in [`data/DATA_DICTIONARY.md`](data/DATA_DICTIONARY.md):

| Dataset | Source | Shape | Contents |
|---|---|---|---|
| Vendor master | NC electronic Vendor Portal (eVP, `evp.nc.gov`) | 295 × 44 | vendor identity, HUB/cert status, per-trade licenses |
| License details | NC Licensing Board for General Contractors (NCLBGC, `nclbgc.org`) | 295 × 12 | license status, limitation, classifications, qualifier |

## Methodology

```
Acquisition  →  Cleaning  →  Profiling  →  Audit  →  Descriptive analytics
(Selenium /     (protocol     (per-column   (missingness   (HUB, licensing,
 Playwright)     standardize)   stats)        report)        geography)
```

1. **Acquisition** (`src/acquisition/`): scraped NCLBGC license details (Selenium) and resolved
   license numbers by company name (Playwright), merged with the eVP vendor/HUB export.
2. **Cleaning** (`src/cleaning/clean_data.py`) applied a documented protocol: trim whitespace,
   lowercase emails, format phones `###-###-####`, hybrid-case business names with standardized
   legal suffixes, dates `MM/DD/YYYY`, license numbers and ZIPs stored as **text** (leading zeros
   preserved), de-duplication on `Vendor_Name + License_Number`, and cross-validation of every
   vendor license against the NCLBGC source.
3. **Profiling** (`src/cleaning/profile_data.py`): per-column counts, missingness, and basic stats.
4. **Audit** (`src/cleaning/make_audit.py`): a Markdown data-quality report ranking columns by missingness.
5. **Analytics**: descriptive analysis (HUB distribution, license levels, geography) delivered as
   an infographic and a video overview.

## Key findings (verified against the data)

**HUB certification: a major data gap**

| HUB status | Vendors | Share |
|---|--:|--:|
| Certified | 80 | 27.1% |
| Not certified | 22 | 7.5% |
| **Missing** | **193** | **65.4%** |

Among HUB-certified vendors, the largest categories were Female-owned (43) and Black-owned (23);
`HUB_Category` was itself missing for 215 vendors (72.9%), limiting demographic analysis.

**Licensing posture (all 295 license records)**

| License limitation | Vendors | | Electrical level\* | Vendors |
|---|--:|---|---|--:|
| Unlimited | 206 (69.8%) | | Unlimited | 11 |
| Limited | 82 (27.8%) | | Limited | 6 |
| Intermediate | 7 (2.4%) | | Intermediate | 1 |

License status: **263 active**, 23 invalid, 9 archived. *\*Among the 18 vendors holding an electrical license.*

📄 Full breakdown in [`reports/findings-summary.md`](reports/findings-summary.md); pipeline details in [`reports/methodology.md`](reports/methodology.md).

## Recommendation

1. **Contact the 22 non-HUB-certified vendors**, a small, actionable list for economic-inclusion outreach.
2. **Close the HUB-status gap** (193 missing) by capturing certification at vendor intake.
3. **Adopt the cleaning protocol** as the standing data-quality standard for vendor onboarding.

## Repository structure

```
.
├─ src/
│  ├─ acquisition/      # NCLBGC scrapers (Selenium, Playwright)
│  └─ cleaning/         # clean · merge · profile · audit
├─ data/
│  ├─ DATA_DICTIONARY.md   # full schema (PII flagged)
│  ├─ sample/              # anonymized data (PII removed); runs out of the box
│  ├─ raw/                 # real source files (gitignored, PII)
│  └─ processed/           # pipeline outputs (gitignored)
├─ reports/             # written analysis
├─ assets/              # infographic + video overview (video via Git LFS)
├─ docs/                # data-cleaning protocol + master-data documentation
├─ pyproject.toml       # dependencies (uv project)
└─ uv.lock              # pinned, reproducible environment
```

## Reproduce

The repo ships an anonymized sample in `data/sample/` (PII removed), so the pipeline runs out of the box. One command runs the full clean, profile, and audit chain (no scraping):

```bash
uv sync                                          # create env from uv.lock
uv run python -m vendorscope.pipeline reproduce  # clean, profile, audit over data/sample
```

Or run each stage directly:

```bash
uv run python src/cleaning/clean_data.py --input data/sample/vendor-details-evp-nc.csv
uv run python src/cleaning/profile_data.py --files data/sample/vendor-details-evp-nc.csv data/sample/nclbgc-license-details.csv
uv run python src/cleaning/make_audit.py         # writes data/processed/data_audit.md
```

## Tech stack

**Python 3.11+** · pandas · openpyxl · tqdm · Selenium + Playwright + webdriver-manager (acquisition)
· SAS Viya + Excel (analytics) · **uv** (environment & locking).

## License & contact

Source-available under the **PolyForm Noncommercial License 1.0.0** (see [`LICENSE`](LICENSE)),
free to view, study, and share for non-commercial purposes.

**Wolfgang Sanyer** · [wolfgang.sanyer@gmail.com](mailto:wolfgang.sanyer@gmail.com)
