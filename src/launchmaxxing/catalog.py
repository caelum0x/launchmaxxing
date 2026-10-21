"""Static reference data: launch directories and the first-100-users
playbook. None of this is fetched over the network -- it is curated,
versioned-in-code reference data you can read, grep and send a PR against.
"""

from __future__ import annotations

from typing import Any

#: Launch/submission directories a founder lists a new product on. ``url``
#: is the real submission page (not just the homepage) wherever the site
#: has one. ``categories`` loosely tags what kind of product fits the site,
#: used only to filter :func:`platforms_for_category`.
PLATFORMS: tuple[dict[str, Any], ...] = (
    {"id": "product_hunt", "name": "Product Hunt", "url": "https://www.producthunt.com/posts/new",
     "categories": ("saas", "ai", "app", "dev_tool", "general"), "account_free": True,
     "note": "Biggest general launch audience; post at 00:01 PT for a full day on the board."},
    {"id": "betalist", "name": "BetaList", "url": "https://betalist.com/submit",
     "categories": ("saas", "ai", "app", "general"), "account_free": True,
     "note": "Pre-launch/early-stage audience; free submission queue is slower, paid is same-week."},
    {"id": "devhunt", "name": "DevHunt", "url": "https://devhunt.org/login",
     "categories": ("dev_tool", "ai", "saas"), "account_free": False,
     "note": "Developer-tool-focused Product-Hunt-style board; the old /submit URL now 404s -- "
             "the site's own \"Submit\" link goes straight to /login, account required.",
     "verified_at": "2026-10-18"},
    {"id": "peerlist", "name": "Peerlist (Launchpad)", "url": "https://peerlist.io/launchpad",
     "categories": ("saas", "ai", "dev_tool", "general"), "account_free": True,
     "note": "Builder/tech-professional audience; a Peerlist profile post plus a Launchpad entry."},
    {"id": "hacker_news", "name": "Hacker News (Show HN)", "url": "https://news.ycombinator.com/submit",
     "categories": ("dev_tool", "ai", "saas", "oss", "general"), "account_free": True,
     "note": "Title must start literally with \"Show HN:\"; founders/developers, not consumers."},
    {"id": "indie_hackers", "name": "Indie Hackers", "url": "https://www.indiehackers.com/post/new",
     "categories": ("saas", "general"), "account_free": True,
     "note": "Post the build story and milestones, not a bare pitch; community of small teams/founders. "
             "The page is behind a Cloudflare JS challenge that returns 403 to plain HTTP clients "
             "(confirmed with both this tool's checker and a real-browser User-Agent via curl) -- "
             "use a real browser, this is a bot-check, not a dead URL.",
     "verified_at": "2026-10-21"},
    {"id": "launching_next", "name": "Launching Next", "url": "https://launchingnext.com/submit",
     "categories": ("saas", "ai", "app", "general"), "account_free": True,
     "note": "Free pre-launch/launch directory."},
    {"id": "saashub", "name": "SaaSHub", "url": "https://www.saashub.com/submit",
     "categories": ("saas", "ai", "dev_tool"), "account_free": True,
     "note": "Alternative-to style directory; good for SEO backlinks."},
    {"id": "alternativeto", "name": "AlternativeTo", "url": "https://alternativeto.net/account/add-software/",
     "categories": ("saas", "ai", "dev_tool", "oss"), "account_free": False,
     "note": "List as an alternative to the tool you displace; strong long-tail search traffic. "
             "The submit URL is literally the account area (`/account/add-software/`) -- AlternativeTo "
             "requires a free account to add software; site is also behind a Cloudflare JS challenge "
             "that blocks plain HTTP verification.",
     "verified_at": "2026-10-21"},
    {"id": "futurepedia", "name": "Futurepedia", "url": "https://www.futurepedia.io",
     "categories": ("ai",), "account_free": True,
     "note": "AI-tool-only directory with category pages that rank; the old /submit-tool URL now "
             "404s and the real submit flow is behind client-side JS with no stable direct URL -- "
             "start from the homepage nav.", "verified_at": "2026-10-18"},
    {"id": "there_is_an_ai_for_that", "name": "There's An AI For That",
     "url": "https://theresanaiforthat.com/add/", "categories": ("ai",), "account_free": True,
     "note": "High-traffic AI-tool directory; free listing, paid featured slot. The /add/ page is "
             "behind a Cloudflare JS challenge to plain HTTP clients -- use a real browser.",
     "verified_at": "2026-10-18"},
    {"id": "g2", "name": "G2", "url": "https://www.g2.com/products/new",
     "categories": ("saas", "general"), "account_free": False,
     "note": "Review-site listing; most value once there are real reviews. Listing a product "
             "requires a G2 seller/vendor account (via sell.g2.com) -- there is no account-free "
             "path; the URL is also behind DataDome bot protection that blocks plain HTTP "
             "verification.", "verified_at": "2026-10-21"},
    {"id": "capterra", "name": "Capterra", "url": "https://www.capterra.com/vendors/sign-up",
     "categories": ("saas", "general"), "account_free": False,
     "note": "B2B software directory; buyer-intent traffic. The submit URL is literally a vendor "
             "sign-up page -- Capterra requires creating a vendor account before a listing can be "
             "started; also behind a Cloudflare bot check that blocks plain HTTP verification.",
     "verified_at": "2026-10-21"},
    {"id": "fazier", "name": "Fazier", "url": "https://fazier.com/launch",
     "categories": ("saas", "ai", "app", "general"), "account_free": True,
     "note": "Startup launch directory with SEO backlinks."},
    {"id": "uneed", "name": "Uneed", "url": "https://www.uneed.best/submit-a-tool",
     "categories": ("saas", "ai", "dev_tool", "general"), "account_free": False,
     "note": "Daily/weekly/monthly launch leaderboard. The name+URL step is account-free, but "
             "finishing the listing requires \"Create your free account to save [product] and "
             "schedule its launch\" -- account required to actually publish.",
     "verified_at": "2026-10-18"},
    {"id": "tinylaunch", "name": "TinyLaunch", "url": "https://www.tinylaunch.com",
     "categories": ("saas", "ai", "general"), "account_free": True,
     "note": "Small-team-friendly weekly launch board; the old /launches/new URL now 404s and "
             "there's no stable direct submit URL in the static page -- start from the homepage.",
     "verified_at": "2026-10-18"},
    {"id": "reddit_sidebuild", "name": "r/SideProject", "url": "https://www.reddit.com/r/SideProject/submit",
     "categories": ("saas", "ai", "app", "general", "oss"), "account_free": True,
     "note": "Share the build, not a bare link; r/SideProject welcomes launches."},
    {"id": "github_awesome", "name": "Awesome lists (GitHub)",
     "url": "https://github.com/search?q=awesome+topic&type=repositories",
     "categories": ("oss", "dev_tool"), "account_free": True,
     "note": "PR your repo into the matching awesome-* list for its category."},
    # -- Added in v2 (2026-10-18), re-verified live via direct fetch that day; see CHANGELOG. --
    {"id": "peerpush", "name": "PeerPush", "url": "https://peerpush.com/submit",
     "categories": ("saas", "ai", "ai_discovery", "dev_tool", "general"), "account_free": False,
     "note": "Paste your URL, free/paid/sponsored launch tiers; explicitly optimizes listings for AI "
             "assistants (ChatGPT, Perplexity, Claude/MCP) as well as human visitors. Re-checked "
             "2026-10-18: the paste-URL step itself is account-free, but claiming/finishing a "
             "listing (same account system as Uneed) requires sign-up.",
     "verified_at": "2026-10-18"},
    {"id": "turbo0", "name": "Turbo0", "url": "https://turbo0.com/submit",
     "categories": ("saas", "ai", "dev_tool", "general"), "account_free": False,
     "note": "Free dofollow listing with a permanent badge; roughly a two-week review queue. "
             "Re-checked 2026-10-18: /submit now redirects (302) straight to "
             "/auth/login?callbackUrl=%2Fsubmit -- account required from the first step.",
     "verified_at": "2026-10-18"},
    {"id": "smol_launch", "name": "Smol Launch", "url": "https://smollaunch.com/submit",
     "categories": ("saas", "ai", "app", "general"), "account_free": False,
     "note": "A full week of visibility instead of one day; paste-URL submission, freemium tiers. "
             "Re-checked 2026-10-18: the rendered page shows a Sign in control before the submit "
             "form -- plan on creating an account.",
     "verified_at": "2026-10-18"},
    {"id": "startupbase", "name": "StartupBase", "url": "https://startupbase.io/launch",
     "categories": ("saas", "ai", "app", "general"), "account_free": False,
     "note": "Every approved product gets a real launch slot (not insiders-only) plus a DR75+ "
             "backlink. Re-checked 2026-10-18: the page itself ships a hidden login-email-origin "
             "field and sign-in/sign-up copy -- account required to complete a listing.",
     "verified_at": "2026-10-18"},
    {"id": "microlaunch", "name": "Microlaunch", "url": "https://microlaunch.net",
     "categories": ("saas", "dev_tool", "general"), "account_free": False,
     "note": "Sign in, then use the 'New Launch' button (no direct /submit URL); listing stays live on "
             "the board for about a month, aimed at micro-SaaS/small tools rather than one big launch day.",
     "verified_at": "2026-10-18"},
    {"id": "findly_tools", "name": "Findly Tools", "url": "https://findly.tools/submit",
     "categories": ("ai", "saas", "dev_tool"), "account_free": False,
     "note": "AI/dev-tool discovery directory; paste-URL submission form. Re-checked 2026-10-18: "
             "/submit now redirects (307) straight to /sign-in?from=%2Fsubmit -- account required "
             "from the first step.",
     "verified_at": "2026-10-18"},
)
PLATFORM_BY_ID: dict[str, dict[str, Any]] = {p["id"]: p for p in PLATFORMS}

#: The 10-step first-100-users distribution playbook. Step 1 ("launch
#: everywhere") is tracked at platform granularity via the state module's
#: per-platform status; the checklist marks it done once any platform for
#: the product is submitted or live.
PLAYBOOK_STEPS: tuple[dict[str, str], ...] = (
    {"key": "launch_everywhere", "title": "Launch everywhere",
     "detail": "Product Hunt, DevHunt, BetaList, Peerlist, Show HN and the other listing sites."},
    {"key": "cold_outreach", "title": "Network + cold outreach",
     "detail": "Friends, ex-colleagues, LinkedIn, one-sentence personalized cold email."},
    {"key": "reddit_pain_points", "title": "Reddit pain-point threads",
     "detail": "Find threads where people complain about the problem this product solves; reply with value."},
    {"key": "ugc_creators", "title": "UGC creator outreach",
     "detail": "DM 10-15 creators: $15-30/video plus a performance bonus, ideally from a fresh account."},
    {"key": "icp_communities", "title": "Where the ICP hangs out",
     "detail": "Communities, newsletters, podcasts, creators the ideal customer already follows."},
    {"key": "competitor_backlinks", "title": "Competitor backlinks",
     "detail": "Find where competitors are listed/linked and submit to the same places."},
    {"key": "demo_video", "title": "Demo video",
     "detail": "A short, real screen-recorded demo on X and LinkedIn -- show, don't tell."},
    {"key": "x_trends", "title": "Ride X/Twitter trends",
     "detail": "Hop on a weekly trend and plug the product with a relevant angle."},
    {"key": "build_in_public", "title": "Build in public",
     "detail": "3-4 posts/day showing real progress, not just announcements."},
    {"key": "reply_viral_tweets", "title": "Reply to viral tweets",
     "detail": "Reply with real value to viral tweets in the product's niche."},
)
STEP_BY_KEY: dict[str, dict[str, str]] = {s["key"]: s for s in PLAYBOOK_STEPS}


def platforms_for_category(category: str | None) -> tuple[dict[str, Any], ...]:
    """All platforms, or only the ones tagged with ``category`` (e.g. ``"ai"``, ``"oss"``)."""
    if not category:
        return PLATFORMS
    cat = category.strip().lower()
    return tuple(p for p in PLATFORMS if cat in p["categories"])


def platforms_account_free(platforms: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    """Filter ``platforms`` down to the ones that can be submitted without creating an account
    anywhere in the flow (``account_free`` is ``True``). Composable with
    :func:`platforms_for_category`, e.g. ``platforms_account_free(platforms_for_category("ai"))``."""
    return tuple(p for p in platforms if p["account_free"])


def all_categories() -> tuple[str, ...]:
    """Every category used across :data:`PLATFORMS`, sorted."""
    seen: set[str] = set()
    for p in PLATFORMS:
        seen.update(p["categories"])
    return tuple(sorted(seen))


__all__ = [
    "PLATFORMS", "PLATFORM_BY_ID", "PLAYBOOK_STEPS", "STEP_BY_KEY",
    "all_categories", "platforms_for_category", "platforms_account_free",
]
