# VendorScope — Reconciled Triage Map

**Scope:** all 30 `src/` Python modules. **Method:** every load-bearing claim re-verified against the files (not just trusted from the inputs).
**Conservative-kill rule honored:** the KILL-CHECKS input was empty (`[]`) — **no kill was independently confirmed safe** — so every kill-eligible module is downgraded to **kill_with_companions** and carries a `fix` verdict in the table. The owner deletes nothing on our say-so.

**Counts:** keep **15** · fix **15** · kill (standalone) **0** · kill_with_companions **11** (subset of the fix rows) · total **30**.

---

## 1. Triage table

| Module | Verdict | One-line reason |
|---|---|---|
| `src/vendorscope/__init__.py` | keep | Wheel package marker + `__version__`; imported by tests + every submodule. Docstring slightly overstates 'IO-free core' (cosmetic). |
| `src/vendorscope/http.py` | keep | NEW acquisition core; owns-vs-borrows `close()` is what makes MockTransport tests work. |
| `src/vendorscope/evp_parse.py` | keep | NEW pure eVP `var data` parser; 5 tests; raises on template change. |
| `src/vendorscope/evp_client.py` | keep | NEW live eVP entrypoint; fast path tested. Playwright repair path only integration-covered (residual risk). |
| `src/vendorscope/nclbgc_parse.py` | keep | NEW pure NCLBGC parsers; best-tested (6 exact-string fixtures). |
| `src/vendorscope/nclbgc_client.py` | keep | NEW browserless replacement for BOTH legacy scrapers; parity canary. |
| `src/vendorscope/cleaning/__init__.py` | keep | NEW engine facade; `__all__` consistent, no logic. |
| `src/vendorscope/cleaning/transforms.py` | keep | NEW **canonical normalization** that supersedes legacy `text.py` + `profiling.normalize`; 38 tests. |
| `src/vendorscope/cleaning/config.py` | **fix** | Vocab **drift vs schema.py**: add `Archived`+`Invalid` to `LICENSE_CONFIG.Status` (L268); `HUBCategory` `Asian`→`Asian American` (L247). |
| `src/vendorscope/cleaning/pipeline.py` | keep | NEW engine composition; tested + live-verified. FLAG: one of three `*pipeline*` modules. |
| `src/vendorscope/cleaning/validate.py` | keep | NEW REPORTING validators (Violation rows). Different layer from sandbox verdict-validation — reconcile, don't merge. |
| `src/vendorscope/cleaning/cli.py` | **fix** | Runs end-to-end, but **not in `test_cli_help.py`** and **undocumented** — close before legacy `clean_data` retires. |
| `src/vendorscope/db/__init__.py` | keep | DB facade; live build succeeds. |
| `src/vendorscope/db/connection.py` | keep | FK-ON + sqlite-vec load correct (FK-rejection tests only pass because FK is ON). |
| `src/vendorscope/db/schema.py` | **fix** | Runs (22 tests) but: vocab drift vs config; single scalar license FK can't carry multi-value/out-of-state numbers; loader not yet written. |
| `src/vendorscope/sandbox/__init__.py` | keep | Wheel-excluded WIP marker (verified pyproject:30). |
| `src/vendorscope/sandbox/license_validation.py` | **fix** | `clean_gc_number` crashes on float NaN; `'810.0'` mis-routes a real NC license; zero tests. |
| `src/vendorscope/sandbox/validate_pipeline.py` | **fix** | Inherits the NaN crash (one missing GC number aborts a live run); untested; third `*pipeline*` name. |
| `src/vendorscope/text.py` | fix · kill_with_companions | `normalize_license` silently fabricates values; 4 legacy importers — retire with the legacy chain. |
| `src/vendorscope/columns.py` | fix · kill_with_companions | Imported ONLY by the 2 legacy acquisition scrapers; dies with Chain B. |
| `src/vendorscope/profiling.py` | fix · kill_with_companions | Legacy `normalize`/`profile_dataframe`; dies with Chain A. |
| `src/vendorscope/audit.py` | fix · kill_with_companions | Only `make_audit` consumes it; dies with Chain A. |
| `src/vendorscope/pipeline.py` | **fix** · bridge | THE bridge pinning all 5 legacy scripts. **Confirmed bug:** `SAMPLE` reads `data/sample/...csv` but it moved to `data/sample/legacy/`; `test_pipeline` masks it via monkeypatch. |
| `src/cleaning/clean_data.py` | fix · kill_with_companions | `read_any()` coerces `license_number`→int64 (drops leading zeros) — the dirty-id bug the new engine fixed. |
| `src/cleaning/profile_data.py` | fix · kill_with_companions | Live via `reproduce()`; pure core already in `vendorscope.profiling`. |
| `src/cleaning/make_audit.py` | fix · kill_with_companions | Live via `reproduce()`; pure core in `vendorscope.audit`. No defect of its own. |
| `src/cleaning/merge_vendors.py` | fix · kill_with_companions | NOT in `reproduce()` SCRIPTS; only tests + a P2.5 mention. Cleanest kill IF P2.5 dropped. |
| `src/cleaning/list_columns.py` | fix · kill_with_companions | No first-party imports/no consumer; 2 real bugs (py2 `except`, emoji UnicodeEncodeError on Windows). Smallest blast radius. |
| `src/acquisition/nclbgc_licenses_acquisition.py` | fix · kill_with_companions | Legacy Playwright scraper; pipeline SCRIPTS + 4 tests + methodology pin it. |
| `src/acquisition/nclbgc_license_details_acquisition.py` | fix · kill_with_companions | Legacy Selenium scraper; py2 `except` (L216); `normalize_license` mangles dirty licenses; same blast radius. |

---

## 2. Duplication clusters

- **VALIDATION (reconcile, do NOT merge):** `cleaning/validate.py` = REPORTING (in-memory vocab/format/referential → Violations, no network) vs `sandbox/license_validation.py` = VERDICT (live NCLBGC, owner-matched, soundex). **Keep both.** Document which layer owns "is this license real?"; fix the sandbox input-boundary defects. They are different layers, not a dedupe target.
- **NORMALIZATION (legacy superseded):** keep `cleaning/transforms.py` as the single source; retire `text.py` (`normalize_license` value-fabrication defect) and `profiling.normalize` (3-name hardcoded Y/N map) **with their legacy chains**, after replacing `normalize_license`'s role with `normalize_text_id` + the reporting layer.
- **THREE `*pipeline*` MODULES (rename, none is a dup):** keep `cleaning/pipeline.py` as the canonical "pipeline"; retire `vendorscope/pipeline.py` with the legacy chain; rename `sandbox/validate_pipeline.py` (e.g. `validate_runner.py`). Consider renaming `cleaning/pipeline.py`→`compose.py`/`engine.py` when the legacy one goes.
- **Profiling-core split (no action):** `vendorscope.profiling.profile_dataframe` (pure, tested) vs `profile_data.py` (IO shell) — the shell is safely removable because the core is extracted.
- **Audit/reporting overlap (conceptual):** legacy `audit.build_report`/`make_audit` vs the engine's violations/corrections output — different mechanisms; keep until the legacy chain retires.

---

## 3. Dead chains (must die together)

- **Chain A — reproduce() cleaning chain:** `pipeline.reproduce()` → `clean_data`/`profile_data`/`make_audit` → `vendorscope.{profiling.normalize, profiling.profile_dataframe, audit.build_report}`. Retiring the 3 scripts frees `audit.py` and `profiling.py`. **Already broken at runtime** (stale `data/sample/` path, verified).
- **Chain B — legacy acquisition scrapers:** both `src/acquisition/*` → `vendorscope.columns.*` + `vendorscope.text.{normalize_name, normalize_license}`. Retiring both frees `columns.py` (no other importer).
- **Chain C — `text.py` fan-in:** imported by FOUR legacy modules (both scrapers, `profiling.py`, `merge_vendors.py`). Dies only after Chains A + B + `merge_vendors` are all retired.
- **Chain D — `merge_vendors.py`:** near-orphan (tests + P2.5 mention only; not in SCRIPTS); also a `text.py` importer.
- **Chain E — `list_columns.py`:** true orphan; dies alone with two test-list entries removed.

---

## 4. Kills needing confirmation (companion edits required, one commit each)

Empty kill-checks ⇒ all 11 below are **kill_with_companions**, owner-confirm.

1. **`list_columns.py`** — drop entries in `test_cli_help.py` (L23) + `test_imports.py` SCRIPT_MODULES. *Alt:* repair `except (TypeError, ValueError)` + de-emoji.
2. **`merge_vendors.py`** — drop the two test entries; **precondition:** P2.5 keep-set plan dropped.
3. **`nclbgc_licenses_acquisition.py`** — delete + edit `pipeline.SCRIPTS`, `test_cli_help.py` L24, `test_imports.py` L42, `test_scrapers_integration.py` (LICENSES + its test), `methodology.md` L12. Leave `test_pipeline` negatives.
4. **`nclbgc_license_details_acquisition.py`** — same set for `acquire-details` (L25/L43/DETAILS/L15). *Interim fix if kept:* L216 `except (TimeoutException, WebDriverException):`.
5. **`columns.py`** — only after #3 **and** #4: remove from PACKAGE_MODULES, delete `test_columns.py`, CONTRIBUTING line.
6. **`clean_data.py`** — delete + edit `pipeline.SCRIPTS['clean']` + `reproduce()`, `test_pipeline` chain assertion, `test_cli_help.py` L19, SCRIPT_MODULES, README L61/160/154, `data-cleaning-protocol.md`, `methodology.md` §2. **Precondition:** `cleaning/cli.py` documented + tested first.
7. **`profile_data.py`** — delete + edit SCRIPTS['profile'] + `reproduce()`, chain assertion, `test_cli_help.py` L22, SCRIPT_MODULES, README L66/161, `methodology.md` §4.
8. **`make_audit.py`** — delete + edit SCRIPTS['audit'] + `reproduce()`, chain assertion, `test_cli_help.py`, SCRIPT_MODULES, README L67, `methodology.md` §5.
9. **`audit.py`** + **`profiling.py`** — only after Chain A fully retired: remove from PACKAGE_MODULES, delete `test_audit.py`/`test_profiling.py`, CONTRIBUTING lines.
10. **`text.py`** — only after Chains A + B + `merge_vendors` all retired: remove from PACKAGE_MODULES, delete `test_text.py`, CONTRIBUTING line.

### Pre-kill hygiene (do first, independent of deletion)
- **Vocab reconcile** `config.py` ↔ `schema.py` (status `Archived`/`Invalid`; HUBCategory `Asian`→`Asian American`) — else clean→load fails schema CHECKs.
- **Fix the data-path bug** in `reproduce()` **and** README L160-161 (point at `data/sample/legacy/`, verified) + add a non-mocked path-existence test so `test_pipeline` stops masking it.
- **Harden** `sandbox/license_validation.clean_gc_number` (str-coerce NaN, strip trailing `.0`) before any live run.