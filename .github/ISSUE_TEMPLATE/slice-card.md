---
name: Slice card
about: One vertical slice. The issue is the card; gate evidence attaches here.
labels: slice
---

<!-- markdownlint-disable MD041 -->
<!-- Card text is public and VALUES-FREE: counts by rule, column names, and
percentages only. Never paste a data value, a before/after pair, or audit-log
rows. No internal or private references. -->

**Epic:**
**Depends on:**

## Covers

## Gate (single numbered checklist; crisp evidence only)

1.

## Requirements

Numbered REQ ids this slice implements (mined before design or code):

## Phase walk

- [ ] Requirements mined onto the card
- [ ] Analysis (profile the real data)
- [ ] Design confirmed against the requirements
- [ ] Baseline (raw inputs frozen, checksummed)
- [ ] Test-first (failing tests for pure-core logic precede implementation)
- [ ] Implement
- [ ] Verify (idempotency, conservation, PII sweep, values-free run report)
- [ ] Document + release (docs updated in the same PR)
- [ ] Retro comment (learned / moved to docs / queued next)

## Definition of done (human items; machines enforce the rest)

- [ ] Diff reviewed against the requirement ids
- [ ] PII sweep clean on every tracked artifact
- [ ] Gate evidence attached (values-free)
- [ ] Docs updated where behavior changed
- [ ] Retro written
- [ ] Owner go/no-go: the PR merge
