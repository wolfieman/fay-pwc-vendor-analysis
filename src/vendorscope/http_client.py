"""Shared HTTP client factory (named to avoid shadowing the standard library).

A thin wrapper over ``httpx.Client`` that fixes the project defaults (a polite
identifying User-Agent, redirect following, a timeout) and accepts an injected
transport so the acquire shell can be driven by a mock in offline tests. The
caller owns the returned client and is responsible for closing it (or using it
as a context manager).

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

import httpx

DEFAULT_TIMEOUT = 60.0
USER_AGENT = "VendorScope/0.2 (public-data acquisition; see repository)"


def build_client(
    *,
    transport: httpx.BaseTransport | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> httpx.Client:
    """Build a configured client; pass ``transport`` to inject a mock in tests."""
    return httpx.Client(
        transport=transport,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
    )
