from __future__ import annotations

import pytest

from launchmaxxing import content


def _profile(**overrides: str) -> content.ProductProfile:
    data = {
        "name": "Acme",
        "tagline": "Launch copy in one command",
        "problem": "Founders waste hours retyping launch copy for every directory.",
        "audience": "founders and small teams launching SaaS",
        "differentiator": "generates platform-correct copy locally, no API key required",
        "url": "https://acme.example",
    }
    data.update(overrides)
    return content.ProductProfile(**data)


def test_profile_requires_all_core_fields() -> None:
    with pytest.raises(ValueError):
        content.ProductProfile(name="", tagline="t", problem="p", audience="a", differentiator="d")
    with pytest.raises(ValueError):
        content.ProductProfile(name="Acme", tagline="", problem="p", audience="a", differentiator="d")
    with pytest.raises(ValueError):
        content.ProductProfile(name="Acme", tagline="t", problem="", audience="a", differentiator="d")
    with pytest.raises(ValueError):
        content.ProductProfile(name="Acme", tagline="t", problem="p", audience="", differentiator="d")
    with pytest.raises(ValueError):
        content.ProductProfile(name="Acme", tagline="t", problem="p", audience="a", differentiator="")


def test_product_hunt_tagline_enforces_60_char_limit() -> None:
    long_tagline = "x" * 120
    result = content.product_hunt_tagline(_profile(tagline=long_tagline))
    assert result["length"] <= content.PRODUCT_HUNT_TAGLINE_MAX
    assert result["text"].endswith("…")


def test_product_hunt_tagline_flags_hype_words() -> None:
    result = content.product_hunt_tagline(_profile(tagline="The most revolutionary launch tool"))
    assert "revolutionary" in result["hype_words"]


def test_product_hunt_tagline_no_hype_words_when_clean() -> None:
    result = content.product_hunt_tagline(_profile())
    assert result["hype_words"] == ()


def test_product_hunt_description_within_limit() -> None:
    result = content.product_hunt_description(_profile())
    assert result["length"] <= content.PRODUCT_HUNT_DESCRIPTION_MAX
    assert "Acme" in result["text"]


def test_product_hunt_description_truncates_long_inputs() -> None:
    profile = _profile(problem="p" * 300, differentiator="d" * 300)
    result = content.product_hunt_description(profile)
    assert result["length"] <= content.PRODUCT_HUNT_DESCRIPTION_MAX


def test_show_hn_title_format_and_limit() -> None:
    result = content.show_hn_title(_profile())
    assert result["text"].startswith("Show HN: Acme – ")
    assert result["length"] <= content.SHOW_HN_TITLE_MAX


def test_show_hn_title_strips_hype_words_without_stray_punctuation() -> None:
    profile = _profile(differentiator="This is a Revolutionary, game-changing tool that does local generation")
    result = content.show_hn_title(profile)
    assert "revolutionary" not in result["text"].lower()
    assert "game-changing" not in result["text"].lower()
    assert ",," not in result["text"]
    assert "  " not in result["text"]


def test_show_hn_title_handles_very_long_name_and_differentiator() -> None:
    profile = _profile(name="A" * 50, differentiator="d" * 200)
    result = content.show_hn_title(profile)
    assert result["length"] <= content.SHOW_HN_TITLE_MAX
    assert result["text"].startswith("Show HN:")


def test_twitter_launch_thread_has_multiple_tweets_and_mentions_url() -> None:
    thread = content.twitter_launch_thread(_profile())
    assert len(thread) >= 5
    assert any("acme.example" in tweet for tweet in thread)
    assert any("Acme" in tweet for tweet in thread)


def test_twitter_launch_thread_without_url_has_no_link() -> None:
    thread = content.twitter_launch_thread(_profile(url=""))
    assert not any("http" in tweet for tweet in thread)


def test_reddit_post_leads_with_problem_and_mentions_product_once() -> None:
    result = content.reddit_post(_profile(subreddit="SaaS"))
    assert result["subreddit"] == "SaaS"
    assert result["body"].count("Acme") == 1
    assert result["body"].strip().startswith("For a while")


def test_linkedin_post_includes_url_when_present() -> None:
    post = content.linkedin_post(_profile())
    assert "https://acme.example" in post
    assert "Acme" in post


def test_linkedin_post_without_url() -> None:
    post = content.linkedin_post(_profile(url=""))
    assert "https://" not in post


def test_generate_all_returns_every_platform() -> None:
    result = content.generate_all(_profile())
    assert set(result) == {"product_hunt", "show_hn", "twitter", "reddit", "linkedin"}
    assert result["product_hunt"]["tagline"]["length"] <= content.PRODUCT_HUNT_TAGLINE_MAX


def test_flag_hype_words_detects_multiple() -> None:
    flags = content.flag_hype_words("This is an incredible, game-changing, revolutionary release")
    assert "incredible" in flags
    assert "revolutionary" in flags
