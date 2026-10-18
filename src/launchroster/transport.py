"""The tiny HTTP transport interface :mod:`launchroster.backlinks` and
:mod:`launchroster.reddit_search` depend on, so tests can swap in a fake
without a real network call. A transport only needs a ``request`` method
that returns an object with a ``.status_code`` and a ``.json()`` method --
:class:`requests.Response` already satisfies this, which is what
:class:`RequestsTransport` uses.
"""

from __future__ import annotations

from typing import Any, Protocol


class Transport(Protocol):
    def request(self, method: str, url: str, *, params: dict[str, Any] | None = None,
                headers: dict[str, str] | None = None, json: Any = None) -> Any: ...


class RequestsTransport:
    """Default transport: a thin wrapper around the ``requests`` library."""

    def __init__(self, timeout_s: float = 15.0) -> None:
        self.timeout_s = timeout_s

    def request(self, method: str, url: str, *, params: dict[str, Any] | None = None,
                headers: dict[str, str] | None = None, json: Any = None) -> Any:
        import requests

        return requests.request(method, url, params=params, headers=headers, json=json, timeout=self.timeout_s)


__all__ = ["RequestsTransport", "Transport"]
