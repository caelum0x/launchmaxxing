from __future__ import annotations

from launchmaxxing import catalog


def test_platform_count_and_shape() -> None:
    assert len(catalog.PLATFORMS) == 82
    for p in catalog.PLATFORMS:
        assert p["id"] and p["name"] and p["url"].startswith("https://")
        assert isinstance(p["categories"], tuple) and p["categories"]
        assert p["note"]
        assert isinstance(p["account_free"], bool)


def test_platform_by_id_matches_platforms() -> None:
    assert set(catalog.PLATFORM_BY_ID) == {p["id"] for p in catalog.PLATFORMS}
    assert catalog.PLATFORM_BY_ID["product_hunt"]["name"] == "Product Hunt"


def test_platforms_for_category_none_returns_all() -> None:
    assert catalog.platforms_for_category(None) == catalog.PLATFORMS
    assert catalog.platforms_for_category("") == catalog.PLATFORMS


def test_platforms_for_category_filters() -> None:
    ai_platforms = catalog.platforms_for_category("ai")
    assert ai_platforms
    assert all("ai" in p["categories"] for p in ai_platforms)
    assert len(ai_platforms) < len(catalog.PLATFORMS)


def test_platforms_for_category_is_case_insensitive() -> None:
    assert catalog.platforms_for_category("AI") == catalog.platforms_for_category("ai")


def test_platforms_for_category_unknown_returns_empty() -> None:
    assert catalog.platforms_for_category("not-a-real-category") == ()


def test_playbook_has_ten_steps() -> None:
    assert len(catalog.PLAYBOOK_STEPS) == 10
    keys = [s["key"] for s in catalog.PLAYBOOK_STEPS]
    assert len(set(keys)) == 10
    assert keys[0] == "launch_everywhere"


def test_step_by_key_matches_playbook() -> None:
    assert set(catalog.STEP_BY_KEY) == {s["key"] for s in catalog.PLAYBOOK_STEPS}


def test_all_categories_sorted_and_covers_platforms() -> None:
    categories = catalog.all_categories()
    assert list(categories) == sorted(categories)
    for p in catalog.PLATFORMS:
        assert set(p["categories"]) <= set(categories)


def test_ai_discovery_category_present_for_geo_optimized_directories() -> None:
    ai_discovery = catalog.platforms_for_category("ai_discovery")
    assert ai_discovery
    assert all(p["id"] == "peerpush" or "ai_discovery" in p["categories"] for p in ai_discovery)


def test_v2_directories_have_verified_at() -> None:
    v2_ids = {"peerpush", "turbo0", "smol_launch", "startupbase", "microlaunch", "findly_tools"}
    for platform_id in v2_ids:
        assert catalog.PLATFORM_BY_ID[platform_id].get("verified_at")


def test_launching_next_url_is_the_live_www_and_trailing_slash_form() -> None:
    # Regression test: the bare `https://launchingnext.com/submit` (no `www.`, no trailing
    # slash) 404s in production -- found live via `directories --check-links` on 2026-10-22.
    # Only `https://www.launchingnext.com/submit/` resolves; don't regress to the stale form.
    platform = catalog.PLATFORM_BY_ID["launching_next"]
    assert platform["url"] == "https://www.launchingnext.com/submit/"
    assert platform["account_free"] is True
    assert platform.get("verified_at")


def test_platforms_account_free_filters() -> None:
    account_free = catalog.platforms_account_free(catalog.PLATFORMS)
    assert account_free
    assert all(p["account_free"] for p in account_free)
    assert len(account_free) < len(catalog.PLATFORMS)


def test_platforms_account_free_excludes_known_signup_required_entries() -> None:
    account_free_ids = {p["id"] for p in catalog.platforms_account_free(catalog.PLATFORMS)}
    for platform_id in ("devhunt", "uneed", "turbo0", "g2", "capterra", "alternativeto"):
        assert platform_id not in account_free_ids


def test_platforms_account_free_is_composable_with_category_filter() -> None:
    ai_platforms = catalog.platforms_for_category("ai")
    account_free_ai = catalog.platforms_account_free(ai_platforms)
    assert account_free_ai
    assert all(p["account_free"] and "ai" in p["categories"] for p in account_free_ai)
    assert len(account_free_ai) < len(ai_platforms)
