# Contributing to VendorScope

VendorScope is built to a consistent set of engineering standards. This document
records them so the project stays legible, reproducible, and easy to extend. It
is a living document: as new capabilities land (see **Roadmap**), they are
documented here.

> This repo is the **reference implementation** of VendorScope: the reusable
> engine plus a real, end-to-end worked example (the Fayetteville PWC vendor
> base, kept as the flagship case-study dataset).

## Project layout

```
src/vendorscope/      # the pure, IO-free core (installable package)
  text.py             #   header / company-name / license / vendor-key normalization
  columns.py          #   license-column detection + column-index resolution
  profiling.py        #   dataframe standardization + profiling
  audit.py            #   markdown audit-report rendering
  pipeline.py         #   thin orchestrator (subcommands; no analysis logic)
src/acquisition/      # site-specific scrapers (Selenium, Playwright) — IO shell
src/cleaning/         # pandas cleaning / profiling / audit scripts — IO shell
tests/                # unit, import-smoke, CLI-help, pipeline + opt-in live integration
data/                 # sample (anonymized, committed) · raw + processed (gitignored)
```

**Functional-core / imperative-shell** is the house architecture: pure transforms
live in `vendorscope/` (no file/network/browser IO) and are unit-tested; all IO
stays in the scripts that import them.

## Toolchain

- **Python 3.14** (the OS-level interpreter; we do not install per-project Pythons).
- **uv** for the environment and locking: `uv sync` (runtime + dev), `uv lock`.
- **ruff** for lint *and* format, always via `uv run ruff` (pinned in the lockfile).
  Zero violations is the gate; `main` stays clean.
- **pytest** for tests; coverage is **measured, not gated**.
- **pre-commit** (ruff + secret scanning) and **CI** (`ruff check` + `ruff format
  --check` + `pytest` + byte-compile) enforce the above on every push and PR.

```bash
uv sync                                   # set up the environment
uv run ruff check src tests               # lint
uv run ruff format src tests              # format
uv run pytest                             # offline test suite
uv run python -m vendorscope.pipeline reproduce   # regenerate the analysis from the sample
```

## Coding standards

- **Code reads as a book.** Functions do one thing; long functions are decomposed
  into named helpers. Comments explain *why*, never *what*; self-documenting names
  carry the rest.
- **Naming.** Files and functions `snake_case`; classes `PascalCase`; constants
  `UPPER_SNAKE_CASE`; **private/internal helpers take a leading underscore**;
  directories `kebab-case`; data files `domain-subject-grain-date.ext`.
- **Type hints.** Modern syntax (`X | None`, `list[str]`, `dict[str, int]`) on
  public function signatures; Google-style docstrings on the public package API.
- **Lint scope.** Broad "data/research" ruff select
  (`E,F,W,I,UP,B,SIM,PTH,RUF` + a copyright-banner check), line length 88,
  double quotes.
- **Licence banner.** Every module's docstring ends with the two-line copyright +
  Polyform Noncommercial notice (enforced by ruff `CPY001`).
- **Errors.** Catch the specific exception a block expects (e.g. a Playwright /
  Selenium error), not bare `Exception`, except at deliberate, annotated top-level
  boundaries.

## Testing

The marker taxonomy is `unit` / `contract` / `integration`, declared with
`--strict-markers`. Unit runs are **offline by default** (`conftest.py` sets
`TEST_MODE=true`).

```bash
uv run pytest                                    # offline: unit + import-smoke + cli-help + pipeline
TEST_MODE=false uv run pytest -m integration     # opt-in: live scrapers against the NCLBGC portal
```

The live integration test asserts a known-good fixture on the real portal, so a
failure flags either a real regression or **site drift** (the page changed) — the
signal to re-validate the scrapers.

## Commits

`[VENDOR][TYPE] Imperative subject` (≤ 72 chars); `TYPE` ∈
`FEAT / FIX / DOCS / REFAC / TEST / CHORE / META`. The body explains *why*. No
attribution trailers, secrets, or absolute paths (a `commit-msg` hook enforces
this).

## Roadmap

VendorScope is developed as a 3-part arc; this document grows with it.

- **Part 1 — standards conformance, repositioning & refactor** *(done)*: installable
  `vendorscope` package on Python 3.14, the pure core extracted and unit-tested,
  broad-tier ruff conformance, a reproducible pipeline entry point, the scrapers
  decomposed, and a CI gate (lint + format + tests).
- **Part 2 — data refresh & data layer**: re-validate the scrapers against the live
  sites, refresh the data, build a proper data store, and add offline
  scraper-parsing tests (HTML fixtures); generalize the cleaning to multiple sources.
- **Part 3 — application & website**: expose the engine as an app/site.
