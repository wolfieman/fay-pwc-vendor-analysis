"""Pure parsers for the eVP (NC electronic Vendor Portal) results page (no IO).

The results page renders the saved search server-side and embeds the entire
filtered vendor set as an inline JS variable ``var data = "[{...}]"``
(HTML-entity-encoded). These functions extract and validate that dataset; the
matching client only fetches the page.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import html
import json
import re

# `var data = "[ ... ]";` — non-greedy, but the JSON's own quotes are HTML-escaped,
# so the only literal `]"` is the array close + the JS-string close.
_DATA_RE = re.compile(r'var\s+data\s*=\s*"(\[.*?\])"\s*;?', re.S)


def parse_embedded_records(page_html: str) -> list[dict[str, str]]:
    """Extract the embedded ``var data`` vendor records from the results page.

    Raises ``ValueError`` if the variable is absent (the template changed).
    """
    match = _DATA_RE.search(page_html or "")
    if match is None:
        raise ValueError("embedded `var data` not found in the eVP results page")
    return json.loads(html.unescape(match.group(1)))


def filters_applied(
    page_html: str,
    records: list[dict[str, str]],
    expect_summary: tuple[str, ...],
    status: str = "Active",
) -> bool:
    """Whether the page reflects the intended filter state.

    Belt-and-braces: the results page must echo every ``expect_summary`` string
    *and* every record must carry the expected ``status`` (the filter lives on a
    shared portal record, so it can drift between runs).
    """
    summary_ok = all(s in (page_html or "") for s in expect_summary)
    status_ok = bool(records) and all(r.get("EvpStatus") == status for r in records)
    return summary_ok and status_ok
