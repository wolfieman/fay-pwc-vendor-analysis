"""httpx client for the NCLBGC public portal (the IO shell over the pure parsers
in nclbgc_parse). The portal search is a tokenless HTTP endpoint, so acquisition
is a session cookie plus three calls — search, detail, qualifiers — with no
browser. Network IO lives here; all parsing is delegated to the pure functions.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import urllib.parse

import httpx

from vendorscope.http import HttpSession
from vendorscope.nclbgc_parse import (
    parse_detail,
    parse_qualifiers,
    parse_search_rows,
)

_BASE = "https://portal.nclbgc.org"
_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{_BASE}/Public/Search",
}
# The full advanced-search form; only a few fields are ever set.
_SEARCH_FIELDS = (
    "ClassificationDefinitionIdnt",
    "AccountNumber",
    "QualifierAccountNumber",
    "CompanyName",
    "FirstName",
    "LastName",
    "PhoneNumber",
    "streetAddress",
    "PostalCode",
    "City",
    "StateCode",
)


class NCLBGCClient(HttpSession):
    """Stateful session against the NCLBGC portal. Use as a context manager."""

    def __init__(self, client: httpx.Client | None = None, timeout: float = 30.0):
        super().__init__(_BASE, client=client, timeout=timeout, headers=_HEADERS)
        self._primed = False

    def _prime(self) -> None:
        """Fetch the search page once to establish the session cookie."""
        if not self._primed:
            self._client.get("/Public/Search").raise_for_status()
            self._primed = True

    def search(
        self,
        *,
        company: str = "",
        license_number: str = "",
        classification_id: str = "",
    ) -> list[dict[str, str]]:
        """Run the portal search and return one parsed dict per result row."""
        self._prime()
        form: dict[str, str] = dict.fromkeys(_SEARCH_FIELDS, "")
        form["CompanyName"] = company
        form["AccountNumber"] = license_number
        form["ClassificationDefinitionIdnt"] = classification_id
        resp = self._client.post("/Public/_Search/", data=form)
        resp.raise_for_status()
        return parse_search_rows(resp.text)

    def detail(self, key: str) -> dict[str, str]:
        """Fetch and parse the account-detail dialog for a result ``key``."""
        resp = self._client.get(
            "/Public/_ShowAccountDetails/",
            params={"key": urllib.parse.unquote(key), "Source": "Search"},
        )
        resp.raise_for_status()
        return parse_detail(resp.text)

    def qualifiers(self, key: str) -> list[dict[str, str]]:
        """Fetch and parse the qualifiers table for a result ``key``."""
        resp = self._client.get(
            "/Public/_ShowAccountQualifiers/",
            params={"key": urllib.parse.unquote(key)},
        )
        resp.raise_for_status()
        return parse_qualifiers(resp.text)

    def license_record(self, company: str) -> dict[str, object] | None:
        """Search by company name and return the first match enriched with its
        detail fields and qualifiers, or None when there is no result."""
        rows = self.search(company=company)
        if not rows:
            return None
        row = rows[0]
        record: dict[str, object] = dict(row)
        record["detail"] = self.detail(row["key"]) if row["key"] else {}
        record["qualifiers"] = self.qualifiers(row["key"]) if row["key"] else []
        return record
