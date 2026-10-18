from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from launchmaxxing import db


@pytest.fixture()
def conn(tmp_path: Path):
    connection = db.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_connect_creates_parent_dir_and_schema(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "launchmaxxing.db"
    connection = db.connect(path)
    assert path.is_file()
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"submission_events", "outreach_contacts", "content_drafts", "utm_links"} <= tables
    connection.close()


def test_default_path_uses_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAUNCHMAXXING_DB", "/tmp/custom-launchmaxxing.db")
    assert db.default_path() == Path("/tmp/custom-launchmaxxing.db")
    monkeypatch.delenv("LAUNCHMAXXING_DB")
    assert db.default_path() == db.DEFAULT_DB_PATH


def test_log_and_list_submission_events(conn) -> None:
    db.log_submission_event(conn, product_name="Acme", platform_id="product_hunt", status="submitted",
                            note="first")
    db.log_submission_event(conn, product_name="Acme", platform_id="product_hunt", status="live")
    db.log_submission_event(conn, product_name="Acme", platform_id="betalist", status="submitted")
    events = db.list_submission_events(conn, "Acme")
    assert len(events) == 3
    assert [e["status"] for e in events] == ["submitted", "live", "submitted"]

    filtered = db.list_submission_events(conn, "Acme", platform_id="product_hunt")
    assert len(filtered) == 2
    assert all(e["platform_id"] == "product_hunt" for e in filtered)


def test_list_submission_events_scoped_per_product(conn) -> None:
    db.log_submission_event(conn, product_name="Acme", platform_id="product_hunt", status="submitted")
    db.log_submission_event(conn, product_name="Other", platform_id="product_hunt", status="submitted")
    assert len(db.list_submission_events(conn, "Acme")) == 1
    assert len(db.list_submission_events(conn, "Other")) == 1


def test_add_outreach_contact_validates_channel_and_status(conn) -> None:
    with pytest.raises(ValueError):
        db.add_outreach_contact(conn, product_name="Acme", name="Jane", channel="not-a-channel")
    with pytest.raises(ValueError):
        db.add_outreach_contact(conn, product_name="Acme", name="Jane", channel="creator", status="bogus")
    with pytest.raises(ValueError):
        db.add_outreach_contact(conn, product_name="Acme", name="   ", channel="creator")


def test_add_and_list_outreach_contacts(conn) -> None:
    db.add_outreach_contact(conn, product_name="Acme", name="Jane", channel="creator", handle="@jane")
    db.add_outreach_contact(conn, product_name="Acme", name="Press Co", channel="press", status="contacted")
    all_rows = db.list_outreach_contacts(conn, product_name="Acme")
    assert len(all_rows) == 2
    contacted = db.list_outreach_contacts(conn, product_name="Acme", status="contacted")
    assert len(contacted) == 1
    assert contacted[0]["name"] == "Press Co"


def test_update_outreach_status_round_trip_and_missing(conn) -> None:
    row = db.add_outreach_contact(conn, product_name="Acme", name="Jane", channel="creator")
    updated = db.update_outreach_status(conn, row["id"], "replied", note="said yes")
    assert updated["status"] == "replied"
    assert updated["note"] == "said yes"
    with pytest.raises(ValueError):
        db.update_outreach_status(conn, row["id"], "not-a-status")
    with pytest.raises(ValueError):
        db.update_outreach_status(conn, "missing-id", "replied")


def test_update_outreach_status_keeps_note_when_not_given(conn) -> None:
    row = db.add_outreach_contact(conn, product_name="Acme", name="Jane", channel="creator", note="original")
    updated = db.update_outreach_status(conn, row["id"], "contacted")
    assert updated["note"] == "original"


def test_stale_outreach_contacts_flags_old_contacted(conn) -> None:
    row = db.add_outreach_contact(conn, product_name="Acme", name="Jane", channel="creator", status="contacted")
    now = datetime.now(timezone.utc)
    fresh = db.stale_outreach_contacts(conn, "Acme", stale_days=5, now=now)
    assert fresh == []
    later = now + timedelta(days=6)
    stale = db.stale_outreach_contacts(conn, "Acme", stale_days=5, now=later)
    assert len(stale) == 1
    assert stale[0]["id"] == row["id"]


def test_stale_outreach_contacts_ignores_replied(conn) -> None:
    row = db.add_outreach_contact(conn, product_name="Acme", name="Jane", channel="creator", status="contacted")
    db.update_outreach_status(conn, row["id"], "replied")
    later = datetime.now(timezone.utc) + timedelta(days=10)
    assert db.stale_outreach_contacts(conn, "Acme", stale_days=5, now=later) == []


def test_add_and_list_content_drafts(conn) -> None:
    db.add_content_draft(conn, product_name="Acme", platform="show_hn", body="Show HN: Acme - thing", kind="title")
    db.add_content_draft(conn, product_name="Acme", platform="twitter", body="[]")
    drafts = db.list_content_drafts(conn, product_name="Acme")
    assert len(drafts) == 2
    only_show_hn = db.list_content_drafts(conn, product_name="Acme", platform="show_hn")
    assert len(only_show_hn) == 1


def test_add_and_list_utm_links(conn) -> None:
    db.add_utm_link(conn, product_name="Acme", base_url="https://acme.example", source="producthunt",
                    medium="launch_directory", campaign="acme", full_url="https://acme.example?utm_source=x",
                    platform_id="product_hunt")
    links = db.list_utm_links(conn, product_name="Acme")
    assert len(links) == 1
    assert links[0]["platform_id"] == "product_hunt"
    assert db.list_utm_links(conn, product_name="Nobody") == []
