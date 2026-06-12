# Findings Summary

Detailed results of the vendor availability & licensing analysis for the Fayetteville Public
Works Commission (PWC), across **295 vendors**. All figures below are computed directly from
the source data. The Part-1 data dictionary was retired with the original pipeline
(it lives in git history); for how the data was produced see [`methodology.md`](methodology.md).

## HUB certification — the headline gap

| HUB status | Vendors | Share |
|---|--:|--:|
| Certified | 80 | 27.1% |
| Not certified | 22 | 7.5% |
| **Missing** | **193** | **65.4%** |

Nearly two-thirds of vendor records have **no HUB status at all** — the most significant
data-quality gap, and the main constraint on any economic-inclusion analysis.

**HUB category** (the 80 certified vendors; `HUB_Category` is missing for the other 215):

| Category | Vendors |
|---|--:|
| Female | 43 |
| Black | 23 |
| American Indian | 6 |
| Hispanic | 5 |
| Disabled | 2 |
| Asian American | 1 |

## Licensing posture

**License limitation** (all 295 records):

| Limitation | Vendors | Share |
|---|--:|--:|
| Unlimited | 206 | 69.8% |
| Limited | 82 | 27.8% |
| Intermediate | 7 | 2.4% |

**License status:** 263 active (89.2%), 23 invalid (7.8%), 9 archived (3.1%).

**Electrical license level** (the 18 vendors holding an electrical license; 277 hold none):
Unlimited 11 · Limited 6 · Intermediate 1.

## Geography

| Top cities | Vendors | | Top counties | Vendors |
|---|--:|---|---|--:|
| Charlotte | 25 | | Wake | 35 |
| Raleigh | 22 | | Mecklenburg | 27 |
| Greensboro | 10 | | Guilford | 11 |
| Wilmington | 8 | | New Hanover / Johnston | 8 each |

Vendors are predominantly North Carolina (240 of 295), with smaller numbers in South Carolina (13),
Tennessee (5), and Florida (4). **County is missing for 55 vendors (18.6%)** and city for 9 — a
secondary geographic data gap.

## Data-quality gaps (ranked)

| Field | Missing | Share |
|---|--:|--:|
| HUB_Category | 215 | 72.9% |
| HUB status | 193 | 65.4% |
| County | 55 | 18.6% |
| City | 9 | 3.1% |

## Recommendations

1. **Contact the 22 non-HUB-certified vendors** — a small, concrete list for economic-inclusion outreach.
2. **Close the HUB-status gap** (193 missing) by capturing certification at vendor intake.
3. **Backfill geography** (county especially) to enable regional supplier planning.
4. **Adopt the cleaning protocol** ([`../docs/`](../docs/)) as the standing vendor-onboarding data standard.
