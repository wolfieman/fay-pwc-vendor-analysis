# VendorScope Project Plan

**Status:** adopted 2026-06-12 · **Last updated:** 2026-06-12 · Supersedes the prior phase plan (deleted in slice 0b; recoverable from git history).

This is the working plan for the greenfield rebuild of VendorScope: a vendor readiness and availability analytics product built on two public North Carolina data sources, the NC electronic Vendor Portal (eVP, `evp.nc.gov`, the vendor master) and the NC Licensing Board for General Contractors (NCLBGC, `nclbgc.org`, license details), joined on license number. The Fayetteville Public Works Commission (PWC) is the flagship client and case study, not a data source. The plan was produced through a multi-expert panel review with an adversarial red-team pass and claim-by-claim verification (2026-06-12); the triggers for re-convening such a review are recorded in section 2.4.

---

## 1. Context and ground rules

The repository was deliberately cleared to a recorded zero (commit `4b977a4`): no source code, no tests, no data. The published Part-1 case study (README narrative, `reports/`) remains and stays. Everything below builds fresh from that zero under four standing rules:

1. **Knowledge yes, code no.** Prior code in git history may be read only to extract requirements and empirically earned findings; no code, test, or config is copied forward. Implementation works from the requirements register (section 9) and fixtures, never from old-code diffs.
2. **Vertical slices, gated.** Work ships as thin end-to-end increments, each walking the full per-slice SDLC (section 2.1) and ending at a crisp go/no-go gate. One slice in flight at a time.
3. **The standards this project follows are binding.** Functional core with an imperative shell, report-don't-coerce cleaning with structured audit records, the four-stage data flow (acquire, clean, validate, load) with immutable hand-offs, text-mode ingestion, controlled vocabularies read from the source, and the commit and content hygiene rules already enforced by this repository's hooks and CI guards.
4. **Public repository discipline.** Every artifact in this tree is world-readable: no personally identifying values anywhere tracked, no internal or private references, no AI or tool attribution of any kind in commits, code, docs, or pull-request text.

---

## 2. Delivery method

### 2.1 The per-slice SDLC walk

Each slice card carries this nine-phase checklist. It is the project's per-change loop made explicit. Requirements, baseline, verification distinct from testing, release, and retro are first-class phases below; operate/maintain is a standing concern owned by the refresh epic (card 6) rather than a per-slice phase.

1. **Requirements.** Mine the project docs and git history for the slice's contract; record a numbered requirements list on the card (or in `docs/`) before any design or code. Each carried-forward empirical finding becomes a numbered requirement.
2. **Analysis.** Profile the real data. Vocabularies are read from the source, never assumed; a mismatch between documentation and source is a documentation correction, not a data correction.
3. **Design.** Module seams (pure core vs IO shell), stage hand-offs, artifact names. Convene a review panel only when a section 2.4 trigger fires.
4. **Baseline.** Freeze the slice's raw inputs (date-stamped, immutable, checksummed) as they are acquired. The golden *output* baseline is a separate artifact captured at slice-1 exit (section 3.5); later slices verify against it.
5. **Test-first.** Write the failing tests for closed-form and contract logic before the implementation (policy in section 3.1).
6. **Implement.** Small `[VENDOR][TYPE]` commits on the slice branch.
7. **Verify.** Data-level proof distinct from a green test suite: idempotency re-run, conservation identity, PII sweep of every tracked artifact, drift checks exercised, run report produced (values-free), divergence from prior canaries explained rather than forced to match.
8. **Document and release.** Data dictionary and affected docs updated in the same PR; merge with CI green; tag only at milestones (D7).
9. **Retro.** A three-bullet closing comment on the card: what was learned, what moved into docs, what the next card inherits. Re-order the backlog while there.

### 2.2 Kanban overlay

- **Board:** GitHub Issues is the single source of truth; one issue per slice card, epic labels, and two state labels — `blocked` and `ready` (`ready` = open, all dependencies met, nothing blocking: the one-query answer, `gh issue list --label ready`, to "what's actionable now"). Advance the state labels at each slice's retro/release (phase 9): clear `ready` from the merged card, add `ready` to whatever its completion unblocks, and drop `blocked` wherever a dependency is now satisfied. An optional Projects view is disposable UI. No parallel backlog file in the tree (an in-repo plan doc used as a board demonstrably drifted in this project's own history).
- **Columns:** Backlog → Ready → In Progress → Verifying → Done. Entry to Ready requires: dependencies' gates passed, requirements mined onto the card, gate stated measurably, blocking owner decisions resolved.
- **WIP limit: one slice**, counted across In Progress and Verifying combined. A new slice may not start while the previous one awaits its gate. Within a slice, parallel sub-tasks are fine. Micro-chores under about 30 minutes bypass the board entirely.
- **Values-free board rule (hard):** issue, card, and PR text never contains data *values*: counts by rule, column names, and percentages only; never a cell value, never a before/after pair. (Cleaning audit records contain real contact data; nothing mechanical scans issue text, so the rule is absolute.)
- **PR per slice** is this repository's recorded, deliberate deviation from the no-branch trunk default: one short-lived branch per slice card; the merge is the go decision.

### 2.3 Ceremony explicitly excluded

Sprints and timeboxes (the gate ends a slice, not a calendar), story points and estimation, standups, velocity/burndown/cumulative-flow charts, demo ceremonies, grooming meetings, named process roles. Each fails the "who consumes this?" test for a solo team. Retained: the ordered backlog, the WIP limit, explicit entry/exit criteria, the retro comment.

### 2.4 When to re-convene a review panel

Work solo (with the pre-merge review ritual below) except when one of these fires:

1. A genuinely novel design opens: the database schema, the embedding-model choice, the app/site sketch.
2. A proposal would change a locked decision or a cross-project standard.
3. The same gate fails twice for the same cause.
4. Any change to the public data surface (new published fields, the public index, anything privacy-adjacent).
5. Deliberate scope broadening (for example, widening the eVP classification filter).
6. A source materially changes (site redesign, terms change, endpoint removed).

Standing discipline: treat panel findings as leads to verify, not facts.

### 2.5 Definition of done and the pre-merge ritual

Machines already enforce most hygiene (commit-message guard, license-banner lint rule, formatter, marker strictness, secret scan, content guards). The card checklist therefore carries only the items machines do not enforce:

1. Requirements list exists and the diff is reviewed against it (by requirement ID).
2. PII sweep clean on every tracked artifact in the diff.
3. Gate evidence attached to the card (values-free).
4. Docs updated where behavior changed.
5. Retro comment written.
6. Owner go/no-go: the PR merge.

Pre-merge ritual, in order, only under a green suite: full offline test run, correctness review pass (which includes a recorded search for placeholder or empty assertions), simplification pass, lint, format, and type check (local only, per D9), then the PR. A structured public-exposure audit (its checklist attached to the card when it runs) applies only to slices that change the public surface, and at releases.

---

## 3. Quality strategy

### 3.1 Test-first: adopted

The panel's unanimous, verification-checked verdict: affirm the standing testing standard without exception.

- **Tier A, test-first mandatory:** all pure-core logic: the eVP parser, cleaning transforms, vocabulary configs, drift predicates, dedup, header rename, the idempotency property. The carried-forward findings are themselves the test cases; writing each as a failing test first is the mechanical enforcement of "knowledge yes, code no."
- **Tier B, fixture-first at the live boundary:** the live acquisition spike is sanctioned exploratory work, and its *first deliverable* is the sanitized fixture; from that moment the parser proceeds test-first against it. Nothing merges untested: shell code is covered by fixture-driven contract tests plus opt-in integration tests before its PR merges.
- **Tier C, regression-test-first for every bug**, no exceptions.

### 3.2 Taxonomy and offline discipline

Exactly three pytest markers, declared strictly: `unit` (pure logic, the bulk), `contract` (fixture-pinned external shapes), `integration` (live, opt-in via `TEST_MODE=false`, auto-skipped otherwise, never in CI). The idempotency test (`clean(clean(x)) == clean(x)` with an empty second-pass corrections log) is a permanent regression test from slice 1 onward. Deliberately not added until a real need fires: property-based testing frameworks, coverage gates, end-to-end or performance markers.

### 3.3 Fixture rules (binding)

1. Fixtures never carry real values from the sensitive columns; substitutions are obviously synthetic (555-prefix phones, `example.com` emails, sentinel names).
2. Sanitization is performed by a checked-in script, never by hand, and includes a **pattern sweep over all fields** (email and phone regexes), because this data family is known to carry stray emails in free-text fields outside the declared sensitive columns.
3. A permanent structural test asserts no email or phone pattern matches anywhere under `tests/fixtures/`.
4. Two eVP fixtures: (a) the captured page sanitized **in place** (entity encoding preserved verbatim) as the contract of record; (b) a regenerable synthetic fixture for structural variety. Plus three drift-case fixtures: a non-Active record, an **added filter clause**, and a shrunk single-category HUB (Historically Underutilized Business certification) distribution.
5. No test ever reads `data/`.

### 3.4 CI, and what "CD" means here

CI runs the portable subset on every push: locked dependency sync, lint, format check, offline tests, byte-compile. The secret scan and content guards stay as-is. CI never runs live scrapes, the machine-local reproducibility verifier, or a coverage threshold.

"CD" for this product is **continuous delivery without continuous deployment** (automated deployment is excluded by design): the main branch is always clone-and-run green; releases are deliberate, infrequent milestone tags with the version synced across `pyproject.toml` and `CITATION.cff`; the deploy-shaped thing is the eventual scheduled refresh, whose promotion gate is the validation stage (a run may promote only when tests pass, validation thresholds hold, and row conservation holds), and whose release note is the run's diff report.

### 3.5 Verification distinct from testing

Tests check code contracts; verification judges the data outputs. A greenfield has no prior outputs to guard, so slice 1 creates the first golden baseline at its exit: a checksum manifest of the cleaned outputs, a toolchain record, and the archived raw inputs, kept **outside the repository in a machine-local location treated as a PII store** (the raw pull contains contact data; the location is written to an untracked local note and never appears in the tree or on the board). From slice 2 onward, any output-affecting change regenerates and verifies against the baseline locally; a fresh pull is a new vintage and a deliberate, recorded re-baseline.

**Counts policy:** the prior run's figures are orientation canaries only (REQ-20), valid order-of-magnitude. Gates never require matching them; a zero where tens are expected is itself a red flag (a validator gone lenient). Hard gate invariants are pipeline-controlled properties only: manifest match, idempotency, conservation, preserved leading zeros, no imputation.

---

## 4. Data discipline applied to this build

### 4.1 Zones and artifacts

The run id is `<YYYYMMDD>T<HHMMSS>-evp` (local time of the acquire), shared by the raw zone and the audit partition.

| Zone | Tracked? | Contents |
|---|---|---|
| `data/raw/evp/<run-id>/` | no (gitignored) | `vendordetails-page-1.html` (verbatim response bytes, written **before** parsing), `evp-vendors.json` (mechanically decoded records, source-native field names, values untouched), `acquire-manifest.json` (checksums, timestamp, record count, client version; written with the raw bytes), `drift-report.json` (written after detection runs) |
| `data/processed/` | no (gitignored) | the cleaned deliverable pair: `evp-vendor-master-vendor-<YYYYMMDD>.csv` (deliverable, no sensitive columns) and `evp-vendor-contacts-vendor-<YYYYMMDD>.csv` (`row_key` + sensitive columns); `audit/<run-id>/` (corrections, violations, run envelope; append-only by run id); `profile/` (profile reports) |
| `data/sample/` | yes, via the publication card only | anonymized export, sensitive columns removed, stray-email sweep applied |
| `data/DATA_DICTIONARY.md` | yes | the authoritative dictionary (4.4) |

Raw files keep chosen deterministic names documented as provenance (the source emits no filename); processed files follow the `domain-subject-grain-date.ext` kebab-case convention.

### 4.2 Header ruling (decided 2026-06-12)

The source publishes field names in its own concatenated-capitals style (for example `MainContactEmail`); these are data column headers, not code identifiers. Raw artifacts keep the source's names exactly (provenance). Cleaning configs key on those raw names, and all cleaning, idempotency, and round-trip tests run in that header space. The **snake_case rename is the final standardize step at processed-write** (for example `main_contact_email`), with a uniqueness assertion so two source columns can never silently merge. Because concatenated-capital headers are not algorithmically derivable (for example `HUBCertStartDate` becomes `hub_cert_start_date`, which no naive rule produces), **the dictionary's explicit per-column dual-name mapping is the rename contract**, confirmed at the slice-1 owner checkpoint and pinned by the dictionary-vs-config agreement test. The future database loader consumes the already-renamed processed names with no second rename. To make a vacuous pass impossible, the engine hard-fails when a configured column is absent rather than skipping it.

### 4.3 PII posture, from the first byte

- The sensitive (red) column sets per source are declared in REQ-16 and the data dictionary.
- The cleaned output is written as **two files** (named in 4.1): the deliverable without red columns, and a contacts sibling holding `row_key` plus the red columns, rehearsing the database's sensitive-table split.
- **Row identity:** `row_key` is the record's zero-padded ordinal position in the decoded raw extract, unique by construction within a run; it joins the deliverable/contacts pair losslessly and keys all audit records. Cross-run identity is the dedup key, not `row_key`.
- **Audit logs are PII-bearing by construction** (corrections carry before/after values; violations carry the offending value) and are never tracked; any tracked or posted audit output is counts-only.
- Profile reports cover red columns with counts and missingness only, never value lists.
- The only tracked data artifacts are the dictionary and, via the publication card, the anonymized sample.

### 4.4 The data dictionary

Rebuilt from zero as a slice-1 gate artifact: hand-authored from the analysis profile, with a unit test asserting it agrees with the executable column manifest and vocabulary config so neither drifts. Contents: provenance header (acquisition method, search-record identifier, the client's parity filters including the deliberately blank HUB filter, pull date, record count); a per-column table with source name, snake_case target, type, description, sensitivity (red/yellow/white), and the observed vocabulary with blank semantics and an observed-vs-documented provenance tag (under the locked filter only Active status is observable; the wider set is recorded as portal knowledge); the conventions block (identifiers and ZIP codes as text, dates `MM/DD/YYYY`, phones `###-###-####`, emails lowercased); the declared red set; the dedup key and the NCLBGC join key stated in live-source terms (`Name` + `GeneralContractorLicenseNumber`; join on `GeneralContractorLicenseNumber`).

### 4.5 Ingest contract and loss accounting (in slice 1)

A per-table column manifest is checked at read time with a hard failure on any mismatch (the source's shape is observed, not contractually documented, and its filter state is mutable by strangers; the first slices are when shape risk is highest). At end of run the conservation identity `rows_in == rows_out + dedup_drops` is asserted, consuming the engine's named dedup-drop records. Both ship in slice 1 **with their red tests**: a doctored fixture must hard-stop the manifest check, and a seeded-duplicate fixture must produce a drop that reconciles the identity. Threshold gating, cross-field date rules, and the reconciliation metric remain validation-slice work.

---

## 5. Decision log

| # | Decision (2026-06-12) | Ruling |
|---|---|---|
| D1 | Header rename timing | snake_case at processed-write inside slice 1 (see 4.2) |
| D2 | Filter-drift repair | Slice 1 ships the hardened detector + loud halt + manual runbook; automated repair is a separate card, gated on the write-side terms check and the credentials question. Slice-1 runtime deps stay `httpx` + `pandas` |
| D3 | Terms-of-use check | Two-tier: a dated, recorded terms/robots review on the slice-1 card before the first pull; full recurring-automated-access confirmation is the hard gate of the refresh slice |
| D4 | Stale docs | Delete the superseded phase plan and triage audit (history retains them); annotate the database design doc as future-slice reference; README keeps the Part-1 case study with a rebuild-in-progress note |
| D5 | Board | GitHub Issues as source of truth; values-free text rule; no in-repo board file |
| D6 | NCLBGC parsing | Stdlib `html.parser`; no parsing dependency unless the markup demonstrably defeats it (recorded as a fresh decision if so) |
| D7 | Release cadence | One milestone tag per completed slice (`v0.3.0` = slice 1, `v0.4.0` = slice 2, …); at tag time the version is synced across `pyproject.toml`, `src/vendorscope/__init__.py`, and `CITATION.cff` with `uv lock` re-run |
| D8 | Embedding table | Not created until the model (and so the vector dimension, fixed at creation) is chosen in the AI slice |
| D9 | Type checking | Adopted as a dev dependency and local pre-merge check (in the 2.5 ritual), scoped to the package; not a CI step and not a gate criterion |
| D10 | Sample publication | Its own card, gated on the owner's anonymization-scope decision and validated data (or an explicit owner-accepted caveat) |

---

## 6. Backlog: epics and slices

Each card below seeds one GitHub issue. **This table is a one-time seed: once the issues exist, GitHub Issues is authoritative (D5) and this table is not updated to track status.** A slice's gate is a single numbered checklist; evidence attaches to the card, values-free.

| Card | Covers | Depends on | Gate |
|---|---|---|---|
| **0a. Harness to green** | Fresh `pyproject.toml` + regenerated lock; package skeleton; first real tests; two-line CI fix; configuration comments rewritten to reference the project's standards generically | nothing | CI green on `main` from a fresh clone, content-guard workflows included; zero placeholder assertions (verified in the correctness review pass, noted on the card) |
| **0b. Docs triage + process adoption** | D4 deletions/annotations; dated historical annotations on the remaining prior-effort data docs (cleaning protocol, master-data documentation); README truth pass with record counts footnoted by vintage; CONTRIBUTING update (layout, per-clone guard setup, kanban overlay, CD definition); docs index fix; this plan lands; issues seeded; issue template with the DoD checklist; CI guard headers adopted from their refreshed, genericized central template | 0a; the owner's refresh of the centrally managed guard template | A locally run link-check script reports zero dead relative links (output attached as card evidence); content guards green; a tracked-file search for internal or private references returns zero hits; backlog issues exist and are ordered |
| **1. eVP pipeline** | Acquire → analyze → clean → standardize, full detail in section 8 | 0b; dated terms note (D3) | Section 8.3 checklist; stops before validation gating and any database work |
| **2. NCLBGC pipeline** | Tokenless HTTP client (session prime, search POST, detail/qualifier fragments), stdlib parsers, qualifier cell-split, license vocab including Invalid/Archived, PII split (`Phone`, `Qualifier_Name`), fixture pack with the same sanitization rules | 1 (consumes its license numbers) | Offline fragment contract tests green in CI; opt-in live run resolves every slice-1 license number or flags it; idempotent; PII sweep clean |
| **3. Validation stage** | Aggregate vocabulary/format/cross-table checks against configured thresholds; cross-field date rules with an injected reference date (never the wall clock); referential check with the per-run reconciliation metric (orphan count, match rate, trend) | 1 + 2 | A clean two-source run promotes; a deliberately poisoned fixture run halts with a red report before any load; reports keyed by run id |
| **4. Database** | Schema authored fresh (panel trigger fires): STRICT single-file SQLite, enforced foreign keys, TEXT identifiers/ZIPs/dates, blank-tolerant CHECK vocabularies, sensitive-table split, child tables, provenance spine; loader consumes snake_case processed frames; licenses load before vendors; no embedding table yet (D8) | 3 | Rebuild from the frozen slice-1/2 snapshots reproduces the cleaned dataset exactly; an out-of-vocabulary hand insert is rejected; sensitive tables provably absent from the public export |
| **5. AI / vector layer** | Embedding model chosen here via a recorded trial and decision note; vector table created at its final dimension; semantic search and cross-source matching; embedding logic isolated so the relational layer runs without it | 4 | The match-quality metric and acceptance threshold are chosen at slice entry (per the 2.2 Ready rule) and the measured result against the sample meets the threshold, recorded on the card; the relational test suite passes with the vector extension absent; extension version pinned in the lock |
| **6. Automated refresh / ops** | One refresh entrypoint composing all four stages; full run envelope (run id, timestamps, source checksums, engine and config versions; append-only audit by run id); the run-over-run diff report as the headline output; drift alarms; scheduler added last as a thin trigger | 4 (5 optional) | **Hard:** recurring-automated-access terms confirmation recorded (D3 tier 2); a headless dry run completes with a clean diff; a rehearsed threshold breach halts without touching the database |
| **7. App/site sketch** | Design card only: app/site + retrieval features + brand; the public name+address index privacy decision is framed and taken here (red-team trigger fires) | 4 | Sketch reviewed; public-index stance decided and recorded; follow-on cards cut |
| **P. Publication card** (floating) | Regenerated anonymized `data/sample/`, NOTICE data-attribution rewrite (source framing, current sensitive-column names, fresh counts), README data/methodology/reproduce rewrite, CITATION bump | 1; D10 gate | Tracked files under `data/` are only the dictionary and the sample export; no red-column values or PII patterns anywhere tracked; claims match the tree; the public-exposure audit passes (checklist attached to the card) |
| **R. Repair automation card** (floating) | Automated filter repair (browser-driven), entering only after a recorded answer on the write-side terms/courtesy question and whether the mutation needs credentials | first real drift event or slice 6 | Repair demonstrated against a rehearsed drift; terms answer recorded |
| **V. Verifier activation card** | The local verify-against-baseline script (exact-equality string compares, explicit tolerances, a headline canary chosen from the slice-1 profile) | slice-1 baseline exists | A no-op refactor verifies green; a deliberately seeded value change verifies red |

---

## 7. Slice 0a specification

One atomic PR:

1. **`pyproject.toml` rewritten from zero.** Runtime: `httpx`, `pandas` (D2 keeps the browser dependency out). Dev: `pytest`, `pytest-cov`, `ruff`, plus the type checker (D9). Carried forward verbatim because they already conform to the standards: the broad lint tier with the license-banner rule (lint-scoped preview, the copyright notice regex, first-party package name) and the strict three-marker pytest block. Dropped: the stale dependency stack, the dead per-file ignores, the sandbox exclude; all comments rewritten to reference the project's standards generically. Lock regenerated.
2. **Package skeleton:** `src/vendorscope/__init__.py` (docstring + banner + `__version__`) and `src/vendorscope/paths.py` (project root finder; `DATA_RAW`, `DATA_PROCESSED`, `DATA_SAMPLE` constants; the acquire step creates the data directories at runtime since git tracks no empty dirs).
3. **Tests:** `tests/conftest.py` (docstring **with banner**, then the offline `TEST_MODE` default; the banner is load-bearing because CI lints `tests/`), `tests/test_imports.py` (real import smoke), `tests/test_paths.py`. Every test file carries the banner.
4. **CI, two lines:** dependency sync becomes locked; an explicit `TEST_MODE` env is set to the offline default (`"true"`, so integration tests auto-skip). Nothing else in the workflows changes.
5. **README, one surgical patch:** remove the commands that no longer exist; add a one-line rebuild-in-progress note. (The full truth pass is 0b.)
6. `.gitignore` gains a `scratch/` line: experiments live in a gitignored top-level scratch directory, never inside the package; promotion is by re-authoring through the standards.

Gate: CI green on `main` (locked sync, lint, format check, tests, byte-compile) with the content-guard workflows green; zero placeholder assertions, verified in the correctness review pass and noted on the card.

---

## 8. Slice 1 specification: the eVP pipeline

**Scope:** fresh acquire → analyze/profile → clean → standardize. Stops before validation gating and any database work. Runtime dependencies: `httpx`, `pandas`.

### 8.1 Module manifest (single package, one shell)

| Module | Responsibility | Stratum |
|---|---|---|
| `paths.py` | root + data-zone constants (from 0a) | pure |
| `http_client.py` | shared HTTP session factory (owns-vs-borrows close semantics; injectable transport for tests); named to avoid shadowing the standard library | boundary IO |
| `evp_client.py` | acquire shell: one GET of the saved-search results page; writes verbatim raw + decoded JSON + acquire manifest **before** any check can abort, then runs drift detection and writes the drift report; loud halt pointing at `docs/runbook-evp-drift.md` on drift | boundary IO |
| `evp_parse.py` | pure: DOTALL regex over the embedded dataset variable → HTML-entity unescape → JSON decode; raises a specific error on template miss; **explicit stringify rule:** booleans become `'True'`/`'False'` via `str()`, documented and tested | pure |
| `drift.py` | pure predicates: exact filter-clause **set** comparison (an added clause is drift), record-count floor (REQ-03), HUB tri-state presence | pure |
| `profiling.py` | pure per-column profile: distinct values + counts, missingness, format sketches; counts-only for red columns | pure |
| `tabular.py` | text-mode frame IO (`dtype=str`, NA-token guessing off, `utf-8-sig`); column-manifest hard check at read; rename-to-snake via the dictionary mapping + uniqueness assertion at processed-write | boundary IO |
| `cleaning/records.py` | frozen Correction/Violation dataclasses; the named dedup-drop record carrying **both** the dropped and the surviving `row_key` | pure |
| `cleaning/transforms.py` | pure `(value) -> (normalized, error)` normalizers: whitespace + invisible characters, email, phone, date parse, hybrid business-name casing (digit-led tokens unchanged), text-id repair, list delimiter, vocabulary map (case-folded flag map) | pure |
| `cleaning/config.py` | `TableConfig` roles + the eVP config authored from the observed profile; `EXPECTED_COLUMNS` as the single source of the field manifest | pure |
| `cleaning/engine.py` | `clean_table` role dispatch in fixed protocol order (whitespace first, dedup last); **hard failure if a configured column is absent**; dedup semantics per REQ-11 | pure |
| `cli.py` | the only orchestration shell: `acquire-evp`, `profile`, `clean` subcommands behind the single console entrypoint `vendorscope`; standard console vocabulary | shell |

The fixture sanitizer is a checked-in script under `tools/`, following the same module skeleton. The manual drift runbook is committed at `docs/runbook-evp-drift.md` in this slice.

### 8.2 Phase walk for this slice

1. **Requirements:** commit `docs/requirements-evp.md`, the numbered register seeded from section 9. Old code may be opened only during this phase, to extract findings into the register.
2. **Analysis (includes the phase-4 raw freeze):** run the first acquire, which freezes the dated raw snapshot; profile every vocabulary candidate column; draft the dictionary.
3. **Owner checkpoint (mid-slice, blocking):** owner reviews the profile report, the dictionary draft (including the full dual-name mapping), the proposed dedup/join keys, and the record-count floor value, on the issue thread, before the config or cleaning is implemented. A wrong vocabulary encoding caught here costs minutes; caught at the gate it costs the slice.
4. **Design:** confirm the module manifest above against the requirements register.
5. **Test-first:** Tier A tests written failing first: transforms; parser against fixtures; drift predicates on all three drift fixtures; dedup semantics trio; flags end-to-end; manifest red test; engine missing-configured-column red test; conservation seeded-duplicate test; serialized round-trip; idempotency.
6. **Implement.**
7. **Verify:** the gate checklist below; the golden output baseline is captured here (gate item 12).
8. **Document and release:** dictionary committed; the slice-1-complete milestone tag (D7) lands at the owner merge, with version sync at tag time.
9. **Retro.**

### 8.3 Gate checklist (all required; owner merge = go)

1. Dated terms/robots note recorded on the card before the first live request (D3 tier 1).
2. Verbatim raw snapshot frozen (page bytes + decoded JSON + checksum manifest) and re-parsable offline from the saved bytes.
3. Column-manifest check green on the live shape and demonstrably red on a doctored fixture.
4. Dictionary committed; the dictionary-vs-config agreement test green.
5. Cleaning idempotent, **in the raw header space before the snake_case rename (per 4.2)**: in memory and through a serialized round-trip (write, read back, re-clean: zero new corrections; the county literally named "NA" survives as a string; leading-zero identifiers survive).
6. Conservation identity holds (`rows_in == rows_out + dedup_drops`) and demonstrably reconciles on the seeded-duplicate fixture.
7. Drift detector fires on all three drift fixtures (3.3 rule 4) and passes on the clean fixture; the committed runbook (`docs/runbook-evp-drift.md`) exists and the halt message points at it. The HUB tri-state check is a halt-and-inspect alarm: a recorded human override may pass a legitimate pull that genuinely lacks a category.
8. Trade flags arrive as JSON booleans and land as canonical `Yes`/`No` end-to-end (fixture-driven test).
9. PII: structural test proves no red **column** is present in the deliverable file and no red-column **values** or PII patterns appear in any tracked artifact; pattern sweep clean over `tests/fixtures/`; the two-file split joins losslessly on `row_key`, which is unique in both files.
10. Processed deliverable written snake_case with the uniqueness assertion exercised.
11. Profile report and run report (values-free, counts by rule) attached to the card; divergence from the orientation canaries (REQ-20) explained.
12. First golden baseline captured outside the repository in the PII-safe location; the location is written to an untracked machine-local note, referenced from the card only as "recorded locally."
13. CI green throughout; live integration test green on a local opt-in run.

---

## 9. Carried-forward requirements register (seed)

Numbered for traceability; slice cards cite these IDs. Extracted from project documentation and git history under the knowledge-yes-code-no rule.

| ID | Requirement |
|---|---|
| REQ-01 | eVP acquisition uses the browserless fast path: one GET of the saved-search results page (record id `20199579-3165-f111-a824-001dd812e0a9`, page 1); the full filtered dataset is embedded as an HTML-entity-encoded JSON array in an inline script variable; decode via DOTALL regex → entity unescape → JSON parse. The record id is public by the portal's design; the defense is REQ-03's detection and halt, not secrecy of the id. |
| REQ-02 | Client parity filters: status Active (option code `1`), classification Public Utilities (option code `790550003`), HUB certification deliberately blank so certified, not-certified, and unevaluated vendors all return (the basis of the HUB-gap analysis). |
| REQ-03 | The filter state lives on a shared, publicly mutable saved-search record; every acquire validates it and halts loudly on drift. Detection: exact clause-set comparison (added clause = drift), record-count floor (seeded at 500 from the documented pull of about 570; revisited at the slice-1 owner checkpoint and recorded in config), HUB tri-state presence. The tri-state check is a halt-and-inspect alarm: a recorded human override may pass a legitimate pull that genuinely lacks a category; it does not by itself trigger the repair runbook. |
| REQ-04 | Manual repair runbook (committed at `docs/runbook-evp-drift.md`): open the advanced-search form, reveal it via the collapse-toggle control, set the two option codes and the blank HUB selection, save; re-acquire and re-check. Automated repair is out of scope until the write-side terms and credentials questions are answered (card R). |
| REQ-05 | Raw is written before anything can fail: verbatim response bytes, decoded JSON, and the checksum manifest land in the date-stamped raw zone before parsing or drift checks gate the run; the drift result is written separately after detection (4.1). |
| REQ-06 | All tabular reads are text-mode: every cell a string, NA-token guessing off, `utf-8-sig`. A county named "NA" is data; identifiers and ZIP codes keep leading zeros; dates stay `MM/DD/YYYY` text. |
| REQ-07 | The parse boundary stringifies JSON booleans as `'True'`/`'False'` (via `str()`), and the flag vocabulary map is case-folded, so the ten trade flags land as canonical `Yes`/`No`. |
| REQ-08 | Observed vocabularies (read from source, never assumed): HUB and NCSBE (NC Small Business Enterprise certification) are Certified / Not Certified / blank, blank meaning unevaluated and never imputed; NCeProcurement is three-valued (Active / Inactive / Not Applicable); the vendor GC limitation includes a literal `None`; the HUB category list includes `Asian American` (not `Asian`); NCLBGC license status additionally includes `Invalid` and `Archived`. |
| REQ-09 | Report, don't coerce: a value violating its contract is flagged and left unchanged; no imputation anywhere; identifiers are never prefix-stripped **in the stored value** (out-of-state and multi-license cells surface as violations). *Scope clarified (slice 3, 2026-06-13): this governs the stored value, not a derived **search key** — the validation slice may strip extraneous decoration to extract a number purely to look the board up, which is not a value edit. A stored identifier is corrected only by a **name-confirmed** board match, logged as a correction; never inferred from address or any other circumstantial signal.* |
| REQ-10 | Business-name casing is hybrid: all-caps input is title-cased with acronym/suffix preservation; digit-led tokens (`42YL`, `51ST`) carry no case signal and are left unchanged. |
| REQ-11 | Dedup semantics: rows with any blank key value never match each other; the most complete row survives (completeness = count of non-blank cells across all columns); ties break by original row order; each drop is logged as the named dedup-drop record carrying both the dropped and the surviving `row_key`. |
| REQ-12 | Row identity: `row_key` is the record's zero-padded ordinal position in the decoded raw extract, unique by construction within a run; written into both processed files and used by all audit records. Cross-run identity is the dedup key (`Name` + `GeneralContractorLicenseNumber`), not `row_key`. |
| REQ-13 | The field manifest is single-sourced in `EXPECTED_COLUMNS` (41 fields as observed 2026-06-10; authoritative copy in config); tests assert against it, never a literal count. Shape change procedure: config, dictionary, and fixtures regenerate in one commit, with the manifest test red until all three agree. |
| REQ-14 | Idempotency is a permanent regression test: re-cleaning cleaned output produces zero corrections, asserted in memory and through the serialized round-trip, in the raw header space (4.2). |
| REQ-15 | Conservation: `rows_in == rows_out + dedup_drops`, asserted at end of run and covered by a seeded-duplicate red test. |
| REQ-16 | Red columns: eVP `MainContactName` / `MainContactEmail` / `MainContactPhone`; NCLBGC `Phone` / `Qualifier_Name`. Red-column **values** never appear anywhere: not tracked, not in fixtures, not in board or PR text. The columns themselves are never tracked (the names may be discussed, per 2.2); audit logs are PII-bearing and never tracked; stray-PII pattern sweeps apply to every published artifact. |
| REQ-17 | Multi-value cells standardize to `'; '` delimiting during cleaning; splitting into rows is the database slice's job. NCLBGC qualifier cells are known to arrive packed and with a header-bleed artifact to scrub at parse. |
| REQ-18 | NCLBGC acquisition (slice 2): tokenless HTTP with a primed session cookie; search POST returns HTML fragments; detail and qualifiers fetched per opaque key; stdlib parsing; one license at a time with a politeness delay. |
| REQ-19 | Future load order: licenses before vendors (the vendor license reference is enforced); the embedding table is created only at its final dimension. |
| REQ-20 | The prior verified run's counts (about 7,100 corrections; 64 strict license-format violations; about 570 records) are orientation canaries only; they describe a different vintage and filter scope from the published Part-1 study's 295 records, and gates never require equality. |

---

## 10. Top risks and their nets

| Risk | Net |
|---|---|
| Shared filter record changed by a stranger (worst case: silent loss of the blank/not-certified HUB population) | REQ-03 hardened detection, three drift fixtures with red tests, the acquire-gate tri-state alarm (halt-and-inspect with recorded override), halt + committed runbook |
| Live shape change on the first pull (new/renamed fields, template change) | read-time manifest hard stop (REQ-13), raw-first persistence (REQ-05), the one-commit shape-change procedure |
| PII reaching the public tree (fixtures, audit logs, board text, baseline location) | fixture rules (3.3), audit-logs-never-tracked, values-free board rule, PII-store baseline rule, structural tests, per-publication exposure audit |
| Empirically earned behavior lost in the rewrite | every finding is a numbered requirement with a named test; old code consultable only in the requirements phase; review by requirement ID |
| Terms-of-use exposure | two-tier check (D3); automated repair deferred behind the write-side answer (card R) |
| Gate theater (gates passed selectively or going stale) | one numbered gate checklist per card; WIP limit counts Verifying; evidence attached on the card; owner merge is the only go |
