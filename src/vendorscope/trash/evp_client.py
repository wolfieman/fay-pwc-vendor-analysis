"""eVP (NC electronic Vendor Portal) acquisition client.

The results page renders the saved search server-side and embeds the full
filtered vendor set as ``var data``, so the normal case is one browserless GET
(the IO shell over evp_parse). The filter lives on a SHARED portal search
record, so when it has drifted the client re-saves it once via Playwright — the
only time a browser is used — and retries.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import re

import httpx

from vendorscope.evp_parse import filters_applied, parse_embedded_records
from vendorscope.http import USER_AGENT, HttpSession

_BASE = "https://evp.nc.gov"
# The persistent, shared "advanced search" record (the GUID in the portal URL).
_SEARCH_RECORD_ID = "20199579-3165-f111-a824-001dd812e0a9"
_FORM_URL = f"{_BASE}/vendors/vendorsearchadvanceform/?id={_SEARCH_RECORD_ID}"
_RESULTS_URL = f"/vendors/vendordetails/?id={_SEARCH_RECORD_ID}&page=1"

# Dataverse optionset CODES (not display labels) for the default PWC-parity filter.
DEFAULT_STATUS = "1"  # eVP Status = Active
DEFAULT_CLASSIFICATION = "790550003"  # Work/License Classifications = Public Utilities
_EXPECT_SUMMARY = ("Status: Active", "WorkLicense Classifications: Public Utilities")


class EVPClient(HttpSession):
    """Fetch the filtered eVP vendor list. Use as a context manager."""

    def __init__(self, client: httpx.Client | None = None, timeout: float = 60.0):
        super().__init__(_BASE, client=client, timeout=timeout)

    def fetch_records(self, *, repair: bool = True) -> list[dict[str, str]]:
        """Return the filtered vendor records via the browserless fast path.

        Validates that the shared search record still holds the intended filters;
        if it has drifted, re-saves them once via Playwright (when ``repair``) and
        retries. Raises RuntimeError if the filters are still wrong afterwards.
        """
        page = self._results_html()
        records = parse_embedded_records(page)
        if filters_applied(page, records, _EXPECT_SUMMARY):
            return records
        if not repair:
            raise RuntimeError(
                "eVP shared search filters have drifted; rerun with repair enabled"
            )
        self.repair_filters()
        page = self._results_html()
        records = parse_embedded_records(page)
        if not filters_applied(page, records, _EXPECT_SUMMARY):
            raise RuntimeError("eVP filters still wrong after re-saving the form")
        return records

    def _results_html(self) -> str:
        resp = self._client.get(_RESULTS_URL)
        resp.raise_for_status()
        return resp.text

    def repair_filters(
        self,
        status: str = DEFAULT_STATUS,
        classification: str = DEFAULT_CLASSIFICATION,
    ) -> None:
        """Re-save the shared advanced-search record by driving the form once.

        Playwright is imported lazily: a browser launches only on drift, never on
        the fast path.
        """
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_context(user_agent=USER_AGENT).new_page()
            page.goto(_FORM_URL, wait_until="domcontentloaded")
            # "Advanced Search" is a jQuery fadeOut collapsible; the triangle icon
            # #collapseTabNameId reveals it (span.tabMargin is decorative).
            page.wait_for_selector("#collapseTabNameId", timeout=15000)
            page.click("#collapseTabNameId")
            page.wait_for_selector(
                "#evp_worklicenseclassifications", state="visible", timeout=8000
            )
            # Set the optionset CODES, not labels; select_option fires the change.
            page.select_option("#evp_vendorstatus", value=status)
            page.select_option("#evp_worklicenseclassifications", value=classification)
            page.select_option("#evp_hubcertificationstatus", value="")
            with page.expect_navigation(
                url=re.compile(r"/vendors/vendordetails/", re.I), timeout=45000
            ):
                page.click("#UpdateButton")
            browser.close()
