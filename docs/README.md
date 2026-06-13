# Documentation

- [project-plan.md](project-plan.md) — the working plan: delivery method, quality strategy, the slice backlog with gates, and the carried-forward requirements register.
- [design-evp.md](design-evp.md) / [design-nclbgc.md](design-nclbgc.md) — per-slice design. Slice 1's lives inline in the project plan (§4 + §8); `design-evp.md` is a pointer to it. Slice 2's is a standalone delta against slice 1.
- [data-cleaning-protocol.md](data-cleaning-protocol.md) — the repeatable value-standardization protocol (requirements input for the rebuild).
- [master-data-documentation.md](master-data-documentation.md) — data standards, controlled vocabularies, and glossary.
- [database-schema.md](database-schema.md) — design reference for the future database slice.

The column-level data dictionary (`data/DATA_DICTIONARY.md`) carries one section per source table (eVP, NCLBGC), each pinned to its config by an agreement test; the retired Part-1 version lives in git history.
