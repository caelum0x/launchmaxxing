from __future__ import annotations

from typing import Any

import pytest

from launchmaxxing import reddit_search


class _FakeResponse:
    def __init__(self, status_code: int, body: dict[str, Any]) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> dict[str, Any]:
        return self._body


def _child(permalink: str, title: str, ups: int, created_utc: float, subreddit: str = "SaaS",
           selftext: str = "") -> dict[str, Any]:
    return {"data": {"permalink": permalink, "title": title, "ups": ups, "created_utc": created_utc,
                      "subreddit": subreddit, "selftext": selftext, "id": permalink, "num_comments": 1,
                      "author": "someone"}}


class _FakeTransport:
    def __init__(self, responses: list[_FakeResponse] | None = None, exc: Exception | None = None) -> None:
        self.responses = list(responses or [])
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.exc:
            raise self.exc
        return self.responses.pop(0)


def test_search_requires_query() -> None:
    with pytest.raises(reddit_search.RedditSearchError):
        reddit_search.search(_FakeTransport(), query="   ")


def test_search_global_builds_correct_url_and_headers() -> None:
    transport = _FakeTransport([_FakeResponse(200, {"data": {"children": []}})])
    reddit_search.search(transport, query="onboarding pain", now=1_700_000_000)
    call = transport.calls[0]
    assert call["url"] == f"{reddit_search.BASE}/search.json"
    assert call["headers"]["User-Agent"] == reddit_search.USER_AGENT
    assert call["params"]["q"] == "onboarding pain"


def test_search_restricted_to_subreddits() -> None:
    now = 1_700_000_000.0
    transport = _FakeTransport([
        _FakeResponse(200, {"data": {"children": [_child("/r/SaaS/x/1", "Thread one", 10, now - 86400)]}}),
        _FakeResponse(200, {"data": {"children": [_child("/r/startups/x/2", "Thread two", 50, now)]}}),
    ])
    threads = reddit_search.search(transport, query="churn", subreddits=["SaaS", "r/startups"], now=now)
    assert [t.url for t in threads] == [f"{reddit_search.BASE}/r/startups/x/2", f"{reddit_search.BASE}/r/SaaS/x/1"]
    assert transport.calls[0]["url"] == f"{reddit_search.BASE}/r/SaaS/search.json"
    assert transport.calls[1]["url"] == f"{reddit_search.BASE}/r/startups/search.json"


def test_search_subreddit_names_starting_with_r_are_not_mangled() -> None:
    # Regression test: subreddit normalization used to use str.lstrip("r/"), which strips any
    # leading characters in the set {"r", "/"} rather than the literal "r/" prefix -- so
    # "r/reactjs" became "eactjs" and even a bare "running" (no prefix at all) became "unning".
    now = 1_700_000_000.0
    transport = _FakeTransport([
        _FakeResponse(200, {"data": {"children": []}}),
        _FakeResponse(200, {"data": {"children": []}}),
    ])
    reddit_search.search(transport, query="q", subreddits=["r/reactjs", "running"], now=now)
    assert transport.calls[0]["url"] == f"{reddit_search.BASE}/r/reactjs/search.json"
    assert transport.calls[1]["url"] == f"{reddit_search.BASE}/r/running/search.json"


def test_search_sorts_by_upvotes_descending() -> None:
    now = 1_700_000_000.0
    transport = _FakeTransport([_FakeResponse(200, {"data": {"children": [
        _child("/r/SaaS/x/1", "Low", 2, now),
        _child("/r/SaaS/x/2", "High", 99, now),
    ]}})])
    threads = reddit_search.search(transport, query="q", now=now)
    assert [t.upvotes for t in threads] == [99, 2]


def test_search_caps_merged_results_to_requested_limit() -> None:
    # Regression test: searching multiple subreddits merges each subreddit's own results, but the
    # final cap used to be out[:max(per_sub_limit, MAX_LIMIT)] -- since per_sub_limit is always
    # <= MAX_LIMIT (25), that max() always evaluated to MAX_LIMIT, so a caller-specified --limit
    # smaller than 25 was silently ignored once results were merged across >1 subreddit (every
    # subreddit's own matches survived instead of only the requested top N overall).
    now = 1_700_000_000.0
    transport = _FakeTransport([
        _FakeResponse(200, {"data": {"children": [_child(f"/r/a/x/{i}", f"a{i}", 90 - i, now) for i in range(3)]}}),
        _FakeResponse(200, {"data": {"children": [_child(f"/r/b/x/{i}", f"b{i}", 80 - i, now) for i in range(3)]}}),
        _FakeResponse(200, {"data": {"children": [_child(f"/r/c/x/{i}", f"c{i}", 70 - i, now) for i in range(3)]}}),
    ])
    threads = reddit_search.search(transport, query="q", subreddits=["a", "b", "c"], limit=3, now=now)
    assert len(threads) == 3
    assert [t.upvotes for t in threads] == [90, 89, 88]


def test_search_dedupes_by_permalink() -> None:
    now = 1_700_000_000.0
    transport = _FakeTransport([
        _FakeResponse(200, {"data": {"children": [_child("/r/SaaS/x/1", "Dup", 5, now)]}}),
        _FakeResponse(200, {"data": {"children": [_child("/r/SaaS/x/1", "Dup", 5, now)]}}),
    ])
    threads = reddit_search.search(transport, query="q", subreddits=["SaaS", "startups"], now=now)
    assert len(threads) == 1


def test_search_rate_limited_raises_429() -> None:
    transport = _FakeTransport([_FakeResponse(429, {})])
    with pytest.raises(reddit_search.RedditSearchError) as exc_info:
        reddit_search.search(transport, query="q")
    assert exc_info.value.status_code == 429


def test_search_network_error_wrapped() -> None:
    transport = _FakeTransport(exc=ConnectionError("down"))
    with pytest.raises(reddit_search.RedditSearchError):
        reddit_search.search(transport, query="q")


def test_age_days_computed_from_created_utc() -> None:
    now = 1_700_000_000.0
    transport = _FakeTransport([_FakeResponse(200, {"data": {"children": [
        _child("/r/SaaS/x/1", "T", 1, now - 3 * 86400),
    ]}})])
    threads = reddit_search.search(transport, query="q", now=now)
    assert threads[0].age_days == 3


def test_draft_reply_mentions_product_once() -> None:
    reply = reddit_search.draft_reply("Why is onboarding so hard?", "I keep losing users on day 1.", "MyTool")
    assert "MyTool" in reply
    assert reply.count("MyTool") == 1


def test_draft_reply_handles_empty_product_name() -> None:
    reply = reddit_search.draft_reply("Title", "snippet", "")
    assert "the tool we built" in reply
