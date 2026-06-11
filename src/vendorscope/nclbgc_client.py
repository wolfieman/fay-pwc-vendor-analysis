"""httpx client for the NCLBGC public portal (the IO shell over the pure parsers
in nclbgc_parse). The portal search is a tokenless HTTP endpoint, so acquisition
is a session cookie plus three calls — search, detail, qualifiers — with no
browser. Network IO lives here; all parsing is delegated to the pure functions.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import urllib.parse

import httpx

from vendorscope.nclbgc_parse import (
    parse_detail,
    parse_qualifiers,
    parse_search_rows,
)

_BASE = "https://portal.nclbgc.org"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{_BASE}/Public/Search",
    "Accept": "*/*",
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


class NCLBGCClient:
    """Stateful session against the NCLBGC portal. Use as a context manager."""

    def __init__(self, client: httpx.Client | None = None, timeout: float = 30.0):
        self._client = client or httpx.Client(
            base_url=_BASE, headers=_HEADERS, timeout=timeout, follow_redirects=True
        )
        self._owns_client = client is None
        self._primed = False

    def __enter__(self) -> NCLBGCClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

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
