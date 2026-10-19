from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from launchmaxxing import backlinks, cli, db, outreach, reddit_search, utm


def _run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, args: list[str]) -> int:
    state_file = str(tmp_path / "state.json")
    db_file = str(tmp_path / "launchmaxxing.db")
    return cli.main([*args, "--state-file", state_file, "--db-file", db_file])


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
    assert "24 launch director" in out


def test_directories_json_and_category_filter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["directories", "--category", "ai", "--json", "--state-file", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert code == 0
    data = json.loads(out)
    assert data["category"] == "ai"
    assert all("ai" in p["categories"] for p in data["platforms"])


def test_directories_account_free_filter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["directories", "--account-free", "--json", "--state-file", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert code == 0
    data = json.loads(out)
    assert data["platforms"]
    assert all(p["account_free"] for p in data["platforms"])
    assert not any(p["id"] in ("devhunt", "uneed", "turbo0") for p in data["platforms"])


def test_directories_account_free_combines_with_category(tmp_path: Path,
                                                          capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["directories", "--category", "ai", "--account-free", "--json",
                     "--state-file", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert code == 0
    data = json.loads(out)
    assert data["platforms"]
    assert all(p["account_free"] and "ai" in p["categories"] for p in data["platforms"])


def test_directories_account_free_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = cli.main(["directories", "--account-free", "--state-file", str(tmp_path / "s.json")])
    out = capsys.readouterr().out
    assert code == 0
    assert "account-free only" in out


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


def test_checklist_step_blank_product_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["checklist-step", "   ", "cold_outreach", "done"])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_platform_status_blank_product_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["platform-status", "   ", "product_hunt", "submitted"])
    assert code == 1
    assert "error" in capsys.readouterr().err


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
        cli.main(["drafts", "--json", "--state-file", state_file])
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
    assert len(data["platforms"]) == 24
    assert data["checklist"]["total"] == 10


# --------------------------------------------------------------------------- #
# submit (new primary command) + history
# --------------------------------------------------------------------------- #
def test_submit_records_status_same_as_platform_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["submit", "Acme", "product_hunt", "submitted", "--note", "launched"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["status"] == "submitted"
    assert data["note"] == "launched"


def test_submit_without_history_or_status_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["submit", "Acme"])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_submit_history_shows_every_event(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["submit", "Acme", "product_hunt", "submitted"])
    capsys.readouterr()
    _run(None, tmp_path, ["submit", "Acme", "product_hunt", "live"])
    capsys.readouterr()
    code = _run(None, tmp_path, ["submit", "Acme", "--history", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert len(data["events"]) == 2
    assert [e["status"] for e in data["events"]] == ["submitted", "live"]


def test_submit_history_filters_by_platform(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["submit", "Acme", "product_hunt", "submitted"])
    capsys.readouterr()
    _run(None, tmp_path, ["submit", "Acme", "betalist", "submitted"])
    capsys.readouterr()
    code = _run(None, tmp_path, ["submit", "Acme", "product_hunt", "--history", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert len(data["events"]) == 1
    assert data["events"][0]["platform_id"] == "product_hunt"


def test_submit_history_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["submit", "Acme", "product_hunt", "submitted", "--note", "launch day"])
    capsys.readouterr()
    code = _run(None, tmp_path, ["submit", "Acme", "--history"])
    out = capsys.readouterr().out
    assert code == 0
    assert "submission event(s) for Acme" in out
    assert "product_hunt -> submitted (launch day)" in out


def test_submit_history_text_output_scoped_to_platform(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["submit", "Acme", "product_hunt", "submitted"])
    capsys.readouterr()
    code = _run(None, tmp_path, ["submit", "Acme", "product_hunt", "--history"])
    out = capsys.readouterr().out
    assert code == 0
    assert "/ product_hunt" in out


# --------------------------------------------------------------------------- #
# content
# --------------------------------------------------------------------------- #
_PROFILE_FLAGS = [
    "--tagline", "Launch copy in one command",
    "--problem", "Founders waste hours retyping launch copy for every directory",
    "--audience", "founders and small teams launching SaaS",
    "--differentiator", "generates platform-correct copy locally, no API key",
]


def test_content_product_hunt_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["content", "Acme", "product_hunt", *_PROFILE_FLAGS, "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["tagline"]["length"] <= 60


def test_content_all_platforms_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["content", "Acme", "all", *_PROFILE_FLAGS])
    out = capsys.readouterr().out
    assert code == 0
    assert "=== product_hunt ===" in out
    assert "=== show_hn ===" in out
    assert "=== twitter ===" in out


def test_content_twitter_platform_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["content", "Acme", "twitter", *_PROFILE_FLAGS])
    out = capsys.readouterr().out
    assert code == 0
    assert "1. " in out


def test_content_reddit_platform_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["content", "Acme", "reddit", *_PROFILE_FLAGS])
    out = capsys.readouterr().out
    assert code == 0
    assert "Title:" in out


def test_content_linkedin_platform_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["content", "Acme", "linkedin", *_PROFILE_FLAGS])
    out = capsys.readouterr().out
    assert code == 0
    assert "Acme" in out


def test_content_tagline_with_hype_words_shown_in_text_mode(tmp_path: Path,
                                                            capsys: pytest.CaptureFixture[str]) -> None:
    flags = ["--tagline", "The most revolutionary launch tool", "--problem", "p", "--audience", "a",
             "--differentiator", "d"]
    code = _run(None, tmp_path, ["content", "Acme", "product_hunt", *flags])
    out = capsys.readouterr().out
    assert code == 0
    assert "hype words to reconsider" in out


def test_content_save_all_platforms_persists_every_draft(tmp_path: Path,
                                                          capsys: pytest.CaptureFixture[str]) -> None:
    db_file = str(tmp_path / "launchmaxxing.db")
    code = cli.main(["content", "Acme", "all", *_PROFILE_FLAGS, "--save", "--db-file", db_file,
                     "--state-file", str(tmp_path / "s.json")])
    assert code == 0
    conn = db.connect(Path(db_file))
    try:
        drafts = db.list_content_drafts(conn, product_name="Acme")
    finally:
        conn.close()
    assert len(drafts) == 5


def test_content_profile_file_not_a_json_object_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile_path = tmp_path / "bad.json"
    profile_path.write_text("[1, 2, 3]", encoding="utf-8")
    code = _run(None, tmp_path, ["content", "Acme", "product_hunt", "--profile-file", str(profile_path)])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_content_missing_required_field_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["content", "Acme", "product_hunt", "--tagline", "x"])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_content_profile_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({
        "tagline": "Launch copy in one command", "problem": "manual launch copy grind",
        "audience": "founders", "differentiator": "local templating, no API key",
    }), encoding="utf-8")
    code = _run(None, tmp_path, ["content", "Acme", "show_hn", "--profile-file", str(profile_path), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["text"].startswith("Show HN: Acme")


def test_content_save_persists_draft(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db_file = str(tmp_path / "launchmaxxing.db")
    code = cli.main(["content", "Acme", "show_hn", *_PROFILE_FLAGS, "--save", "--db-file", db_file,
                     "--state-file", str(tmp_path / "s.json")])
    assert code == 0
    conn = db.connect(Path(db_file))
    try:
        drafts = db.list_content_drafts(conn, product_name="Acme")
    finally:
        conn.close()
    assert len(drafts) == 1
    assert drafts[0]["platform"] == "show_hn"


# --------------------------------------------------------------------------- #
# outreach
# --------------------------------------------------------------------------- #
def test_outreach_add_list_and_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["outreach", "add", "Acme", "Jane Creator", "creator", "--handle", "@jane",
                                 "--json"])
    row = json.loads(capsys.readouterr().out)
    assert code == 0
    assert row["status"] == "not_contacted"

    code2 = _run(None, tmp_path, ["outreach", "list", "Acme", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code2 == 0
    assert len(data["contacts"]) == 1

    code3 = _run(None, tmp_path, ["outreach", "status", row["id"], "replied", "--json"])
    updated = json.loads(capsys.readouterr().out)
    assert code3 == 0
    assert updated["status"] == "replied"


def test_outreach_status_unknown_id_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["outreach", "status", "missing-id", "replied"])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_outreach_list_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["outreach", "add", "Acme", "Jane Creator", "creator", "--handle", "@jane",
                          "--note", "likes dev tools"])
    capsys.readouterr()
    code = _run(None, tmp_path, ["outreach", "list", "Acme"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Jane Creator" in out
    assert "@jane" in out
    assert "likes dev tools" in out


def test_outreach_list_csv_writes_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["outreach", "add", "Acme", "Jane Creator", "creator", "--handle", "@jane",
                          "--note", "likes dev tools"])
    capsys.readouterr()
    csv_path = tmp_path / "contacts.csv"
    code = _run(None, tmp_path, ["outreach", "list", "Acme", "--csv", str(csv_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert csv_path.is_file()
    assert f"Wrote 1 outreach contact(s) to {csv_path}" in out
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    assert header == list(outreach.CSV_FIELDS)
    assert len(rows) == 1
    assert rows[0][outreach.CSV_FIELDS.index("name")] == "Jane Creator"
    assert rows[0][outreach.CSV_FIELDS.index("handle")] == "@jane"
    assert rows[0][outreach.CSV_FIELDS.index("note")] == "likes dev tools"


def test_outreach_list_csv_takes_precedence_over_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["outreach", "add", "Acme", "Jane Creator", "creator"])
    capsys.readouterr()
    csv_path = tmp_path / "contacts.csv"
    code = _run(None, tmp_path, ["outreach", "list", "Acme", "--csv", str(csv_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "outreach contact(s) for Acme:" not in out


def test_outreach_add_rejects_blank_name(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["outreach", "add", "Acme", "   ", "creator"])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_outreach_draft_prints_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["outreach", "draft", "Acme", "creator", *_PROFILE_FLAGS])
    out = capsys.readouterr().out
    assert code == 0
    assert "Acme" in out


def test_outreach_draft_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["outreach", "draft", "Acme", "creator", *_PROFILE_FLAGS, "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["channel"] == "creator"
    assert "Acme" in data["message"]


def test_outreach_draft_missing_profile_field_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["outreach", "draft", "Acme", "creator", "--tagline", "x"])
    assert code == 1
    assert "error" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# utm
# --------------------------------------------------------------------------- #
def test_utm_build_and_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["utm", "build", "Acme", "https://acme.example", "--platform-id",
                                 "product_hunt", "--json"])
    row = json.loads(capsys.readouterr().out)
    assert code == 0
    assert row["source"] == "producthunt"
    assert "utm_campaign=acme" in row["full_url"]

    code2 = _run(None, tmp_path, ["utm", "list", "Acme", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code2 == 0
    assert len(data["links"]) == 1


def test_utm_build_custom_campaign_and_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["utm", "build", "Acme", "https://acme.example", "--source", "newsletter",
                                 "--medium", "email", "--campaign", "week1", "--json"])
    row = json.loads(capsys.readouterr().out)
    assert code == 0
    assert row["source"] == "newsletter"
    assert row["campaign"] == "week1"


def test_utm_build_rejects_blank_base_url(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["utm", "build", "Acme", "   "])
    assert code == 1
    assert "error" in capsys.readouterr().err


def test_utm_list_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["utm", "build", "Acme", "https://acme.example"])
    capsys.readouterr()
    code = _run(None, tmp_path, ["utm", "list", "Acme"])
    out = capsys.readouterr().out
    assert code == 0
    assert "UTM link(s) for Acme" in out
    assert "acme.example" in out


def test_utm_list_csv_writes_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["utm", "build", "Acme", "https://acme.example", "--platform-id", "product_hunt"])
    capsys.readouterr()
    csv_path = tmp_path / "links.csv"
    code = _run(None, tmp_path, ["utm", "list", "Acme", "--csv", str(csv_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert csv_path.is_file()
    assert f"Wrote 1 UTM link(s) to {csv_path}" in out
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    assert header == list(utm.CSV_FIELDS)
    assert len(rows) == 1
    assert rows[0][utm.CSV_FIELDS.index("source")] == "producthunt"
    assert "acme.example" in rows[0][utm.CSV_FIELDS.index("full_url")]


def test_utm_list_csv_takes_precedence_over_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["utm", "build", "Acme", "https://acme.example"])
    capsys.readouterr()
    csv_path = tmp_path / "links.csv"
    code = _run(None, tmp_path, ["utm", "list", "Acme", "--csv", str(csv_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "UTM link(s) for Acme:" not in out


# --------------------------------------------------------------------------- #
# track
# --------------------------------------------------------------------------- #
def test_track_json_reports_directories_and_checklist(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["submit", "Acme", "product_hunt", "submitted"])
    capsys.readouterr()
    code = _run(None, tmp_path, ["track", "Acme", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["directories"]["submitted_or_live"] == 1
    assert data["checklist"]["total"] == 10


def test_track_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["track", "Acme"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Launch status for Acme" in out
    assert "Directories:" in out
    assert "Checklist:" in out


def test_track_text_output_shows_stale_directories_and_followups(tmp_path: Path,
                                                                  capsys: pytest.CaptureFixture[str]) -> None:
    _run(None, tmp_path, ["checklist-step", "Acme", "cold_outreach", "pending"])
    capsys.readouterr()
    _run(None, tmp_path, ["outreach", "add", "Acme", "Jane Creator", "creator", "--status", "contacted"])
    capsys.readouterr()
    code = _run(None, tmp_path, ["track", "Acme", "--stale-days", "0"])
    out = capsys.readouterr().out
    assert code == 0
    assert "overdue" in out
    assert "awaiting follow-up" in out
    assert "Jane Creator" in out


def test_track_blank_product_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["track", "   "])
    assert code == 1
    assert "error" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def test_report_prints_markdown_by_default(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["report", "Acme"])
    out = capsys.readouterr().out
    assert code == 0
    assert "# Launch report: Acme" in out


def test_report_writes_to_file_with_out_flag(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out_file = tmp_path / "report.md"
    code = _run(None, tmp_path, ["report", "Acme", "--out", str(out_file)])
    assert code == 0
    assert out_file.is_file()
    assert "# Launch report: Acme" in out_file.read_text(encoding="utf-8")


def test_report_json_mode_returns_dashboard(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["report", "Acme", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert data["product_name"] == "Acme"


def test_report_blank_product_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = _run(None, tmp_path, ["report", "   "])
    assert code == 1
    assert "error" in capsys.readouterr().err
