"""Pure parser: NCLBGC HTML fragments to text license records.

Stdlib ``html.parser`` (decision D6): no third-party parsing dependency. Three
fragment shapes, each handled by a small ``HTMLParser`` subclass:

- the search result carries the opaque account key in an ``onclick`` handler
  (``ShowAccountDetails('<key>')``); an empty search yields no key (the flag
  path);
- the detail fragment is a series of ``display-label`` / ``display-field`` div
  pairs grouped by ``<legend>``; the ``Active Classifications`` block is a
  ``<br />``-separated list;
- the qualifiers fragment is a table whose body rows can include a ``Status``
  header-bleed row that is scrubbed here.

The parser emits the Master Data Documentation Part II field names (the raw
header space), values otherwise untouched: the ``L.``/``Q.`` sigils, the address
``<br />``, and the like are left for the cleaning stage. ``parse_detail`` raises
``NclbgcTemplateError`` when the fragment carries no fields (a markup change),
the raw bytes already frozen by the client for forensics.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re
from html.parser import HTMLParser

# The twelve-column license-details schema (Master Data Documentation Part II),
# in order; the raw header space before the snake_case rename.
FIELDS = (
    "License_Number",
    "Company_Name",
    "Address",
    "Phone",
    "Issue_Date",
    "Expiration_Date",
    "Status",
    "License_Limitation",
    "Classifications",
    "Qualifier_Number",
    "Qualifier_Name",
    "Qualifier_Status",
)

# Detail fragment label -> schema field. Labels absent here (Account Type) drop.
_LABEL_MAP = {
    "Name": "Company_Name",
    "Address": "Address",
    "Phone": "Phone",
    "License #": "License_Number",
    "First Issued Date": "Issue_Date",
    "Expiration Date": "Expiration_Date",
    "Status": "Status",
    "License Limitation": "License_Limitation",
}
_CLASSIFICATIONS_LEGEND = "Active Classifications"
_KEY_RE = re.compile(r"ShowAccountDetails\(\s*'([^']+)'\s*\)")


class NclbgcTemplateError(ValueError):
    """A detail fragment carried no recognizable fields (a markup change)."""


class _KeyCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.onclicks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            onclick = dict(attrs).get("onclick")
            if onclick:
                self.onclicks.append(onclick)


class _DetailCollector(HTMLParser):
    """Collects ``(legend, kind, pieces)`` for each label/field div in order."""

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[tuple[str, str, list[str]]] = []
        self._legend = ""
        self._legend_buf = ""
        self._in_legend = False
        self._kind: str | None = None
        self._pieces: list[str] = []
        self._buf = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "legend":
            self._in_legend = True
            self._legend_buf = ""
        elif tag == "div":
            css = dict(attrs).get("class", "")
            if css == "display-label":
                self._kind, self._pieces, self._buf = "label", [], ""
            elif css == "display-field":
                self._kind, self._pieces, self._buf = "field", [], ""
        elif tag == "br" and self._kind:
            self._pieces.append(self._buf.strip())
            self._buf = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "legend":
            self._in_legend = False
            self._legend = self._legend_buf.strip()
        elif tag == "div" and self._kind:
            self._pieces.append(self._buf.strip())
            self.entries.append(
                (self._legend, self._kind, [p for p in self._pieces if p])
            )
            self._kind, self._pieces, self._buf = None, [], ""

    def handle_data(self, data: str) -> None:
        if self._in_legend:
            self._legend_buf += data
        elif self._kind:
            self._buf += data


class _TableCollector(HTMLParser):
    """Collects ``(section, cells)`` for each table row."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str, list[str]]] = []
        self._section = ""
        self._cells: list[str] | None = None
        self._in_td = False
        self._buf = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("thead", "tbody"):
            self._section = tag
        elif tag == "tr":
            self._cells = []
        elif tag == "td":
            self._in_td, self._buf = True, ""

    def handle_endtag(self, tag: str) -> None:
        if tag in ("thead", "tbody"):
            self._section = ""
        elif tag == "td" and self._cells is not None:
            self._cells.append(self._buf.strip())
            self._in_td = False
        elif tag == "tr" and self._cells is not None:
            self.rows.append((self._section, self._cells))
            self._cells = None

    def handle_data(self, data: str) -> None:
        if self._in_td:
            self._buf += data


def parse_search_keys(page: str) -> list[str]:
    """Extract the opaque account keys from the search result's onclick handlers."""
    collector = _KeyCollector()
    collector.feed(page)
    keys: list[str] = []
    for onclick in collector.onclicks:
        match = _KEY_RE.search(onclick)
        if match and match.group(1) not in keys:
            keys.append(match.group(1))
    return keys


def parse_detail(fragment: str) -> dict[str, str]:
    """Decode the detail fragment into the nine detail-derived schema fields."""
    collector = _DetailCollector()
    collector.feed(fragment)
    if not any(kind == "field" for _, kind, _ in collector.entries):
        raise NclbgcTemplateError("detail fragment carried no display fields")

    record: dict[str, str] = {}
    pending_label: str | None = None
    for legend, kind, pieces in collector.entries:
        if kind == "label":
            pending_label = " ".join(pieces)
            continue
        if legend == _CLASSIFICATIONS_LEGEND:
            record["Classifications"] = "; ".join(pieces)
        elif pending_label is not None:
            field = _LABEL_MAP.get(pending_label)
            if field is not None:  # unmapped labels (Account Type) drop
                record[field] = " ".join(pieces)
        pending_label = None

    for field in _LABEL_MAP.values():
        record.setdefault(field, "")
    record.setdefault("Classifications", "")
    return record


def parse_qualifiers(fragment: str) -> list[dict[str, str]]:
    """Decode the qualifiers table, scrubbing the Status header-bleed row."""
    collector = _TableCollector()
    collector.feed(fragment)
    headers = next(
        (cells for section, cells in collector.rows if section == "thead"), []
    )
    rows: list[dict[str, str]] = []
    for section, cells in collector.rows:
        if section != "tbody" or len(cells) < 3:
            continue
        if cells[:3] == headers[:3]:  # the bled header row
            continue
        rows.append(
            {
                "Qualifier_Name": cells[0],
                "Qualifier_Number": cells[1],
                "Qualifier_Status": cells[2],
            }
        )
    return rows


def decode_record(detail_fragment: str, qualifiers_fragment: str) -> dict[str, str]:
    """Combine the detail and qualifiers fragments into one flat schema record."""
    record = parse_detail(detail_fragment)
    qualifiers = parse_qualifiers(qualifiers_fragment)
    record["Qualifier_Number"] = "; ".join(q["Qualifier_Number"] for q in qualifiers)
    record["Qualifier_Name"] = "; ".join(q["Qualifier_Name"] for q in qualifiers)
    record["Qualifier_Status"] = "; ".join(q["Qualifier_Status"] for q in qualifiers)
    return {field: record.get(field, "") for field in FIELDS}
