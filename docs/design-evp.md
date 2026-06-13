# Slice 1 Design: the eVP pipeline

**Status:** pointer (no content of its own) · **Last updated:** 2026-06-13

Slice 1 was the **template slice**: its design was authored directly into
[project-plan.md](project-plan.md) rather than as a standalone document, and every
later slice is written as a delta against it (see [design-nclbgc.md](design-nclbgc.md)
section 1, "What is identical to slice 1"). This file exists only so the `docs/`
design set is symmetric and self-describing; the canonical eVP design lives in two
sections of the plan:

- **[project-plan.md §8 — Slice 1 specification: the eVP pipeline](project-plan.md#8-slice-1-specification-the-evp-pipeline):**
  the module manifest (§8.1, pure core vs IO shell, one module per row), the
  per-slice phase walk (§8.2), and the gate checklist (§8.3).
- **[project-plan.md §4 — Data discipline applied to this build](project-plan.md#4-data-discipline-applied-to-this-build):**
  the cross-cutting design both slices share — zones and artifact names (§4.1), the
  header / snake_case-rename ruling (§4.2), the PII posture and two-file split
  (§4.3), the data dictionary (§4.4), and the ingest contract with conservation
  accounting (§4.5).

Companion slice-1 documents:

- Requirements: [requirements-evp.md](requirements-evp.md) — elaborates the REQ-\*
  subset of the plan's §9 register.
- Traceability: [traceability-evp.md](traceability-evp.md) — requirement → test
  coverage, closed at the slice-1 gate.
- Operations: [runbook-evp-drift.md](runbook-evp-drift.md) — the manual
  filter-drift repair path.

This file is intentionally a pointer. If a slice-1 design ever needs to be revised
independently of the plan, expand it here and annotate the plan sections as
superseded; until then, the plan is canonical.
