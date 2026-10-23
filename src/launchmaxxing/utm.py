"""Local UTM link builder -- the "analytics integration hook" that fits the no-server philosophy:
this tool has no backend to receive clicks, so instead of faking analytics it generates correctly
tagged links and stores them locally so you know which exact link you used where. Paste the
result into whatever analytics you already run (Plausible, self-hosted PostHog/Umami, GA4) --
nothing here calls any of those services.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

#: Sensible utm_source/utm_medium defaults per directory, so a founder does not have to invent
#: naming conventions by hand for every catalog entry -- only override when it matters. Platforms
#: without an explicit entry here still work: :func:`defaults_for_platform` falls back to deriving
#: source/medium from the platform_id itself.
PLATFORM_UTM_DEFAULTS: dict[str, dict[str, str]] = {
    "product_hunt": {"source": "producthunt", "medium": "launch_directory"},
    "betalist": {"source": "betalist", "medium": "launch_directory"},
    "devhunt": {"source": "devhunt", "medium": "launch_directory"},
    "peerlist": {"source": "peerlist", "medium": "launch_directory"},
    "hacker_news": {"source": "hackernews", "medium": "show_hn"},
    "indie_hackers": {"source": "indiehackers", "medium": "community_post"},
    "launching_next": {"source": "launchingnext", "medium": "launch_directory"},
    "saashub": {"source": "saashub", "medium": "directory"},
    "alternativeto": {"source": "alternativeto", "medium": "directory"},
    "futurepedia": {"source": "futurepedia", "medium": "ai_directory"},
    "there_is_an_ai_for_that": {"source": "theresanaiforthat", "medium": "ai_directory"},
    "g2": {"source": "g2", "medium": "review_directory"},
    "capterra": {"source": "capterra", "medium": "review_directory"},
    "fazier": {"source": "fazier", "medium": "launch_directory"},
    "uneed": {"source": "uneed", "medium": "launch_directory"},
    "tinylaunch": {"source": "tinylaunch", "medium": "launch_directory"},
    "reddit_sidebuild": {"source": "reddit", "medium": "community_post"},
    "github_awesome": {"source": "github", "medium": "awesome_list"},
    "peerpush": {"source": "peerpush", "medium": "launch_directory"},
    "turbo0": {"source": "turbo0", "medium": "launch_directory"},
    "smol_launch": {"source": "smollaunch", "medium": "launch_directory"},
    "startupbase": {"source": "startupbase", "medium": "launch_directory"},
    "microlaunch": {"source": "microlaunch", "medium": "launch_directory"},
    "findly_tools": {"source": "findlytools", "medium": "ai_directory"},
    # -- Hand-curated for the 58 catalog entries added in v3 (2026-10-23); same naming
    # convention as the block above (source = the site's own slug, medium = what kind of
    # listing it actually is) instead of falling back to the generic id-derived default. --
    "aitools_fyi": {"source": "aitoolsfyi", "medium": "ai_directory"},
    "dang_ai": {"source": "dangai", "medium": "ai_directory"},
    "supertools_rundown": {"source": "supertools", "medium": "ai_directory"},
    "futuretools": {"source": "futuretools", "medium": "ai_directory"},
    "aixploria": {"source": "aixploria", "medium": "ai_directory"},
    "toolify_ai": {"source": "toolify", "medium": "ai_directory"},
    "insidr_ai": {"source": "insidrai", "medium": "ai_directory"},
    "aitoolmall": {"source": "aitoolmall", "medium": "ai_directory"},
    "toolsnavigator": {"source": "toolsnavigator", "medium": "ai_directory"},
    "chrome_web_store": {"source": "chromewebstore", "medium": "extension_store"},
    "edge_addons": {"source": "edgeaddons", "medium": "extension_store"},
    "firefox_addons": {"source": "firefoxaddons", "medium": "extension_store"},
    "opera_addons": {"source": "operaaddons", "medium": "extension_store"},
    "rapidapi": {"source": "rapidapi", "medium": "api_marketplace"},
    "postman_api_network": {"source": "postman", "medium": "api_marketplace"},
    "apis_guru": {"source": "apisguru", "medium": "api_directory"},
    "public_apis_github": {"source": "publicapis", "medium": "api_directory"},
    "paved": {"source": "paved", "medium": "newsletter_sponsor"},
    "swapstack": {"source": "swapstack", "medium": "newsletter_sponsor"},
    "sidebar_sponsor": {"source": "sidebar", "medium": "newsletter_sponsor"},
    "beehiiv_ad_network": {"source": "beehiiv", "medium": "newsletter_sponsor"},
    "disboard": {"source": "disboard", "medium": "discord_directory"},
    "discord_me": {"source": "discordme", "medium": "discord_directory"},
    "discadia": {"source": "discadia", "medium": "discord_directory"},
    "slofile": {"source": "slofile", "medium": "slack_directory"},
    "getapp": {"source": "getapp", "medium": "review_directory"},
    "software_advice": {"source": "softwareadvice", "medium": "review_directory"},
    "trustradius": {"source": "trustradius", "medium": "review_directory"},
    "sourceforge_vendors": {"source": "sourceforge", "medium": "directory"},
    "crozdesk": {"source": "crozdesk", "medium": "review_directory"},
    "goodfirms": {"source": "goodfirms", "medium": "review_directory"},
    "featuredcustomers": {"source": "featuredcustomers", "medium": "review_directory"},
    "slant": {"source": "slant", "medium": "review_directory"},
    "appsumo_partners": {"source": "appsumo", "medium": "marketplace"},
    "zapier_apps": {"source": "zapier", "medium": "integration_marketplace"},
    "make_integromat": {"source": "make", "medium": "integration_marketplace"},
    "ifttt": {"source": "ifttt", "medium": "integration_marketplace"},
    "slack_app_directory": {"source": "slackappdirectory", "medium": "integration_marketplace"},
    "zoom_marketplace": {"source": "zoommarketplace", "medium": "integration_marketplace"},
    "shopify_app_store": {"source": "shopifyappstore", "medium": "integration_marketplace"},
    "woocommerce_marketplace": {"source": "woocommerce", "medium": "integration_marketplace"},
    "wordpress_plugins": {"source": "wordpressplugins", "medium": "integration_marketplace"},
    "notion_integrations": {"source": "notion", "medium": "integration_marketplace"},
    "atlassian_marketplace": {"source": "atlassianmarketplace", "medium": "integration_marketplace"},
    "google_workspace_marketplace": {"source": "googleworkspacemarketplace", "medium": "integration_marketplace"},
    "salesforce_appexchange": {"source": "salesforceappexchange", "medium": "integration_marketplace"},
    "hubspot_ecosystem": {"source": "hubspot", "medium": "integration_marketplace"},
    "crunchbase": {"source": "crunchbase", "medium": "company_profile"},
    "betapage": {"source": "betapage", "medium": "launch_directory"},
    "nocodelist": {"source": "nocodelist", "medium": "directory"},
    "nocodefinder": {"source": "nocodefinder", "medium": "directory"},
    "yc_launches": {"source": "yclaunches", "medium": "launch_directory"},
    "stackshare": {"source": "stackshare", "medium": "tech_stack_directory"},
    "console_dev": {"source": "consoledev", "medium": "directory"},
    "reddit_saas": {"source": "reddit", "medium": "community_post"},
    "reddit_entrepreneur_ridealong": {"source": "reddit", "medium": "community_post"},
    "reddit_artificial": {"source": "reddit", "medium": "community_post"},
    "reddit_roastmystartup": {"source": "reddit", "medium": "community_post"},
}

UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content")

#: Column order for CSV export, matching the ``utm_links`` row shape returned by
#: :func:`launchmaxxing.db.list_utm_links`.
CSV_FIELDS = ("id", "product_name", "platform_id", "base_url", "source", "medium", "campaign", "content",
              "full_url", "created_at")


def defaults_for_platform(platform_id: str) -> dict[str, str]:
    return dict(PLATFORM_UTM_DEFAULTS.get(platform_id, {"source": platform_id or "unknown", "medium": "referral"}))


def build_url(base_url: str, *, source: str, medium: str, campaign: str, content: str = "") -> str:
    """Append (or replace) ``utm_*`` query params on ``base_url``. Existing non-UTM query params
    are preserved; a base URL with its own ``utm_*`` params already set gets them overwritten by
    the explicit arguments, so re-running this is idempotent instead of stacking duplicates."""
    clean_base = base_url.strip()
    if not clean_base:
        raise ValueError("base_url is required")
    if "://" not in clean_base:
        clean_base = f"https://{clean_base}"
    parsed = urlparse(clean_base)
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.startswith("utm_")]
    utm_pairs = [("utm_source", source), ("utm_medium", medium), ("utm_campaign", campaign)]
    if content:
        utm_pairs.append(("utm_content", content))
    new_query = urlencode(kept + utm_pairs)
    return urlunparse(parsed._replace(query=new_query))


def write_links_csv(rows: Sequence[dict[str, Any]], path: Path | str) -> Path:
    """Write saved UTM link ``rows`` (as returned by :func:`launchmaxxing.db.list_utm_links`) to a
    CSV file at ``path`` with a header row, so a founder can import links into a spreadsheet.
    Returns the resolved :class:`~pathlib.Path` written to."""
    out_path = Path(path)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})
    return out_path


__all__ = ["CSV_FIELDS", "PLATFORM_UTM_DEFAULTS", "UTM_KEYS", "build_url", "defaults_for_platform",
           "write_links_csv"]
