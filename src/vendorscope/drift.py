"""Pure drift predicates over the parsed results page.

The filter state lives on a shared, publicly mutable saved-search record, so
every acquire must validate it and halt loudly on drift (REQ-03). The signals:

- the filter-clause set must equal the expected set exactly (an *added* clause,
  e.g. a HUB selection that would drop the not-certified population, is drift);
- the record count must be at or above the floor;
- the summary count must equal the parsed record count (integrity);
- no record may carry a non-Active status (the status filter changed);
- the three HUB states must all be present (a halt-and-inspect alarm: a recorded
  human override may pass a legitimate pull that genuinely lacks one).

All values placed in an alarm detail are non-sensitive (filter text and counts),
never cell data.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from dataclasses import dataclass

EXPECTED_CLAUSES = ("Status: Active", "WorkLicense Classifications: Public Utilities")
EXPECTED_HUB_STATES = ("", "Certified", "Not Certified")

_COUNT_RE = re.compile(r"<strong>\s*(\d+)\s*Records</strong>")
_CRITERIA_RE = re.compile(r"filter criteria:<br>(.*?)</p>", re.S)


@dataclass(frozen=True, slots=True)
class DriftAlarm:
    kind: str
    detail: str


def parse_filter_summary(page: str) -> tuple[int, tuple[str, ...]]:
    """Extract the record count and the filter-clause tuple from the summary block."""
    count_match = _COUNT_RE.search(page)
    count = int(count_match.group(1)) if count_match else -1
    criteria_match = _CRITERIA_RE.search(page)
    clauses: tuple[str, ...] = ()
    if criteria_match:
        clauses = tuple(
            part.strip()
            for part in criteria_match.group(1).split("<br>")
            if part.strip()
        )
    return count, clauses


def clause_drift(
    clauses: tuple[str, ...], expected: tuple[str, ...] = EXPECTED_CLAUSES
) -> bool:
    return set(clauses) != set(expected)


def count_floor_drift(count: int, floor: int) -> bool:
    return count < floor


def non_active(records: list[dict[str, str]]) -> list[dict[str, str]]:
    return [r for r in records if r.get("EvpStatus", "") != "Active"]


def hub_tristate_alarm(
    records: list[dict[str, str]], expected: tuple[str, ...] = EXPECTED_HUB_STATES
) -> bool:
    present = {r.get("HUB", "") for r in records}
    return bool(set(expected) - present)


def evaluate(
    page: str,
    records: list[dict[str, str]],
    *,
    floor: int,
    expected_clauses: tuple[str, ...] = EXPECTED_CLAUSES,
    expected_hub_states: tuple[str, ...] = EXPECTED_HUB_STATES,
) -> list[DriftAlarm]:
    """Return every drift alarm; an empty list means the pull matches expectations."""
    alarms: list[DriftAlarm] = []
    count, clauses = parse_filter_summary(page)

    if clause_drift(clauses, expected_clauses):
        alarms.append(DriftAlarm("filter-clause", f"clauses={list(clauses)}"))
    if count_floor_drift(count, floor):
        alarms.append(DriftAlarm("record-floor", f"count={count} floor={floor}"))
    if count != -1 and count != len(records):
        alarms.append(
            DriftAlarm("count-mismatch", f"summary={count} parsed={len(records)}")
        )
    off_status = non_active(records)
    if off_status:
        alarms.append(
            DriftAlarm("non-active-status", f"{len(off_status)} record(s) not Active")
        )
    if hub_tristate_alarm(records, expected_hub_states):
        alarms.append(
            DriftAlarm(
                "hub-tristate", "a HUB state is absent (inspect; override allowed)"
            )
        )

    return alarms
