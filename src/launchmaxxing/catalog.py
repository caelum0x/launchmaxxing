"""Static reference data: launch directories and the first-100-users
playbook. None of this is fetched over the network -- it is curated,
versioned-in-code reference data you can read, grep and send a PR against.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _xml_escape
from xml.sax.saxutils import quoteattr as _xml_quoteattr

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
    {"id": "launching_next", "name": "Launching Next", "url": "https://www.launchingnext.com/submit/",
     "categories": ("saas", "ai", "app", "general"), "account_free": True,
     "note": "Free pre-launch/launch directory; the submission form itself is account-free "
             "(plain POST, no login). The old `https://launchingnext.com/submit` (no `www.`, no "
             "trailing slash) now 404s -- the site enforces both the `www.` host and the trailing "
             "slash; `--check-links` caught this live. Confirmed real submissions went through this "
             "directory for ereboslab, lawsynth and scribase (see launch-evidence/).",
     "verified_at": "2026-10-22"},
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
    # -- Added in v3 (2026-10-23), verified live via direct HTTP fetch that day; see CHANGELOG and
    # BUILD-LOG-2026-10-23.md. This batch closes the breadth gap against SubmitMap (366),
    # OpenLaunch (239) and SubmitFleet (339) called out in STRATEGY-2026-10-23.md section 1 by
    # adding six new category families: AI-tool/GEO directories, browser-extension stores, API
    # marketplaces, newsletter sponsor slots, Slack/Discord community lists and vertical-SaaS/
    # integration-ecosystem directories. --
    {"id": "aitools_fyi", "name": "AITools.fyi", "url": "https://aitools.fyi/submit",
     "categories": ("ai", "ai_discovery"), "account_free": True,
     "note": "Paste-URL AI tool directory submission form; responded 200 to a plain GET, no login "
             "wall visible on the form page itself.", "verified_at": "2026-10-23"},
    {"id": "dang_ai", "name": "Dang.ai", "url": "https://dang.ai/submit",
     "categories": ("ai", "ai_discovery"), "account_free": True,
     "note": "Curated AI tools directory; submit form is a plain page, no account wall on GET.",
     "verified_at": "2026-10-23"},
    {"id": "supertools_rundown", "name": "Supertools (The Rundown AI)", "url": "https://supertools.therundown.ai",
     "categories": ("ai", "ai_discovery"), "account_free": True,
     "note": "AI tool directory run by The Rundown AI newsletter; start from the homepage, no "
             "stable direct /submit URL found.", "verified_at": "2026-10-23"},
    {"id": "futuretools", "name": "Future Tools", "url": "https://www.futuretools.io/submit-a-tool",
     "categories": ("ai", "ai_discovery"), "account_free": True,
     "note": "Matt Wolfe's widely-followed AI tool directory; /submit-a-tool redirects (308, https "
             "canonicalization) but resolves live.", "verified_at": "2026-10-23"},
    {"id": "aixploria", "name": "Aixploria", "url": "https://aixploria.com/en/add-ai/",
     "categories": ("ai", "ai_discovery"), "account_free": True,
     "note": "AI tool directory with a dedicated add-your-tool page; responded 200 to a plain GET.",
     "verified_at": "2026-10-23"},
    {"id": "toolify_ai", "name": "Toolify.ai", "url": "https://www.toolify.ai",
     "categories": ("ai", "ai_discovery"), "account_free": False,
     "note": "Large AI tool directory; homepage is behind a Cloudflare JS challenge that returns "
             "403 to a plain HTTP client -- use a real browser; account likely required to submit.",
     "verified_at": "2026-10-23"},
    {"id": "insidr_ai", "name": "Insidr.ai AI Tools", "url": "https://www.insidr.ai/ai-tools",
     "categories": ("ai", "ai_discovery"), "account_free": True,
     "note": "AI tools directory page; no stable direct /submit URL found, start from this listing "
             "page's own submission link.", "verified_at": "2026-10-23"},
    {"id": "aitoolmall", "name": "AI Tool Mall", "url": "https://aitoolmall.com",
     "categories": ("ai", "ai_discovery"), "account_free": True,
     "note": "AI tool directory; no stable direct submit URL in the static page, start from the "
             "homepage nav.", "verified_at": "2026-10-23"},
    {"id": "toolsnavigator", "name": "Tools Navigator", "url": "https://toolsnavigator.com",
     "categories": ("ai", "ai_discovery", "saas"), "account_free": True,
     "note": "AI/SaaS tool directory; no stable direct submit URL in the static page, start from "
             "the homepage nav.", "verified_at": "2026-10-23"},
    {"id": "chrome_web_store", "name": "Chrome Web Store", "url": "https://chromewebstore.google.com/",
     "categories": ("dev_tool", "browser_extension", "general"), "account_free": False,
     "note": "List a Chrome extension; requires a one-time $5 Google developer registration fee "
             "(not a subscription) before publishing anything.", "verified_at": "2026-10-23"},
    {"id": "edge_addons", "name": "Microsoft Edge Add-ons",
     "url": "https://partner.microsoft.com/en-us/dashboard/microsoftedge/overview",
     "categories": ("dev_tool", "browser_extension"), "account_free": False,
     "note": "List a browser extension on Edge Add-ons; requires a free Microsoft Partner Center "
             "account (no listing fee, unlike Chrome's $5 one-time charge).", "verified_at": "2026-10-23"},
    {"id": "firefox_addons", "name": "Firefox Add-ons (AMO)",
     "url": "https://addons.mozilla.org/en-US/developers/addon/submit/distribution",
     "categories": ("dev_tool", "browser_extension", "oss"), "account_free": True,
     "note": "List a Firefox extension; a free Mozilla account is required but there is no listing "
             "fee at all, the only one of the four browser stores here with zero cost to publish.",
     "verified_at": "2026-10-23"},
    {"id": "opera_addons", "name": "Opera Add-ons", "url": "https://addons.opera.com/developer/",
     "categories": ("dev_tool", "browser_extension"), "account_free": False,
     "note": "List a browser extension on Opera; the developer dashboard redirects to a login page "
             "for anyone not signed in -- free account required.", "verified_at": "2026-10-23"},
    {"id": "rapidapi", "name": "RapidAPI", "url": "https://rapidapi.com/solution/api-provider",
     "categories": ("dev_tool", "api", "saas"), "account_free": False,
     "note": "List an API on the RapidAPI marketplace as a provider; requires a free RapidAPI "
             "provider account to actually publish an endpoint.", "verified_at": "2026-10-23"},
    {"id": "postman_api_network", "name": "Postman API Network", "url": "https://www.postman.com/explore",
     "categories": ("dev_tool", "api"), "account_free": False,
     "note": "Publish a public API collection/workspace to Postman's API Network; requires a free "
             "Postman account.", "verified_at": "2026-10-23"},
    {"id": "apis_guru", "name": "APIs.guru", "url": "https://apis.guru",
     "categories": ("dev_tool", "api", "oss"), "account_free": True,
     "note": "Open-source directory of OpenAPI/Swagger specs; adding an API is a GitHub pull "
             "request against the APIs.guru repo, not a hosted signup form.", "verified_at": "2026-10-23"},
    {"id": "public_apis_github", "name": "Public APIs (GitHub)",
     "url": "https://github.com/public-apis/public-apis",
     "categories": ("dev_tool", "api", "oss"), "account_free": True,
     "note": "The widely-starred public-apis list; adding an API is a GitHub pull request against "
             "the repo's README, same no-account-beyond-GitHub model as the existing Awesome lists "
             "entry.", "verified_at": "2026-10-23"},
    {"id": "paved", "name": "Paved", "url": "https://paved.com",
     "categories": ("saas", "general", "newsletter"), "account_free": False,
     "note": "Newsletter ad marketplace; booking a sponsor slot requires creating a free advertiser "
             "account before you can see inventory or pay for a placement.", "verified_at": "2026-10-23"},
    {"id": "swapstack", "name": "Swapstack", "url": "https://www.swapstack.co",
     "categories": ("saas", "general", "newsletter"), "account_free": False,
     "note": "Newsletter sponsorship marketplace connecting advertisers with newsletter publishers; "
             "requires a free advertiser account to book a slot.", "verified_at": "2026-10-23"},
    {"id": "sidebar_sponsor", "name": "Sidebar.io Sponsorship", "url": "https://sidebar.io/sponsor",
     "categories": ("dev_tool", "newsletter"), "account_free": True,
     "note": "One-off sponsor slot in the Sidebar.io design-links newsletter; the page itself is a "
             "plain contact/booking form, no account needed to inquire.", "verified_at": "2026-10-23"},
    {"id": "beehiiv_ad_network", "name": "beehiiv Ad Network", "url": "https://ad.beehiiv.com",
     "categories": ("saas", "general", "newsletter"), "account_free": False,
     "note": "Matches advertisers with beehiiv-hosted newsletters for sponsor slots; the page is "
             "behind a Cloudflare JS challenge that returns 403 to a plain HTTP client -- use a "
             "real browser; a free advertiser account is required to book.", "verified_at": "2026-10-23"},
    {"id": "disboard", "name": "Disboard", "url": "https://disboard.org",
     "categories": ("general", "community", "discord"), "account_free": True,
     "note": "The largest Discord server listing site; bumping/listing your own server's invite is "
             "free via their bot, no paid tier required. Homepage is behind a Cloudflare JS "
             "challenge that returns 403 to a plain HTTP client -- use a real browser.",
     "verified_at": "2026-10-23"},
    {"id": "discord_me", "name": "Discord.me", "url": "https://discord.me",
     "categories": ("general", "community", "discord"), "account_free": True,
     "note": "Discord server listing directory; free to list a server. Homepage is behind a "
             "Cloudflare JS challenge that returns 403 to a plain HTTP client -- use a real browser.",
     "verified_at": "2026-10-23"},
    {"id": "discadia", "name": "Discadia", "url": "https://discadia.com",
     "categories": ("general", "community", "discord"), "account_free": True,
     "note": "Discord server listing directory; free to list a server, and the only one of the "
             "three Discord listing sites checked here that answers a plain HTTP GET with 200 "
             "instead of a bot challenge.", "verified_at": "2026-10-23"},
    {"id": "slofile", "name": "Slofile", "url": "https://slofile.com",
     "categories": ("general", "community", "slack"), "account_free": True,
     "note": "Slack community directory; free to add your own Slack community's invite link.",
     "verified_at": "2026-10-23"},
    {"id": "getapp", "name": "GetApp", "url": "https://www.getapp.com/vendors",
     "categories": ("saas", "general"), "account_free": False,
     "note": "Gartner Digital Markets B2B software directory (sister site to Capterra/Software "
             "Advice); listing requires a free vendor account. Site is behind a Cloudflare bot "
             "check that returns 403 to plain HTTP clients.", "verified_at": "2026-10-23"},
    {"id": "software_advice", "name": "Software Advice", "url": "https://www.softwareadvice.com/vendors",
     "categories": ("saas", "general"), "account_free": False,
     "note": "Gartner Digital Markets B2B software directory (sister site to Capterra/GetApp); "
             "listing requires a free vendor account. Site is behind a Cloudflare bot check that "
             "returns 403 to plain HTTP clients.", "verified_at": "2026-10-23"},
    {"id": "trustradius", "name": "TrustRadius", "url": "https://www.trustradius.com/vendors",
     "categories": ("saas", "general"), "account_free": False,
     "note": "B2B software review directory; getting listed/claimed requires a free vendor account. "
             "Site is behind a Cloudflare bot check that returns 403 to plain HTTP clients.",
     "verified_at": "2026-10-23"},
    {"id": "sourceforge_vendors", "name": "SourceForge (vendor listing)",
     "url": "https://sourceforge.net/software/vendors",
     "categories": ("saas", "dev_tool", "oss", "general"), "account_free": False,
     "note": "SourceForge's B2B software directory side (separate from its classic OSS project "
             "hosting); listing requires a free vendor account. Site is behind a bot check that "
             "returns 403 to plain HTTP clients.", "verified_at": "2026-10-23"},
    {"id": "crozdesk", "name": "Crozdesk", "url": "https://www.crozdesk.com/software/get-listed",
     "categories": ("saas", "general"), "account_free": False,
     "note": "B2B software comparison directory with a dedicated get-listed page; requires a free "
             "vendor account. Page is behind a bot check that returns 403 to plain HTTP clients.",
     "verified_at": "2026-10-23"},
    {"id": "goodfirms", "name": "GoodFirms", "url": "https://www.goodfirms.co/vendor/sign-up",
     "categories": ("saas", "general"), "account_free": False,
     "note": "B2B software/services review directory; the submit URL is literally the vendor "
             "sign-up page -- free account required. Page is behind a Cloudflare bot check that "
             "returns 403 to plain HTTP clients.", "verified_at": "2026-10-23"},
    {"id": "featuredcustomers", "name": "FeaturedCustomers",
     "url": "https://www.featuredcustomers.com/vendors/signup",
     "categories": ("saas", "general"), "account_free": False,
     "note": "B2B software review/case-study directory; the submit URL is the vendor sign-up page "
             "-- free account required, but unlike most of this batch's review sites, it answers a "
             "plain HTTP GET with 200 (no bot challenge).", "verified_at": "2026-10-23"},
    {"id": "slant", "name": "Slant", "url": "https://www.slant.co",
     "categories": ("saas", "dev_tool", "general"), "account_free": False,
     "note": "Community Q&A-style \"best X\" recommendation site; adding your own product to a "
             "question's option list requires a free account. Site is behind a bot check that "
             "returns 403 to plain HTTP clients.", "verified_at": "2026-10-23"},
    {"id": "appsumo_partners", "name": "AppSumo Partners", "url": "https://appsumo.com/partners/",
     "categories": ("saas", "general"), "account_free": False,
     "note": "Apply to sell a lifetime-deal listing on AppSumo's marketplace; requires applying as "
             "a partner (free to apply, revenue share on sales) -- not a self-serve instant listing.",
     "verified_at": "2026-10-23"},
    {"id": "zapier_apps", "name": "Zapier App Directory", "url": "https://zapier.com/apps",
     "categories": ("saas", "dev_tool", "integration"), "account_free": False,
     "note": "Build and submit a Zapier integration so your product shows up as a Zap action/"
             "trigger; requires applying through Zapier's developer platform, free but reviewed.",
     "verified_at": "2026-10-23"},
    {"id": "make_integromat", "name": "Make (formerly Integromat)", "url": "https://www.integromat.com",
     "categories": ("saas", "dev_tool", "integration"), "account_free": False,
     "note": "Automation platform's integration directory; publishing your own app/module requires "
             "Make's free developer program.", "verified_at": "2026-10-23"},
    {"id": "ifttt", "name": "IFTTT", "url": "https://ifttt.com/explore",
     "categories": ("saas", "integration", "general"), "account_free": False,
     "note": "Consumer automation platform; publishing your own IFTTT service/applet requires a "
             "free IFTTT developer account and review.", "verified_at": "2026-10-23"},
    {"id": "slack_app_directory", "name": "Slack App Directory", "url": "https://slack.com/marketplace",
     "categories": ("saas", "dev_tool", "integration", "slack"), "account_free": False,
     "note": "List a Slack app; building and submitting one goes through api.slack.com with a free "
             "Slack developer account, then Slack's app review before it appears publicly.",
     "verified_at": "2026-10-23"},
    {"id": "zoom_marketplace", "name": "Zoom App Marketplace", "url": "https://developer.zoom.us/docs/marketplace/",
     "categories": ("saas", "integration"), "account_free": False,
     "note": "List a Zoom app/integration; requires a free Zoom developer account and app review "
             "before publishing.", "verified_at": "2026-10-23"},
    {"id": "shopify_app_store", "name": "Shopify App Store", "url": "https://apps.shopify.com",
     "categories": ("saas", "integration", "ecommerce"), "account_free": False,
     "note": "List a Shopify app; requires joining the free Shopify Partner Program and passing "
             "Shopify's app review before the listing goes live.", "verified_at": "2026-10-23"},
    {"id": "woocommerce_marketplace", "name": "WooCommerce Marketplace",
     "url": "https://woocommerce.com/products/",
     "categories": ("saas", "dev_tool", "integration", "ecommerce"), "account_free": False,
     "note": "List a WooCommerce extension; requires joining WooCommerce's (free to apply) "
             "marketplace partner program and a product review before it goes live.",
     "verified_at": "2026-10-23"},
    {"id": "wordpress_plugins", "name": "WordPress Plugin Directory",
     "url": "https://wordpress.org/plugins/developers/add/",
     "categories": ("oss", "dev_tool", "integration"), "account_free": True,
     "note": "Submit a WordPress plugin; a free WordPress.org account is required but there is no "
             "fee and no partner-program gate -- the plugin's source just has to pass the "
             "WordPress.org review guidelines.", "verified_at": "2026-10-23"},
    {"id": "notion_integrations", "name": "Notion Integrations", "url": "https://developers.notion.com",
     "categories": ("saas", "dev_tool", "integration"), "account_free": True,
     "note": "Build and publish a public Notion integration; a free Notion account is enough to "
             "create one at notion.so/my-integrations, no partner-program gate.",
     "verified_at": "2026-10-23"},
    {"id": "atlassian_marketplace", "name": "Atlassian Marketplace",
     "url": "https://developer.atlassian.com/platform/marketplace/",
     "categories": ("saas", "dev_tool", "integration"), "account_free": False,
     "note": "List a Jira/Confluence/Trello app; requires a free Atlassian developer account and "
             "app review before the listing is public.", "verified_at": "2026-10-23"},
    {"id": "google_workspace_marketplace", "name": "Google Workspace Marketplace",
     "url": "https://developers.google.com/workspace/marketplace",
     "categories": ("saas", "integration"), "account_free": False,
     "note": "List a Google Workspace add-on; requires a Google Cloud developer account, OAuth "
             "verification and Google's review before the listing is public.", "verified_at": "2026-10-23"},
    {"id": "salesforce_appexchange", "name": "Salesforce AppExchange", "url": "https://appexchange.salesforce.com",
     "categories": ("saas", "integration"), "account_free": False,
     "note": "List a Salesforce app; requires joining the free Salesforce Partner Community and a "
             "security review, the most involved listing process in this marketplace batch.",
     "verified_at": "2026-10-23"},
    {"id": "hubspot_ecosystem", "name": "HubSpot App Marketplace", "url": "https://developers.hubspot.com/get-started",
     "categories": ("saas", "integration"), "account_free": False,
     "note": "List a HubSpot app/integration; requires a free HubSpot developer account and app "
             "certification review before it appears in the marketplace.", "verified_at": "2026-10-23"},
    {"id": "crunchbase", "name": "Crunchbase", "url": "https://www.crunchbase.com/add-new",
     "categories": ("general", "saas"), "account_free": True,
     "note": "Add a free company profile; strong for SEO/backlinks and investor/press discovery. "
             "The add-company page is behind a Cloudflare bot check that returns 403 to plain HTTP "
             "clients -- use a real browser; the profile itself is free to create.",
     "verified_at": "2026-10-23"},
    {"id": "betapage", "name": "BetaPage", "url": "https://betapage.co/submit",
     "categories": ("saas", "ai", "app", "general"), "account_free": True,
     "note": "Pre-launch/beta product directory, similar niche to BetaList; the /submit page "
             "answers a plain HTTP GET with 200.", "verified_at": "2026-10-23"},
    {"id": "nocodelist", "name": "NoCodeList", "url": "https://nocodelist.co/submit",
     "categories": ("saas", "no_code", "general"), "account_free": True,
     "note": "No-code tool directory with a dedicated submit page that answers a plain HTTP GET "
             "with 200.", "verified_at": "2026-10-23"},
    {"id": "nocodefinder", "name": "NoCodeFinder", "url": "https://nocodefinder.com",
     "categories": ("saas", "no_code", "general"), "account_free": True,
     "note": "No-code tool directory; no stable direct submit URL in the static page, start from "
             "the homepage nav.", "verified_at": "2026-10-23"},
    {"id": "yc_launches", "name": "Y Combinator Launches", "url": "https://www.ycombinator.com/launches",
     "categories": ("saas", "ai", "general"), "account_free": False,
     "note": "YC's own launch board; restricted to YC-backed companies (not a general-purpose "
             "directory) -- only relevant if the product going through this tool is a current or "
             "former YC company.", "verified_at": "2026-10-23"},
    {"id": "stackshare", "name": "StackShare", "url": "https://stackshare.io",
     "categories": ("dev_tool", "saas"), "account_free": False,
     "note": "Developer-tool directory where companies publish their tech stack and tools get "
             "discovered via \"uses this\" pages; adding a tool page requires a free account. The "
             "site rate-limited a plain HTTP check (429) during verification -- confirmed live, "
             "just bot-throttled.", "verified_at": "2026-10-23"},
    {"id": "console_dev", "name": "Console.dev", "url": "https://console.dev/tools",
     "categories": ("dev_tool",), "account_free": True,
     "note": "Developer-tools newsletter and directory; tool suggestions go through Console's "
             "editorial submission, not a self-serve instant listing.", "verified_at": "2026-10-23"},
    {"id": "reddit_saas", "name": "r/SaaS", "url": "https://www.reddit.com/r/SaaS/submit",
     "categories": ("saas", "general"), "account_free": True,
     "note": "SaaS-founder-focused subreddit; share the build story, same etiquette as r/SideProject.",
     "verified_at": "2026-10-23"},
    {"id": "reddit_entrepreneur_ridealong", "name": "r/EntrepreneurRideAlong",
     "url": "https://www.reddit.com/r/EntrepreneurRideAlong/submit",
     "categories": ("saas", "general"), "account_free": True,
     "note": "Build-in-public-friendly subreddit for founders narrating their journey; welcomes "
             "progress/launch posts, not bare links.", "verified_at": "2026-10-23"},
    {"id": "reddit_artificial", "name": "r/artificial", "url": "https://www.reddit.com/r/artificial/submit",
     "categories": ("ai",), "account_free": True,
     "note": "General AI subreddit; relevant for AI-category products, same rule as every other "
             "subreddit here -- lead with substance, not a bare launch link.", "verified_at": "2026-10-23"},
    {"id": "reddit_roastmystartup", "name": "r/roastmystartup",
     "url": "https://www.reddit.com/r/roastmystartup/submit",
     "categories": ("saas", "general"), "account_free": True,
     "note": "Explicitly invites harsh feedback on a new product/landing page -- useful early-stage "
             "pre-launch validation thread, not just a launch-day announcement board.",
     "verified_at": "2026-10-23"},
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


#: Column order for CSV export, matching the catalog's own field names, with ``categories``
#: flattened from a tuple into a single ``;``-separated string so the file round-trips through a
#: spreadsheet without a nested-list column.
CSV_FIELDS = ("id", "name", "url", "categories", "account_free", "note", "verified_at")


def export_csv(platforms: tuple[dict[str, Any], ...], path: Path | str) -> Path:
    """Write ``platforms`` (e.g. from :func:`platforms_for_category`) to a CSV file at ``path``
    with a header row, so a founder can pull the catalog into their own spreadsheet or project
    tracker instead of only consuming it through the CLI's own commands."""
    out_path = Path(path)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for p in platforms:
            writer.writerow({
                "id": p["id"], "name": p["name"], "url": p["url"],
                "categories": ";".join(p["categories"]), "account_free": p["account_free"],
                "note": p["note"], "verified_at": p.get("verified_at", ""),
            })
    return out_path


def export_json(platforms: tuple[dict[str, Any], ...], path: Path | str) -> Path:
    """Write ``platforms`` to a JSON file at ``path`` as a plain list of objects (the same shape
    ``launchmaxxing directories --json`` prints to stdout), for scripting against the catalog
    without parsing CLI text output."""
    out_path = Path(path)
    out_path.write_text(json.dumps(list(platforms), indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def export_opml(platforms: tuple[dict[str, Any], ...], path: Path | str, *,
                title: str = "launchmaxxing launch directories") -> Path:
    """Write ``platforms`` to an OPML bookmark file at ``path`` -- the format feed readers and
    outliner apps (NetNewsWire, Inoreader's bookmark import, etc.) import, so a founder can drop
    the whole catalog straight into whatever bookmark/reading-list tool they already use instead
    of a spreadsheet. Each directory becomes one ``<outline>`` leaf with its submit URL, a
    ``category`` attribute (comma-separated, OPML's own convention for tagging an outline) and the
    catalog note as its ``description``."""
    out_path = Path(path)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0"><head>',
        f"<title>{_xml_escape(title)}</title>",
        "</head><body>",
    ]
    for p in platforms:
        lines.append(
            f'<outline text={_xml_quoteattr(p["name"])} type="link" url={_xml_quoteattr(p["url"])} '
            f'category={_xml_quoteattr(",".join(p["categories"]))} '
            f'description={_xml_quoteattr(p["note"])} />'
        )
    lines += ["</body></opml>"]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


__all__ = [
    "CSV_FIELDS",
    "PLATFORMS",
    "PLATFORM_BY_ID",
    "PLAYBOOK_STEPS",
    "STEP_BY_KEY",
    "all_categories",
    "export_csv",
    "export_json",
    "export_opml",
    "platforms_account_free",
    "platforms_for_category",
]
