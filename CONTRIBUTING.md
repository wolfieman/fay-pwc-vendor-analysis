# Contributing to VendorScope

VendorScope is built to a consistent set of engineering standards. This document
records them so the project stays legible, reproducible, and easy to extend. It
is a living document: as new capabilities land (see **Plan**), it is updated in
the same PR.

> This repo is the **reference implementation** of VendorScope: the reusable
> engine plus a real, end-to-end worked example (the Fayetteville PWC vendor
> base, kept as the flagship case-study dataset).

## Project layout

```text
src/vendorscope/      # the installable package; everything importable lives here
  paths.py            #   the single root-finder + data-zone constants
tests/                # pytest suite; fixtures under tests/fixtures/
docs/                 # project plan (backlog + gates) and data references
data/                 # raw + processed (gitignored, PII); sample regenerates in the eVP slice
scratch/              # gitignored experiments; promoted only by re-authoring into the package
```

**Functional core / imperative shell** is the house architecture: pure transforms
live in pure modules (no file/network IO) and are unit-tested; IO concentrates in
boundary modules (acquisition clients, tabular IO) and a single CLI shell as they
land, slice by slice.

## Toolchain

- **Python 3.14** (the OS-level interpreter; we do not install per-project Pythons).
- **uv** for the environment and locking: `uv sync` (runtime + dev), `uv lock`.
  CI syncs with `--locked`, so lockfile drift fails loud.
- **ruff** for lint *and* format, always via `uv run ruff` (pinned in the lockfile).
  Zero violations is the gate; `main` stays clean.
- **pytest** for tests; coverage is **measured, not gated**.
- **pyright** (basic mode, scoped to the package) as a local pre-merge check;
  it is not a CI step.
- **pre-commit** (ruff + secret scanning) locally, and **CI** (locked sync +
  `ruff check` + `ruff format --check` + `pytest` + byte-compile) on every push
  and PR; CI re-runs the content guards server-side for clones without hooks.

```bash
uv sync                        # set up the environment
uvx pre-commit install         # once per clone: local lint + secret-scan hooks
uv run ruff check src tests    # lint
uv run ruff format src tests   # format
uv run pytest                  # offline test suite
uv run pyright                 # type check (local gate)
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
- **License banner.** Every module's docstring (tests included) ends with the
  two-line copyright + Polyform Noncommercial notice (enforced by ruff `CPY001`).
- **Errors.** Catch the specific exception a block expects (e.g. an `httpx`
  error), not bare `Exception`, except at deliberate, annotated top-level
  boundaries.

## Testing

The marker taxonomy is `unit` / `contract` / `integration`, declared with
`--strict-markers`. Unit and contract runs are **offline by default**
(`conftest.py` sets `TEST_MODE=true`); fixtures never carry real contact data.

```bash
uv run pytest                                  # offline: unit + contract
TEST_MODE=false uv run pytest -m integration   # opt-in: live acquisition checks
```

A live integration failure flags either a real regression or **site drift** (a
source page changed): the signal to re-validate acquisition before trusting a pull.

## Process

Work ships as **vertical slices** on a kanban flow:

- **Board:** GitHub Issues is the single source of truth (one issue per slice
  card; epic labels; `blocked` as a label). No board files live in the tree.
- **Columns:** Backlog, Ready, In Progress, Verifying, Done. **WIP limit: one
  slice**, counted across In Progress and Verifying. Micro-chores (under about
  30 minutes) bypass the board.
- **Card text is values-free:** counts by rule, column names, and percentages
  only; never a data value or a before/after pair.
- **Each card walks the full loop:** requirements, analysis, design, baseline,
  test-first, implement, verify, document/release, retro.
- **Definition of done** (beyond the machine gates): diff reviewed against the
  card's numbered requirements; PII sweep of every tracked artifact; gate
  evidence attached to the card; docs updated where behavior changed; a short
  retro comment; the owner's merge of the slice PR is the go decision.
- **Pre-merge ritual**, only under a green suite: full offline run, correctness
  review, simplification pass, lint + format + type check, then the PR. One
  short-lived branch and PR per slice (a recorded local deviation from the
  trunk-only default).
- **Releases** are deliberate milestone tags, with the version synced across
  `pyproject.toml` and `CITATION.cff` at tag time. `main` is always
  clone-and-run; there is no automated deployment.

## Commits

`[VENDOR][TYPE] Imperative subject` (≤ 72 chars); `TYPE` ∈
`FEAT / FIX / DOCS / REFAC / TEST / CHORE / META`. The body explains *why*. No
attribution trailers, secrets, or absolute paths (a `commit-msg` hook enforces
this).

## Plan

- **Part 1 (shipped):** the published PWC case study (see [`reports/`](reports/)).
- **The rebuild (current):** greenfield, in gated slices per
  [`docs/project-plan.md`](docs/project-plan.md): harness, eVP pipeline, NCLBGC
  pipeline, validation, database, AI/vector layer, automated refresh, app sketch.
