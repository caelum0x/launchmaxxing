from __future__ import annotations

from typing import Any

from launchmaxxing import linkcheck


class _FakeResponse:
    def __init__(self, status_code: int, url: str, history: list[Any] | None = None) -> None:
        self.status_code = status_code
        self.url = url
        self.history = history or []


class _FakeTransport:
    def __init__(self, responses: dict[str, _FakeResponse] | None = None,
                 excs: dict[str, Exception] | None = None) -> None:
        self.responses = responses or {}
        self.excs = excs or {}
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if url in self.excs:
            raise self.excs[url]
        return self.responses[url]


def _platform(**overrides: Any) -> dict[str, Any]:
    data = {"id": "product_hunt", "name": "Product Hunt", "url": "https://example.com/submit",
            "categories": ("saas",), "account_free": True, "note": "n"}
    data.update(overrides)
    return data


def test_check_one_ok_for_200() -> None:
    p = _platform()
    transport = _FakeTransport({p["url"]: _FakeResponse(200, p["url"])})
    result = linkcheck.check_one(transport, p)
    assert result.ok is True
    assert result.status_code == 200
    assert result.note == "ok"


def test_check_one_flags_404() -> None:
    p = _platform()
    transport = _FakeTransport({p["url"]: _FakeResponse(404, p["url"])})
    result = linkcheck.check_one(transport, p)
    assert result.ok is False
    assert result.status_code == 404
    assert "404" in result.note


def test_check_one_flags_5xx() -> None:
    p = _platform()
    transport = _FakeTransport({p["url"]: _FakeResponse(503, p["url"])})
    result = linkcheck.check_one(transport, p)
    assert result.ok is False
    assert "503" in result.note


def test_check_one_flags_redirect_even_when_final_status_ok() -> None:
    # The recurring real-world failure mode in this catalog: a /submit URL that
    # responds 200 only after redirecting straight to a login/sign-in page --
    # status-code-only checking would call this "ok" and miss exactly the kind of
    # stale/account-gated URL that three past changelog entries fixed by hand.
    p = _platform(url="https://example.com/submit")
    final = "https://example.com/login?callbackUrl=%2Fsubmit"
    transport = _FakeTransport({p["url"]: _FakeResponse(200, final, history=[object()])})
    result = linkcheck.check_one(transport, p)
    assert result.ok is True
    assert result.status_code == 200
    assert result.final_url == final
    assert "redirected" in result.note
    assert final in result.note


def test_check_one_reports_unreachable_on_exception() -> None:
    p = _platform()
    transport = _FakeTransport(excs={p["url"]: TimeoutError("boom")})
    result = linkcheck.check_one(transport, p)
    assert result.ok is False
    assert result.status_code is None
    assert "unreachable" in result.note
    assert "TimeoutError" in result.note


def test_check_all_checks_every_platform_in_category() -> None:
    from launchmaxxing import catalog

    responses = {p["url"]: _FakeResponse(200, p["url"]) for p in catalog.platforms_for_category("ai")}
    transport = _FakeTransport(responses)
    results = linkcheck.check_all(transport, category="ai")
    assert len(results) == len(catalog.platforms_for_category("ai"))
    assert all(r.ok for r in results)


def test_check_all_sends_a_descriptive_user_agent() -> None:
    p = _platform()
    transport = _FakeTransport({p["url"]: _FakeResponse(200, p["url"])})
    linkcheck.check_one(transport, p)
    assert "launchmaxxing" in transport.calls[0]["headers"]["User-Agent"]


def test_broken_filters_to_only_failing_results() -> None:
    ok = linkcheck.LinkCheckResult("a", "A", "https://a.example", True, 200, "https://a.example", "ok")
    bad = linkcheck.LinkCheckResult("b", "B", "https://b.example", False, 404, "https://b.example", "HTTP 404")
    assert linkcheck.broken([ok, bad]) == (bad,)
