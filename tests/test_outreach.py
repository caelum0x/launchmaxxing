from __future__ import annotations

import csv
from pathlib import Path

import pytest

from launchmaxxing import content, outreach


def _profile() -> content.ProductProfile:
    return content.ProductProfile(
        name="Acme", tagline="t", problem="manual launch checklist grind",
        audience="founders and small teams", differentiator="one local CLI, no signup required",
    )


def test_draft_message_rejects_unknown_channel() -> None:
    with pytest.raises(ValueError):
        outreach.draft_message("not-a-channel", _profile())


@pytest.mark.parametrize("channel", ["creator", "press", "community", "user"])
def test_draft_message_mentions_product_for_every_channel(channel: str) -> None:
    message = outreach.draft_message(channel, _profile())
    assert "Acme" in message
    assert "manual launch checklist grind" in message or "no signup required" in message


@pytest.mark.parametrize("channel", ["creator", "press"])
def test_draft_message_mentions_audience_for_pitch_channels(channel: str) -> None:
    message = outreach.draft_message(channel, _profile())
    assert "founders and small teams" in message


def test_draft_message_uses_contact_name_when_given() -> None:
    message = outreach.draft_message("creator", _profile(), contact_name="Jane")
    assert message.startswith("Hey Jane,")


def test_draft_message_without_contact_name_uses_generic_greeting() -> None:
    message = outreach.draft_message("press", _profile())
    assert message.startswith("Hey,")


def test_draft_message_creator_mentions_video_and_payment() -> None:
    message = outreach.draft_message("creator", _profile())
    assert "video" in message.lower()


def test_draft_message_press_mentions_pitch_language() -> None:
    message = outreach.draft_message("press", _profile())
    assert "pitch" in message.lower()


def _contact_row(**overrides: str) -> dict[str, str]:
    row = {"id": "c1", "product_name": "Acme", "name": "Jane Creator", "channel": "creator", "handle": "@jane",
           "status": "contacted", "note": "likes dev tools", "created_at": "2026-10-01T00:00:00+00:00",
           "updated_at": "2026-10-02T00:00:00+00:00"}
    row.update(overrides)
    return row


def test_write_contacts_csv_writes_header_and_rows(tmp_path: Path) -> None:
    out_path = tmp_path / "contacts.csv"
    rows = [_contact_row(), _contact_row(id="c2", name="Press Co", channel="press", handle="", note="")]

    result = outreach.write_contacts_csv(rows, out_path)

    assert result == out_path
    assert out_path.is_file()
    with out_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        data_rows = list(reader)
    assert header == list(outreach.CSV_FIELDS)
    assert len(data_rows) == 2
    assert data_rows[0] == ["c1", "Acme", "Jane Creator", "creator", "@jane", "contacted", "likes dev tools",
                            "2026-10-01T00:00:00+00:00", "2026-10-02T00:00:00+00:00"]
    assert data_rows[1][0:4] == ["c2", "Acme", "Press Co", "press"]


def test_write_contacts_csv_handles_empty_rows(tmp_path: Path) -> None:
    out_path = tmp_path / "empty.csv"

    outreach.write_contacts_csv([], out_path)

    with out_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows == [list(outreach.CSV_FIELDS)]


def test_write_contacts_csv_accepts_str_path(tmp_path: Path) -> None:
    out_path = tmp_path / "contacts.csv"

    result = outreach.write_contacts_csv([_contact_row()], str(out_path))

    assert result == out_path
    assert out_path.is_file()
