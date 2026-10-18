from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from launchmaxxing import backlinks, cli, reddit_search


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, args: list[str]) -> int:
    state_file = str(tmp_path / "state.json")
    return cli.main([*args, "--state-file", state_file])


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0
    assert "launchmaxxing" in capsys.readouterr().out


def test_directories_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["directories", "--state-file", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert code == 0
    assert "Product Hunt" in out
    assert "18 launch director" in out


def test_directories_json_and_category_filter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["directories", "--category", "ai", "--json", "--state-file", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert code == 0
    data = json.loads(out)
    assert data["category"] == "ai"
    assert all("ai" in p["categories"] for p in data["platforms"])


def test_platform_status_then_checklist(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(None, tmp_path, ["platform-status", "Acme", "product_hunt", "submitted"]) == 0
    capsys.readouterr()
    code = _run(None, tmp_path, ["checklist", "Acme", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["done"] == 1
    assert data["platforms_submitted"] == ["product_hunt"]


def test_platform_status_rejects_unknown_platform_at_parse_time(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        _run(None, tmp_path, ["platform-status", "Acme", "not_a_real_platform", "submitted"])


def test_checklist_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["checklist", "Acme"])
    out = capsys.readouterr().out
    assert code == 0
    assert "0/10 steps done" in out
    assert "Launch everywhere" in out


def test_checklist_step_marks_done(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(None, tmp_path, ["checklist-step", "Acme", "cold_outreach", "done", "--note", "sent 20 emails"]) == 0
    capsys.readouterr()
    _run(None, tmp_path, ["checklist", "Acme", "--json"])
    data = json.loads(capsys.readouterr().out)
    step = next(s for s in data["steps"] if s["key"] == "cold_outreach")
    assert step["status"] == "done"
    assert step["note"] == "sent 20 emails"


def test_backlinks_default_fallback_no_network(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                               monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRAWLGRAPH_API_KEY", raising=False)
    monkeypatch.delenv("DATAFORSEO_LOGIN", raising=False)
    code = _run(None, tmp_path, ["backlinks", "competitor.com", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["live"] is False
    assert data["fallback_directories"]


def test_backlinks_invalid_domain_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["backlinks", "not a domain"])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_backlinks_allow_live_uses_configured_provider(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLGRAPH_API_KEY", "key")

    def fake_fetch(domain: str, *, transport: Any = None, allow_live: bool = False,
                   env: dict[str, str] | None = None) -> dict[str, Any]:
        assert allow_live is True
        return {"domain": domain, "live": True, "configured": True, "backlinks": [], "fallback_directories": [],
                "provider": "crawlgraph", "message": "ok"}

    monkeypatch.setattr(backlinks, "fetch", fake_fetch)
    code = _run(None, tmp_path, ["backlinks", "competitor.com", "--allow-live", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["live"] is True


def test_pain_points_saves_drafts_and_prints(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    thread = reddit_search.RedditThread(url="https://reddit.com/r/SaaS/x/1", title="Onboarding is painful",
                                        snippet="I keep losing users", subreddit="SaaS", upvotes=12, age_days=2)

    def fake_search(transport: Any, *, query: str, subreddits: list[str] | None = None, limit: int = 10,
                    now: float | None = None) -> list[reddit_search.RedditThread]:
        return [thread]

    monkeypatch.setattr(reddit_search, "search", fake_search)
    code = cli.main(["pain-points", "onboarding", "--product", "Acme", "--state-file", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert code == 0
    assert "Onboarding is painful" in out
    assert "Acme" in out
    assert "nothing here posts to Reddit" in out

    capsys.readouterr()
    code2 = cli.main(["drafts", "--json", "--state-file", str(tmp_path / "s.json")])
    data = json.loads(capsys.readouterr().out)
    assert code2 == 0
    assert len(data["drafts"]) == 1
    assert data["drafts"][0]["status"] == "drafted"


def test_pain_points_search_error_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_search(*args: Any, **kwargs: Any) -> list[Any]:
        raise reddit_search.RedditSearchError("rate limited", 429)

    monkeypatch.setattr(reddit_search, "search", fake_search)
    code = cli.main(["pain-points", "q", "--state-file", str(tmp_path / "s.json")])
    assert code == 1
    assert "rate limited" in capsys.readouterr().err


def test_draft_status_approve_round_trip(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    thread = reddit_search.RedditThread(url="https://reddit.com/r/SaaS/x/1", title="T", snippet="s",
                                        subreddit="SaaS", upvotes=1, age_days=0)
    monkeypatch.setattr(reddit_search, "search", lambda *a, **k: [thread])
    state_file = str(tmp_path / "s.json")
    cli.main(["pain-points", "q", "--state-file", state_file, "--json"])
    draft_id = json.loads(capsys.readouterr().out)["threads"][0].get("id")
    if not draft_id:
        drafts_out = cli.main(["drafts", "--json", "--state-file", state_file])
        draft_id = json.loads(capsys.readouterr().out)["drafts"][0]["id"]
    code = cli.main(["draft-status", draft_id, "approved", "--json", "--state-file", state_file])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["status"] == "approved"


def test_draft_status_unknown_id_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["draft-status", "missing", "approved", "--state-file", str(tmp_path / "s.json")])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_init_prints_plan_and_footer(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["init", "Acme", "--state-file", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert code == 0
    assert "Launch plan for Acme" in out
    assert "Product Hunt" in out
    assert "Menivor" in out


def test_init_json_contains_platforms_and_checklist(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["init", "Acme", "--json", "--state-file", str(tmp_path / "s.json")])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["product_name"] == "Acme"
    assert len(data["platforms"]) == 18
    assert data["checklist"]["total"] == 10
