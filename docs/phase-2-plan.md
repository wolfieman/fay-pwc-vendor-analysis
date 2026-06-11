# Phase 2 — Data Refresh & Database

VendorScope ships in a 3-part arc: **P1** standards/refactor (done, merged), **P2**
data refresh + own database (this document), **P3** app + website + AI features.
Phase 2 turns the project from a one-shot flat-file pipeline into a maintained data
product. Everything here is **additive** — it builds on top of the existing cleaning
pipeline and its outputs; nothing is torn out.

## Locked decisions

- **Database = SQLite + `sqlite-vec`.** One file holds the normalized relational
  tables *and* the embedding vectors. Clone-and-run, no service to host. Use
  `STRICT` tables and `PRAGMA foreign_keys = ON` for real constraint enforcement;
  pin `sqlite-vec` (it is pre-1.0). Keep embedding logic isolated and lean on
  standard SQL so a later SQLite -> Postgres port stays a swap, not a rewrite.
- **AI data layer (embeddings + vector search) is in scope for P2.** Embedding model
  chosen at P2.3 against the current model/pricing reference (not assumed up front).
- **Multi-source generalization (P2.5) is deferred** — no new source is expected.
  Honor the rule of three; do not pre-generalize the cleaning code.
- **Dataset scope stays at PWC's filters for now** (see Acquisition). Build the
  machinery to reproduce today's dataset first; broadening scope is a separate,
  deliberate decision made *after* the pipeline is proven.

## Acquisition architecture (two-stage, API-first)

Data comes from **two live public sources**; Fayetteville PWC is the *client* /
flagship case study, **not** a source.

**Stage 1 — eVP vendor list** (NC electronic Vendor Portal, `evp.nc.gov`).
*No code today — must be built.* Currently a manual advanced-search + Excel export.
Reproduce these filters first (PWC's set):

- `eVP Status = Active`
- `Work/License Classifications = Public Utilities`
- `HUB Certification Status = (blank)` — left unselected on purpose so both certified
  and not-certified vendors return; this is what powers the HUB-gap analysis, so it
  **stays open**.

This filter returned 395 records (~Sept) and ~570 now (live growth). The export is
the 44-column vendor master, including each vendor's license number.

**Stage 2 — NCLBGC license enrichment** (NC Licensing Board for General Contractors,
`nclbgc.org`). *Already scripted* (`src/acquisition/`). Feed each license number from
Stage 1 into the board search, which returns one license at a time; iterate over all
valid licenses to pull the 12-column details.

**API-first — probed and confirmed (2026-06-10):**

- **NCLBGC = full HTTP API, no browser, no token.** `POST https://portal.nclbgc.org/Public/_Search/`
  (`application/x-www-form-urlencoded`, `x-requested-with: XMLHttpRequest`, no anti-forgery
  token) takes named form fields (`CompanyName`, `AccountNumber`, `ClassificationDefinitionIdnt`,
  …) and returns the results **table HTML**. Each row carries an opaque `key`; detail/qualifiers
  via `GET /Public/_ShowAccountDetails/?key=<k>&Source=Search`, `/_ShowAccountQualifiers/?key=<k>`.
  ⇒ Replace Playwright/Selenium with **`httpx` + HTML-fragment parsing** (keep one session cookie).
- **eVP = JSON API, token-bound + tamper-proofed ⇒ API-assisted headless browser.** Rows come
  from `POST https://evp.nc.gov/_services/entity-subgrid-data.json/<gridId>` → `application/json`,
  requiring an `__RequestVerificationToken` header and an opaque, server-signed
  `base64SecureConfiguration` body (the filter is encrypted into it; the advanced search is an
  ASP.NET WebForms `__VIEWSTATE` postback). ⇒ Drive the filtered results page in **headless
  Playwright and harvest the `entity-subgrid-data.json` JSON responses while paging** — capture
  the JSON, don't reverse the blob. Pinned container is needed for eVP only.

Net: NCLBGC drops the browser entirely; eVP stays browser-driven but yields clean JSON.

## Database schema (normalized, ~3NF)

Grounded in `data/DATA_DICTIONARY.md` + `docs/data-cleaning-protocol.md`. The
normalization: (1) collapse eVP's repeating per-trade column blocks into a
`vendor_trade` table; (2) resolve the semicolon-delimited `Classifications` into a
`classification` lookup + `license_classification` bridge; (3) split the five PII
columns into sibling `*_pii` tables so the public/`sample/` export simply omits them;
(4) add `source` + `acquisition_run` for provenance and run-over-run diffing.

Tables:

- `source` — the two sources (eVP, NCLBGC).
- `acquisition_run` — one row per scrape/refresh (enables diffing; carries the `v##` tag).
- `license` — NCLBGC license details (PK `license_number`, text); `license_pii(phone)`.
- `qualifier` — licensed individual (PK `qualifier_number`); `qualifier_pii(qualifier_name)`.
- `classification` + `license_classification` — many-to-many classifications.
- `vendor` — eVP business fields (PK `vendor_id`; `UNIQUE(vendor_name, license_number)`
  = the documented dedup key; FK `license_number`); `vendor_pii(contact_name/email/phone)`.
- `vendor_trade` — one row per held trade (kills the repeating GC/Electrical/Plumbing-
  Fire-Sprinkler/Mechanical-Heating/Trades-Sub blocks).
- `vendor_certification` — HUB + NCSBE (status/category/start/end/active).
- `vendor_embedding` — `vec0` virtual table (`sqlite-vec`), embedding dim set at P2.3.

Controlled vocabularies (HUB status, license status, license limitation) enforced via
`CHECK` constraints under `STRICT`. The existing `merge_vendors` HUB/master/PWC
presence-flag SSOT becomes a view over `vendor`, not a parallel model.

## Sub-passes & gates

Run as sequenced sub-passes with a go/no-go gate between each (not one mega-PR).

- **P2.0 — Gate & decisions.** Confirm eVP + NCLBGC terms/rate limits permit recurring
  automated access. Probe both sites for APIs (API-first). Lock the PII/mosaic design
  stance (which fields the DB exposes vs. the eventual P3 public index).
  *Gate: terms confirmed + acquisition approach (API vs browser) chosen per source.*
- **P2.1 — Scraper hardening + offline parsing tests (test-first).** Build the NCLBGC
  `httpx` client + pure HTML-fragment parsers; build Stage-1 eVP acquisition (headless JSON
  harvest) to reproduce PWC's filters. Pure parsers are covered by **offline contract tests over
  saved fixtures** (HTML for NCLBGC, JSON for eVP) that run deterministically in default CI.
  Live validation is **opt-in integration tests** — extend `tests/test_scrapers_integration.py`
  (`@pytest.mark.integration`, gated by `TEST_MODE`; skipped by default, run with
  `TEST_MODE=false uv run pytest -m integration`), the documented pattern already established for
  the Part-1 canary. (The one-off `scripts/probe_endpoints.py` used for endpoint discovery has
  served its purpose and is removed; its checks become integration tests.)
  *Gate: offline contract tests green in CI; live integration tests pass against both sources.*
- **P2.2 — Own database.** Implement the schema above; a `vendorscope.db` loader inserts
  the cleaned frames; reproducible build from saved raw snapshots.
  *Gate: rebuild from the saved `v##` snapshots reproduces the current cleaned dataset
  (~295 rows) 1:1. (A live pull returns the grown ~570 — that is P2.4's job, not a
  parity failure.)*
- **P2.3 — AI data layer.** Embeddings over vendor/trade/classification text -> semantic
  search, cross-source fuzzy matching, dedup; foundation for P3 RAG. Embedding provider
  chosen here against the current model reference.
  *Gate: semantic lookup + match quality validated on the sample.*
- **P2.4 — Automated refresh.** One refresh entrypoint writing to the DB; pinned
  container for any browser-driven source; run-over-run diff/changelog + site-drift
  alarms. Starts manual; the scheduler (GitHub Actions cron running the pinned
  container) is a thin trigger added later — same code.
  *Gate: a dry-run refresh completes headless and reports a clean diff.*
- **P2.5 — Multi-source generalization (deferred).** Only if a real new source appears:
  parameterize the `clean_data` Y/N list + `merge_vendors` keep-set; extract a shared
  `vendorscope.scraping` library. Evaluate candidate sources with an expert review.

## Out of scope / deferred

- Broadening the eVP classification filter beyond Public Utilities (a deliberate scope
  decision for after the pipeline is proven; an expert panel weighs the
  procurement-readiness vs. gap-analysis framings).
- The public searchable name+address index and its full PII/mosaic-effect scope call
  (P3 gate; P2 only designs the DB to anticipate it).
- Docs rework (drop buyer-centric "procurement" wording, move the overview video to
  YouTube, add a "now standardized" section, em-dash sweep of `docs/*.md` +
  `reports/*.md`, untrack the two `.docx` per the Office-binary rule) — a separate
  small pass.
