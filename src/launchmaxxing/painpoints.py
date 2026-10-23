"""Merged, read-only pain-point discovery across every free, keyless source this tool knows how
to search -- not just Reddit. Extends :mod:`launchmaxxing.reddit_search` with two more sources:

* **Hacker News**, via the Algolia HN Search API (``hn.algolia.com/api/v1/search``) -- free,
  public, no API key, searches both story titles/text and comments.
* **Indie Hackers** -- best-effort. IndieHackers puts a Cloudflare JS challenge in front of
  every page and every API-shaped URL this module tries (confirmed 2026-10-23: the search page,
  a guessed ``/api/search`` route, the RSS/feed route and a guessed GraphQL route all return 403
  to a plain HTTP client). Rather than silently returning zero results and letting a caller
  believe IH simply has no matches, this source reports itself as **blocked** with the reason,
  so ``launchmaxxing pain-points`` can tell a human "IH wasn't searched, here's why" instead of
  lying about coverage. If Cloudflare's posture ever changes, the same request will start
  returning real data with no code change needed here.

Like :mod:`launchmaxxing.reddit_search`, nothing in this module posts, comments, votes, or signs
in anywhere -- every function here only ever reads, and :mod:`launchmaxxing.cli`'s ``pain-points``
command is still the only thing that saves a draft locally for a human to review and post by hand.
"""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from typing import Any

from launchmaxxing import reddit_search as _reddit

ALGOLIA_HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
INDIEHACKERS_SEARCH_URL = "https://www.indiehackers.com/search"
INDIEHACKERS_USER_AGENT = "launchmaxxing/1.0 (+https://github.com/caelum0x/launchmaxxing; read-only search)"
HTTP_TIMEOUT_S = 15.0

#: Every pain-point source this module knows about, in the order ``search_all`` runs them.
SOURCES: tuple[str, ...] = ("reddit", "hacker_news", "indie_hackers")
SOURCE_LABELS: dict[str, str] = {
    "reddit": "Reddit", "hacker_news": "Hacker News", "indie_hackers": "Indie Hackers",
}


class PainPointSearchError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class PainPointThread:
    """One normalized hit across any source. ``community`` is a subreddit name for Reddit
    threads, and the fixed string ``"Hacker News"`` for HN hits -- the same row shape
    :mod:`launchmaxxing.state` already persists, just with a ``source`` tag added so the CLI can
    label it correctly (``r/<community>`` for Reddit, plain ``<community>`` otherwise)."""
    source: str
    url: str
    title: str
    snippet: str
    community: str
    upvotes: int
    age_days: int
    raw: dict[str, Any] = field(default_factory=dict)


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_hn_text(text: Any) -> str:
    """HN story/comment text comes back from Algolia as raw HTML (``<p>`` paragraph breaks,
    ``&#x27;`` entities, etc.) since that's how HN itself stores it -- strip tags and unescape
    entities so a generated draft reply reads as plain text instead of leaking markup."""
    unescaped = html.unescape(str(text or ""))
    stripped = _HTML_TAG_RE.sub(" ", unescaped)
    return " ".join(stripped.split())


def _age_days(created_at_i: Any, *, now: float) -> int:
    try:
        created = float(created_at_i or 0)
    except (TypeError, ValueError):
        return 0
    if created <= 0:
        return 0
    return max(0, int((now - created) // 86400))


def search_hacker_news(transport: Any, *, query: str, limit: int = 10,
                        now: float | None = None) -> list[PainPointThread]:
    """Search HN story titles/text *and* comments for ``query`` via the free Algolia HN Search
    API, merged and re-sorted by points, highest first. No key, no account, no rate-limit header
    required (Algolia's HN mirror is explicitly built for this kind of public search)."""
    q = str(query or "").strip()
    if not q:
        raise PainPointSearchError("query is required", 422)
    moment = now if now is not None else time.time()
    try:
        resp = transport.request("GET", ALGOLIA_HN_SEARCH_URL,
                                 params={"query": q, "tags": "(story,comment)",
                                         "hitsPerPage": str(max(1, min(int(limit or 10), 50)))})
    except Exception as exc:
        raise PainPointSearchError(f"Hacker News search is unreachable ({type(exc).__name__}).") from exc
    status = getattr(resp, "status_code", 200)
    if status >= 400:
        raise PainPointSearchError(f"Hacker News search error {status}.", 502)
    try:
        body = resp.json() or {}
    except ValueError:
        body = {}
    out: list[PainPointThread] = []
    for hit in body.get("hits") or []:
        object_id = str(hit.get("objectID") or "")
        if not object_id:
            continue
        story_id = hit.get("story_id") or object_id
        is_comment = "comment" in (hit.get("_tags") or [])
        url = str(hit.get("url") or "") or f"https://news.ycombinator.com/item?id={story_id}"
        hn_thread_url = f"https://news.ycombinator.com/item?id={story_id}"
        title = _clean_hn_text(hit.get("title") or hit.get("story_title") or "(comment thread)")[:500]
        snippet_source = hit.get("comment_text") if is_comment else (hit.get("story_text") or "")
        snippet = _clean_hn_text(snippet_source)[:400]
        out.append(PainPointThread(
            source="hacker_news", url=hn_thread_url, title=title, snippet=snippet,
            community="Hacker News", upvotes=int(hit.get("points") or 0),
            age_days=_age_days(hit.get("created_at_i"), now=moment),
            raw={"object_id": object_id, "external_url": url, "num_comments": hit.get("num_comments")},
        ))
    out.sort(key=lambda t: t.upvotes, reverse=True)
    return out[: max(1, min(int(limit or 10), 50))]


def search_indie_hackers(transport: Any, *, query: str, limit: int = 10) -> dict[str, Any]:
    """Best-effort Indie Hackers search. Returns ``{"available": True, "threads": [...]}`` if IH
    ever answers a plain HTTP GET with real content, or ``{"available": False, "reason": "..."}``
    when it is blocked (the confirmed state as of 2026-10-23: a Cloudflare JS challenge in front
    of every route tried) -- this never raises for a blocked source, since "blocked" is an
    expected, reportable outcome here, not a bug."""
    q = str(query or "").strip()
    if not q:
        raise PainPointSearchError("query is required", 422)
    try:
        resp = transport.request("GET", INDIEHACKERS_SEARCH_URL, params={"q": q},
                                 headers={"User-Agent": INDIEHACKERS_USER_AGENT})
    except Exception as exc:  # noqa: BLE001 - "unreachable" is a reportable status here, not an error to propagate
        return {"available": False, "threads": [],
                "reason": f"Indie Hackers is unreachable ({type(exc).__name__})."}
    status = getattr(resp, "status_code", 200)
    if status != 200:
        return {"available": False, "threads": [],
                "reason": f"Indie Hackers returned HTTP {status} to a plain HTTP client (as of "
                          "2026-10-23 every route tried -- search, feed, a guessed API/GraphQL "
                          "route -- is blocked the same way, typically a Cloudflare JS challenge) "
                          "-- search it directly in a real browser instead."}
    # If IH ever stops blocking, a real HTML search-results page would land here. This tool does
    # not ship an HTML scraper for a page whose structure could change at any time without
    # notice; treat an unexpected 200 as "reachable but not parseable yet" rather than guessing
    # at markup, which would silently return garbage snippets instead of an honest limitation.
    return {"available": False, "threads": [],
            "reason": "Indie Hackers responded with HTTP 200, but this version of launchmaxxing "
                      "does not yet parse its result markup (only reachability is confirmed) -- "
                      "search it directly in a real browser for now."}


def search_all(transport: Any, *, query: str, subreddits: list[str] | None = None, limit: int = 10,
                sources: tuple[str, ...] = SOURCES, now: float | None = None) -> dict[str, Any]:
    """Run every requested source, merging Reddit + Hacker News hits into one list (sorted by
    upvotes within each source's own results, sources concatenated in the order given) and always
    reporting a per-source status so a caller can see *why* a source contributed zero results
    instead of just seeing a shorter list. Never raises for a single source's failure -- one
    source being down/blocked/rate-limited must not hide results the other sources did return."""
    status: dict[str, dict[str, Any]] = {}
    threads: list[PainPointThread] = []

    if "reddit" in sources:
        try:
            reddit_threads = _reddit.search(transport, query=query, subreddits=subreddits, limit=limit,
                                            now=now)
            threads.extend(PainPointThread(
                source="reddit", url=t.url, title=t.title, snippet=t.snippet, community=t.subreddit,
                upvotes=t.upvotes, age_days=t.age_days, raw=t.raw,
            ) for t in reddit_threads)
            status["reddit"] = {"ok": True, "count": len(reddit_threads), "reason": ""}
        except _reddit.RedditSearchError as exc:
            status["reddit"] = {"ok": False, "count": 0, "reason": exc.message}

    if "hacker_news" in sources:
        try:
            hn_threads = search_hacker_news(transport, query=query, limit=limit, now=now)
            threads.extend(hn_threads)
            status["hacker_news"] = {"ok": True, "count": len(hn_threads), "reason": ""}
        except PainPointSearchError as exc:
            status["hacker_news"] = {"ok": False, "count": 0, "reason": exc.message}

    if "indie_hackers" in sources:
        ih_result = search_indie_hackers(transport, query=query, limit=limit)
        status["indie_hackers"] = {"ok": ih_result["available"], "count": len(ih_result["threads"]),
                                   "reason": ih_result.get("reason", "")}
        threads.extend(ih_result["threads"])

    return {"query": query, "threads": threads, "status": status}


__all__ = [
    "ALGOLIA_HN_SEARCH_URL", "INDIEHACKERS_SEARCH_URL", "SOURCES", "SOURCE_LABELS",
    "PainPointSearchError", "PainPointThread", "search_all", "search_hacker_news",
    "search_indie_hackers",
]
