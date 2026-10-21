"""Live reachability check for every launch directory's submit URL
(``launchmaxxing directories --check-links``).

This catalog's own accuracy is the tool's core promise -- three separate
changelog entries (0.1.0 -> 0.2.1, and 0.2.1 -> 0.2.2) were fixes for stale
submit URLs or wrong ``account_free`` tags, and every one of them was found
only because someone manually tried to submit and hit a 404 or an
unexpected login wall. This module automates that first check: a plain,
read-only HTTP GET against every catalog URL (no login, no JS execution --
so it cannot see client-side-only submit forms; the catalog's own notes
already call those cases out) that reports exactly what a human would hit
first: a dead link, a server error, or a redirect to a login/sign-in page.

Like :mod:`launchmaxxing.reddit_search`, this never writes anything and
never needs an API key, so it runs directly -- no ``--allow-live`` gate --
whenever a caller passes a transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from launchmaxxing import catalog

USER_AGENT = "launchmaxxing/1.0 (+https://github.com/caelum0x/launchmaxxing; link-check)"


@dataclass(frozen=True)
class LinkCheckResult:
    platform_id: str
    name: str
    url: str
    ok: bool
    status_code: int | None
    final_url: str
    note: str


def check_one(transport: Any, platform: dict[str, Any]) -> LinkCheckResult:
    """Check one catalog entry's submit URL. ``ok`` is True only for a response under 400 --
    a redirect that still lands on a 2xx/3xx page is reported as ``ok`` but flagged in ``note``
    with its real destination, since "redirects to a login page" is the single most common way
    this catalog has gone stale (see module docstring)."""
    url = platform["url"]
    try:
        resp = transport.request("GET", url, headers={"User-Agent": USER_AGENT})
    except Exception as exc:
        return LinkCheckResult(platform["id"], platform["name"], url, False, None, url,
                                f"unreachable ({type(exc).__name__})")
    status = getattr(resp, "status_code", 0) or 0
    final_url = str(getattr(resp, "url", "") or url)
    redirected = bool(getattr(resp, "history", None)) or final_url.rstrip("/") != url.rstrip("/")
    if status >= 400:
        return LinkCheckResult(platform["id"], platform["name"], url, False, status, final_url,
                                f"HTTP {status}")
    note = f"redirected to {final_url}" if redirected else "ok"
    return LinkCheckResult(platform["id"], platform["name"], url, True, status, final_url, note)


def check_all(transport: Any, *, category: str | None = None) -> list[LinkCheckResult]:
    """Check every catalog entry, or only the ones tagged with ``category``."""
    return [check_one(transport, p) for p in catalog.platforms_for_category(category)]


def broken(results: list[LinkCheckResult]) -> tuple[LinkCheckResult, ...]:
    """The subset of ``results`` that failed outright (not merely redirected)."""
    return tuple(r for r in results if not r.ok)


__all__ = ["USER_AGENT", "LinkCheckResult", "broken", "check_all", "check_one"]
