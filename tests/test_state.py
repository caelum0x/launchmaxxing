from __future__ import annotations

from pathlib import Path

import pytest

from launchmaxxing import state


def test_load_missing_file_returns_empty_state(tmp_path: Path) -> None:
    result = state.load(tmp_path / "nope.json")
    assert result == {"products": {}, "pain_point_drafts": []}


def test_load_corrupt_file_returns_empty_state(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    path.write_text("not json{{", encoding="utf-8")
    assert state.load(path) == {"products": {}, "pain_point_drafts": []}


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "state.json"
    app_state = state.load(path)
    state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="submitted")
    state.save(app_state, path)
    reloaded = state.load(path)
    assert reloaded["products"]["Acme"]["platforms"]["product_hunt"]["status"] == "submitted"


def test_set_platform_status_rejects_unknown_platform() -> None:
    app_state = state.load(Path("/nonexistent"))
    with pytest.raises(ValueError):
        state.set_platform_status(app_state, product_name="Acme", platform_id="not_real", status="submitted")


def test_set_platform_status_rejects_bad_status() -> None:
    app_state = state.load(Path("/nonexistent"))
    with pytest.raises(ValueError):
        state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="bogus")


def test_set_platform_status_sets_submitted_at_once() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    row = state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="submitted")
    assert row["submitted_at"] is not None
    first_submitted_at = row["submitted_at"]
    row2 = state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="live")
    assert row2["submitted_at"] == first_submitted_at


def test_set_platform_status_not_started_clears_submitted_at() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="live")
    row = state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="not_started")
    assert row["submitted_at"] is None


def test_get_platform_statuses_empty_for_unknown_product() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    assert state.get_platform_statuses(app_state, "Nobody") == {}


def test_set_step_status_rejects_unknown_step() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    with pytest.raises(ValueError):
        state.set_step_status(app_state, product_name="Acme", step_key="not_real", status="done")


def test_set_step_status_round_trips() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_step_status(app_state, product_name="Acme", step_key="cold_outreach", status="done", note="emailed 20")
    row = state.get_step_statuses(app_state, "Acme")["cold_outreach"]
    assert row["status"] == "done"
    assert row["note"] == "emailed 20"


def test_product_name_required() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    with pytest.raises(ValueError):
        state.set_step_status(app_state, product_name="   ", step_key="cold_outreach", status="done")


def test_add_pain_point_drafts_dedupes_by_url_and_query() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    threads = [{"thread_url": "https://reddit.com/x/1", "thread_title": "T", "snippet": "s", "subreddit": "SaaS",
                "upvotes": 5, "age_days": 1, "draft_reply": "r"}]
    first = state.add_pain_point_drafts(app_state, query="q", product_name="Acme", threads=threads)
    second = state.add_pain_point_drafts(app_state, query="q", product_name="Acme", threads=threads)
    assert len(first) == 1
    assert len(second) == 1
    assert len(app_state["pain_point_drafts"]) == 1


def test_list_pain_point_drafts_filters_by_status_and_product() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    threads = [{"thread_url": "https://reddit.com/x/1", "thread_title": "T", "snippet": "s", "subreddit": "SaaS",
                "upvotes": 5, "age_days": 1, "draft_reply": "r"}]
    state.add_pain_point_drafts(app_state, query="q", product_name="Acme", threads=threads)
    assert len(state.list_pain_point_drafts(app_state, status="drafted")) == 1
    assert len(state.list_pain_point_drafts(app_state, status="approved")) == 0
    assert len(state.list_pain_point_drafts(app_state, product_name="Other")) == 0


def test_set_draft_status_updates_and_rejects_bad_status() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    threads = [{"thread_url": "https://reddit.com/x/1", "thread_title": "T", "snippet": "s", "subreddit": "SaaS",
                "upvotes": 5, "age_days": 1, "draft_reply": "r"}]
    [draft] = state.add_pain_point_drafts(app_state, query="q", product_name="Acme", threads=threads)
    updated = state.set_draft_status(app_state, draft["id"], "approved")
    assert updated["status"] == "approved"
    with pytest.raises(ValueError):
        state.set_draft_status(app_state, draft["id"], "posted")
    with pytest.raises(ValueError):
        state.set_draft_status(app_state, "missing-id", "approved")


def test_default_path_uses_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAUNCHMAXXING_STATE", "/tmp/custom-state.json")
    assert state.default_path() == Path("/tmp/custom-state.json")
    monkeypatch.delenv("LAUNCHMAXXING_STATE")
    assert state.default_path() == state.DEFAULT_STATE_PATH


def test_get_product_created_at_set_on_first_touch() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    assert state.get_product_created_at(app_state, "Acme") is None
    state.set_step_status(app_state, product_name="Acme", step_key="cold_outreach", status="pending")
    created_at = state.get_product_created_at(app_state, "Acme")
    assert created_at is not None


def test_get_product_created_at_stable_across_updates() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_step_status(app_state, product_name="Acme", step_key="cold_outreach", status="pending")
    first = state.get_product_created_at(app_state, "Acme")
    state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="submitted")
    second = state.get_product_created_at(app_state, "Acme")
    assert first == second
