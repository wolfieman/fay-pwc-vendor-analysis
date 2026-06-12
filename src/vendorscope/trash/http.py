"""Shared HTTP scaffolding for the acquisition clients: a common User-Agent and a
context-managed httpx session that the source-specific clients build on. Only the
session boilerplate is shared here; each client keeps its own endpoints + parsing.

Copyright © 2026 Wolfgang Sanyer
Licensed under the Polyform Noncommercial License 1.0.0 (see LICENSE).
"""

from typing import Self

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)


def make_client(
    base_url: str, timeout: float = 30.0, headers: dict[str, str] | None = None
) -> httpx.Client:
    """Build an httpx.Client with the shared User-Agent and sane defaults."""
    merged = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        merged.update(headers)
    return httpx.Client(
        base_url=base_url, headers=merged, timeout=timeout, follow_redirects=True
    )


class HttpSession:
    """Context-managed wrapper that owns (or borrows) an httpx.Client.

    A borrowed client (passed in, e.g. a test transport) is left open on exit;
    only an owned client is closed.
    """

    def __init__(
        self,
        base_url: str,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ):
        self._client = client or make_client(base_url, timeout, headers)
        self._owns_client = client is None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
