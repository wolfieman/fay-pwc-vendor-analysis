"""Pure parsers for the NCLBGC public-portal HTML fragments (no IO): the search
results table, the account-detail dialog, and the qualifiers table. The matching
acquisition client fetches these fragments; these functions only parse them, so
they are fully unit-testable against saved fixtures.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re

from bs4 import BeautifulSoup

# The detail anchor's onclick carries the (already URL-encoded) account key:
#   onclick="ShowAccountDetails( 'JTe...%3d%3d' );"
_KEY_RE = re.compile(r"ShowAccountDetails\(\s*'([^']+)'")

# Detail-dialog label -> output field name.
_DETAIL_FIELDS = {
    "Name": "company_name",
    "Address": "address",
    "Phone": "phone",
    "License #": "license_number",
    "Account Type": "account_type",
    "First Issued Date": "issue_date",
    "Expiration Date": "expiration_date",
    "Status": "status",
    "License Limitation": "license_limitation",
}


def _soup(html: str) -> BeautifulSoup:
    # stdlib html.parser backend: the portal markup is clean, server-rendered
    # HTML, so lxml's leniency buys nothing and a pure-Python parser keeps the
    # install reproducible (no C-extension to compile on an odd platform).
    return BeautifulSoup(html or "", "html.parser")


def _clean(text: str) -> str:
    """Collapse internal whitespace and trim."""
    return re.sub(r"\s+", " ", text or "").strip()


def parse_search_rows(html: str) -> list[dict[str, str]]:
    """Parse the ``_Search`` results table into one dict per row.

    Each row yields the license number, the owner/company text, the account type,
    and the opaque (URL-encoded) ``key`` used to fetch the detail and qualifier
    fragments. Returns an empty list when the results table is absent.
    """
    soup = _soup(html)
    table = soup.find("table", id="AccountSearchTable")
    if table is None:
        return []
    body = table.find("tbody") or table
    rows: list[dict[str, str]] = []
    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        anchor = cells[0].find("a")
        if anchor is None:
            continue
        match = _KEY_RE.search(anchor.get("onclick", ""))
        rows.append(
            {
                "license_number": _clean(anchor.get_text()),
                "account_type": _clean(cells[1].get_text()),
                "company_name": _clean(cells[2].get_text()),
                "key": match.group(1) if match else "",
            }
        )
    return rows


def parse_detail(html: str) -> dict[str, str]:
    """Parse the account-detail dialog into a flat record.

    Reads the ``display-label`` / ``display-field`` pairs and the Active
    Classifications fieldset. Missing fields default to an empty string;
    classifications come back semicolon-joined.
    """
    soup = _soup(html)
    out: dict[str, str] = dict.fromkeys(_DETAIL_FIELDS.values(), "")
    out["classifications"] = ""

    for label in soup.find_all("div", class_="display-label"):
        key = _DETAIL_FIELDS.get(_clean(label.get_text()))
        if key is None:
            continue
        field = label.find_next_sibling("div", class_="display-field")
        if field is None:
            continue
        if key == "address":
            parts = [ln.strip() for ln in field.get_text("\n").splitlines()]
            out[key] = ", ".join(_clean(p) for p in parts if p.strip())
        else:
            out[key] = _clean(field.get_text(" "))

    for fieldset in soup.find_all("fieldset"):
        legend = fieldset.find("legend")
        if legend is not None and _clean(legend.get_text()) == "Active Classifications":
            classes = [
                _clean(f.get_text(" "))
                for f in fieldset.find_all("div", class_="display-field")
            ]
            out["classifications"] = "; ".join(c for c in classes if c)
    return out


def parse_qualifiers(html: str) -> list[dict[str, str]]:
    """Parse the qualifiers table into one dict per qualifier.

    Skips the styled header row (it uses ``<td>`` rather than ``<th>``). Returns
    an empty list when the table is absent.
    """
    soup = _soup(html)
    table = soup.find("table")
    if table is None:
        return []
    body = table.find("tbody") or table
    rows: list[dict[str, str]] = []
    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        name = _clean(cells[0].get_text())
        if name.lower() == "name":
            continue
        rows.append(
            {
                "name": name,
                "qualifier_number": _clean(cells[1].get_text()),
                "status": _clean(cells[2].get_text()),
            }
        )
    return rows
