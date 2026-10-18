from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from launchmaxxing import db, state, track


@pytest.fixture()
def conn(tmp_path: Path):
    connection = db.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def _state_with_age(product: str, days_old: int) -> dict:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_step_status(app_state, product_name=product, step_key="cold_outreach", status="pending")
    created = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
    app_state["products"][product]["created_at"] = created
    return app_state


def test_build_requires_product_name(conn) -> None:
    with pytest.raises(ValueError):
        track.build({"products": {}, "pain_point_drafts": []}, conn, "   ")


def test_build_new_product_has_no_age_and_no_stale_flags(conn) -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    result = track.build(app_state, conn, "Acme")
    assert result["age_days"] is None
    assert result["directories"]["stale"] == []
    assert result["directories"]["not_started"] == result["directories"]["total"]


def test_build_flags_stale_directories_after_threshold(conn) -> None:
    app_state = _state_with_age("Acme", days_old=10)
    result = track.build(app_state, conn, "Acme", stale_days=5)
    assert result["age_days"] == 10
    assert len(result["directories"]["stale"]) == result["directories"]["total"]


def test_build_does_not_flag_directories_before_threshold(conn) -> None:
    app_state = _state_with_age("Acme", days_old=2)
    result = track.build(app_state, conn, "Acme", stale_days=5)
    assert result["directories"]["stale"] == []


def test_build_submitted_directory_is_not_flagged_stale(conn) -> None:
    app_state = _state_with_age("Acme", days_old=10)
    state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="submitted")
    result = track.build(app_state, conn, "Acme", stale_days=5)
    stale_ids = {p["id"] for p in result["directories"]["stale"]}
    assert "product_hunt" not in stale_ids
    assert result["directories"]["submitted_or_live"] == 1


def test_build_includes_checklist_progress(conn) -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_step_status(app_state, product_name="Acme", step_key="cold_outreach", status="done")
    result = track.build(app_state, conn, "Acme")
    assert result["checklist"]["done"] == 1
    assert result["checklist"]["total"] == 10


def test_build_outreach_summary_and_stale_followups(conn) -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    row = db.add_outreach_contact(conn, product_name="Acme", name="Jane", channel="creator", status="contacted")
    later = datetime.now(timezone.utc) + timedelta(days=10)
    result = track.build(app_state, conn, "Acme", stale_days=5, now=later)
    assert result["outreach"]["total"] == 1
    assert result["outreach"]["by_status"] == {"contacted": 1}
    assert result["outreach"]["stale_followups"][0]["id"] == row["id"]


def test_build_counts_content_drafts_and_utm_links(conn) -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    db.add_content_draft(conn, product_name="Acme", platform="show_hn", body="x")
    db.add_utm_link(conn, product_name="Acme", base_url="https://acme.example", source="s", medium="m",
                    campaign="c", full_url="https://acme.example?utm_source=s")
    result = track.build(app_state, conn, "Acme")
    assert result["content_drafts"] == 1
    assert result["utm_links"] == 1


def test_build_handles_corrupt_created_at_gracefully(conn) -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_step_status(app_state, product_name="Acme", step_key="cold_outreach", status="pending")
    app_state["products"]["Acme"]["created_at"] = "not-a-real-timestamp"
    result = track.build(app_state, conn, "Acme")
    assert result["age_days"] is None


def test_build_is_scoped_per_product(conn) -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    db.add_outreach_contact(conn, product_name="Other", name="Jane", channel="creator")
    result = track.build(app_state, conn, "Acme")
    assert result["outreach"]["total"] == 0
