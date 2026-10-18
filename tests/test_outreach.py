from __future__ import annotations

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
