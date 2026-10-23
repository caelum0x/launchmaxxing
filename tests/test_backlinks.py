from __future__ import annotations

from typing import Any

import pytest

from launchmaxxing import backlinks, catalog


class _FakeResponse:
    def __init__(self, status_code: int, body: dict[str, Any]) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> dict[str, Any]:
        return self._body


class _FakeTransport:
    def __init__(self, response: _FakeResponse | None = None, exc: Exception | None = None) -> None:
        self.response = response
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.exc:
            raise self.exc
        assert self.response is not None
        return self.response


def test_fetch_rejects_bad_domain() -> None:
    with pytest.raises(backlinks.BacklinkError):
        backlinks.fetch("not a domain", env={})


def test_fetch_defaults_to_fallback_without_allow_live() -> None:
    result = backlinks.fetch("example.com", env={"CRAWLGRAPH_API_KEY": "key"})
    assert result["live"] is False
    assert result["configured"] is True
    assert result["fallback_directories"]
    assert "allow_live" in result["message"]


def test_fetch_fallback_when_not_configured() -> None:
    result = backlinks.fetch("example.com", env={})
    assert result["live"] is False
    assert result["configured"] is False
    assert result["message"] == backlinks.SETUP_STEP


def test_configured_true_with_crawlgraph_key() -> None:
    assert backlinks.configured({"CRAWLGRAPH_API_KEY": "k"}) is True
    assert backlinks.configured({}) is False


def test_configured_true_with_dataforseo_creds() -> None:
    assert backlinks.configured({"DATAFORSEO_LOGIN": "a", "DATAFORSEO_PASSWORD": "b"}) is True
    assert backlinks.configured({"DATAFORSEO_LOGIN": "a"}) is False


def test_fetch_live_crawlgraph_success() -> None:
    transport = _FakeTransport(_FakeResponse(200, {
        "results": [{"linking_domain": "blog.example.com", "cg_rank": 5, "num_hosts": 3}],
        "total_linking_domains": 1, "cg_authority": 42,
    }))
    result = backlinks.fetch("example.com", transport=transport, allow_live=True,
                             env={"CRAWLGRAPH_API_KEY": "key"})
    assert result["live"] is True
    assert result["provider"] == "crawlgraph"
    assert result["backlinks"][0]["source_domain"] == "blog.example.com"
    assert transport.calls[0]["method"] == "POST"


def test_fetch_live_crawlgraph_error_status() -> None:
    transport = _FakeTransport(_FakeResponse(500, {}))
    with pytest.raises(backlinks.BacklinkError):
        backlinks.fetch("example.com", transport=transport, allow_live=True, env={"CRAWLGRAPH_API_KEY": "key"})


def test_fetch_live_crawlgraph_network_error() -> None:
    transport = _FakeTransport(exc=ConnectionError("boom"))
    with pytest.raises(backlinks.BacklinkError):
        backlinks.fetch("example.com", transport=transport, allow_live=True, env={"CRAWLGRAPH_API_KEY": "key"})


def test_fetch_live_prefers_crawlgraph_over_dataforseo() -> None:
    transport = _FakeTransport(_FakeResponse(200, {"results": []}))
    result = backlinks.fetch(
        "example.com", transport=transport, allow_live=True,
        env={"CRAWLGRAPH_API_KEY": "key", "DATAFORSEO_LOGIN": "l", "DATAFORSEO_PASSWORD": "p"},
    )
    assert result["provider"] == "crawlgraph"


def test_fetch_live_dataforseo_success() -> None:
    transport = _FakeTransport(_FakeResponse(200, {
        "tasks": [{"result": [{"items": [{"domain_from": "ref.example", "url_to": "https://x", "anchor": "a",
                                           "rank": 10}]}]}],
    }))
    result = backlinks.fetch("example.com", transport=transport, allow_live=True,
                             env={"DATAFORSEO_LOGIN": "login", "DATAFORSEO_PASSWORD": "pass"})
    assert result["provider"] == "dataforseo"
    assert result["backlinks"][0]["source_domain"] == "ref.example"


def test_fetch_strips_scheme_and_trailing_slash() -> None:
    result = backlinks.fetch("https://Example.com/", env={})
    assert result["domain"] == "example.com"


def test_fetch_fallback_narrows_by_category() -> None:
    result = backlinks.fetch("example.com", env={}, category="oss")
    oss_ids = {p["id"] for p in catalog.platforms_for_category("oss")}
    assert result["category"] == "oss"
    assert {row["id"] for row in result["fallback_directories"]} == oss_ids
    assert len(result["fallback_directories"]) < len(catalog.PLATFORMS)


def test_fetch_fallback_narrows_by_account_free() -> None:
    result = backlinks.fetch("example.com", env={}, account_free_only=True)
    free_ids = {p["id"] for p in catalog.platforms_account_free(catalog.PLATFORMS)}
    assert result["account_free_only"] is True
    assert {row["id"] for row in result["fallback_directories"]} == free_ids
    assert len(result["fallback_directories"]) < len(catalog.PLATFORMS)


def test_fetch_fallback_category_and_account_free_combine() -> None:
    result = backlinks.fetch("example.com", env={}, category="saas", account_free_only=True)
    expected = {p["id"] for p in catalog.platforms_account_free(catalog.platforms_for_category("saas"))}
    assert {row["id"] for row in result["fallback_directories"]} == expected


def test_fetch_live_ignores_category_and_account_free() -> None:
    transport = _FakeTransport(_FakeResponse(200, {"results": []}))
    result = backlinks.fetch("example.com", transport=transport, allow_live=True,
                             env={"CRAWLGRAPH_API_KEY": "key"}, category="oss", account_free_only=True)
    assert result["live"] is True
    assert result["fallback_directories"] == []
