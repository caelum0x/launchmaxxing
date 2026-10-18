from __future__ import annotations

import pytest

from launchmaxxing import utm


def test_defaults_for_known_platform() -> None:
    defaults = utm.defaults_for_platform("product_hunt")
    assert defaults == {"source": "producthunt", "medium": "launch_directory"}


def test_defaults_for_unknown_platform_falls_back() -> None:
    defaults = utm.defaults_for_platform("totally-unknown")
    assert defaults["source"] == "totally-unknown"
    assert defaults["medium"] == "referral"


def test_defaults_for_every_catalog_platform_id_present() -> None:
    from launchmaxxing import catalog

    for platform in catalog.PLATFORMS:
        assert platform["id"] in utm.PLATFORM_UTM_DEFAULTS


def test_build_url_adds_utm_params() -> None:
    url = utm.build_url("https://acme.example", source="producthunt", medium="launch_directory",
                        campaign="acme-launch")
    assert "utm_source=producthunt" in url
    assert "utm_medium=launch_directory" in url
    assert "utm_campaign=acme-launch" in url


def test_build_url_adds_scheme_when_missing() -> None:
    url = utm.build_url("acme.example", source="s", medium="m", campaign="c")
    assert url.startswith("https://acme.example")


def test_build_url_preserves_existing_non_utm_params() -> None:
    url = utm.build_url("https://acme.example/page?ref=abc", source="s", medium="m", campaign="c")
    assert "ref=abc" in url


def test_build_url_overwrites_existing_utm_params_idempotently() -> None:
    first = utm.build_url("https://acme.example", source="old", medium="old", campaign="old")
    second = utm.build_url(first, source="new", medium="new", campaign="new")
    assert "utm_source=new" in second
    assert "utm_source=old" not in second
    assert second.count("utm_source") == 1


def test_build_url_includes_optional_content_param() -> None:
    url = utm.build_url("https://acme.example", source="s", medium="m", campaign="c", content="thread-1")
    assert "utm_content=thread-1" in url


def test_build_url_rejects_empty_base_url() -> None:
    with pytest.raises(ValueError):
        utm.build_url("", source="s", medium="m", campaign="c")
