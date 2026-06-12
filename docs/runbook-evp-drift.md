# Runbook: eVP filter drift

**Status:** committed in slice 1 · **Audience:** the maintainer running an acquire
that halted on drift.

The eVP results page is driven by a saved-search record whose filter state lives
on a **shared, publicly mutable** Dataverse record (the `id` in the results URL).
Any portal user can change it. VendorScope therefore validates the filter state on
every acquire and **halts loudly** rather than trusting a pull whose population may
have silently shifted (REQ-03). This runbook is the manual repair path; automated
repair is deliberately out of scope until the write-side terms and credentials
questions are answered (decision D2, card R).

The raw response is always frozen **before** the halt (REQ-05), so the bytes that
triggered the alarm are available for inspection under
`data/raw/evp/<run-id>/` (`vendordetails-page-1.html`, `evp-vendors.json`,
`acquire-manifest.json`, `drift-report.json`).

## 1. Read the drift report

Open `data/raw/evp/<run-id>/drift-report.json`. Each alarm has a `kind`:

| `kind` | Meaning | Action |
|---|---|---|
| `filter-clause` | The summary clause set differs from the expected set (an **added** clause, e.g. a HUB selection, would drop the not-certified population — the basis of the HUB-gap analysis). | Repair the saved search (section 2). |
| `record-floor` | The record count fell below the configured floor (`RECORD_FLOOR`). | Inspect: a genuine shrink, or a filter narrowing? Repair if filters moved. |
| `count-mismatch` | The summary count and the parsed record count disagree. | Likely a template change; inspect the page and the parser. |
| `non-active-status` | At least one record is not `EvpStatus == Active`. | The status filter changed; repair (section 2). |
| `hub-tristate` | One of the three HUB states (blank / Certified / Not Certified) is absent. | **Halt-and-inspect alarm.** May be a legitimate pull that genuinely lacks a category; a recorded human override may pass it (section 3). It does not by itself require a repair. |

## 2. Repair the saved search (manual)

The filter state is restored through the portal's advanced-search form:

1. Open the advanced vendor search form for the saved-search record
   (`/vendors/vendorsearchadvanceform/?id=<record-id>`); the record id is in
   `cleaning/config.py` (`RECORD_ID`).
2. Reveal the filter panel via the collapse-toggle control (the triangle reveal
   icon, not the adjacent margin element).
3. Set the parity filters (codes recorded in `cleaning/config.py`):
   - eVP Status = **Active** (`FILTER_STATUS_CODE`);
   - Work/License Classifications = **Public Utilities**
     (`FILTER_CLASSIFICATION_CODE`);
   - HUB Certification Status = **left blank** on purpose, so certified,
     not-certified, and unevaluated vendors all return.
4. Save the search.
5. Re-run `vendorscope acquire-evp` and confirm the drift report is empty.

## 3. Recorded override (HUB tri-state only)

If the only alarm is `hub-tristate` and inspection shows the pull is otherwise
faithful (clauses correct, count healthy, all Active), the absence may be real
(a small category simply has no current vendors). Record the decision on the
slice card with the run id and the missing state, then proceed. Never override
`filter-clause`, `non-active-status`, or `record-floor` without repairing first.

## 4. If the page template changed

A `count-mismatch`, or an `EmbeddedDataError` from the parser, points at a markup
change rather than a filter change. Inspect the frozen
`vendordetails-page-1.html`, confirm whether the inline `var data` variable moved
or was renamed, and update the parser and its fixtures together in one commit
(the manifest test stays red until config, dictionary, and fixtures agree).
