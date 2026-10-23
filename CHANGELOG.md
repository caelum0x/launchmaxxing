# Changelog

## 0.3.3 -- 2026-10-23

### Added

- **`watch --notify-email`**. A real email-delivery channel for `watch`'s alerts, for a headless
  server or any machine without a native OS notification mechanism (and for anyone who just
  wants an email trail alongside a desktop popup) -- sends via the same SMTP credentials
  `outreach send`/`send-batch` already use, only ever to the one address you configure it with
  (never a contact, never automatically discovered). `watch.compose_notifiers` combines it with
  the existing native notifier so both fire for the same event; fails fast with a clear setup
  error before the poll loop ever starts if SMTP isn't configured.

### Fixed

- `watch`'s "no native notifications" log line still said "need macOS (osascript)" after 0.3.1
  added real Linux/Windows support -- it now names the actual reason (missing `notify-send` on
  Linux, or an unrecognized platform) and only fires when the caller is actually relying on the
  native notifier (not when `--notify-email` is already covering alerting).

## 0.3.2 -- 2026-10-23

### Added

- **Stack Overflow added as a fourth pain-point source.** `pain-points` now also searches
  Stack Overflow question titles *and* bodies (not just titles) via the free, keyless Stack
  Exchange API, sorted by score -- some of the highest-signal pain points anywhere, since a
  developer asking "how do I do X" or "is there a tool for Y" is already looking for exactly
  what a dev tool/SaaS product usually offers. No API key required (shared anonymous 300
  request/day quota). `painpoints.SOURCES`/`SOURCE_LABELS` gained `"stack_overflow"`, so
  `pain-points --source stack_overflow` works immediately and it's included by default
  alongside Reddit, Hacker News and the best-effort Indie Hackers source.

## 0.3.1 -- 2026-10-23

### Added

- **Real mail-merge batch mode for `outreach`.** Two new commands close the loop started by
  `outreach list --csv`: `outreach import <product> <csv_file>` bulk-adds contacts from a CSV
  (case-insensitive header matching, dedupes against already-tracked contacts by email/handle so
  re-importing an updated list never creates duplicates, skips malformed rows with a reason
  instead of aborting the file), and `outreach send-batch <product>` actually drafts and sends
  the channel-appropriate message to every tracked contact matching `--status`/`--channel` with a
  resolvable email, one real SMTP send per contact with a polite `--delay` between sends,
  `--limit` to cap a run, `--resend` to intentionally re-send, and `--dry-run` to preview a whole
  batch without opening an SMTP connection. The to-email resolution logic (explicit override ->
  `email` column -> `handle` when it looks like one) is now a single shared
  `outreach.resolve_recipient_email`, used by both the original single `outreach send` and the
  new batch command so the two can never drift.
- **Cross-platform native notifications for `watch`.** `watch.notify` now works on Linux
  (`notify-send`, detected at import time so a headless box without a notification daemon
  correctly reports `NOTIFY_SUPPORTED = False` instead of silently failing every poll) and Windows
  (a one-shot PowerShell `System.Windows.Forms.NotifyIcon` balloon tip, no extra module required)
  in addition to the existing macOS `osascript` support -- `watch` fires a real native popup on
  all three platforms it's actually likely to run on, not just macOS.
- **Hand-curated UTM defaults for all 82 catalog entries.** The 58 directories added in 0.3.0
  (AI-tool directories, browser-extension stores, API marketplaces, newsletter sponsor slots,
  Slack/Discord community lists, integration marketplaces, review sites, and four more
  subreddits) now have a real per-platform `utm_source`/`utm_medium` pair in
  `utm.PLATFORM_UTM_DEFAULTS` (e.g. `chrome_web_store` -> `extension_store`, `rapidapi` ->
  `api_marketplace`, `appsumo_partners` -> `marketplace`) instead of falling back to the generic
  id-derived default every one of them previously used.

## 0.3.0 -- 2026-10-23

### Added

- **Catalog expanded from 24 to 82 directories.** Added 58 new entries across six category
  families identified as the single biggest competitive gap vs. SubmitMap (366), OpenLaunch
  (239) and SubmitFleet (339) in `STRATEGY-2026-10-23.md`: AI-tool/GEO directories (AITools.fyi,
  Dang.ai, Future Tools, Aixploria, Toolify.ai, Tools Navigator, AI Tool Mall, Insidr.ai),
  browser-extension stores (Chrome Web Store, Edge, Firefox, Opera), API marketplaces (RapidAPI,
  Postman API Network, APIs.guru, the public-apis GitHub list), newsletter sponsor slots (Paved,
  Swapstack, Sidebar.io, beehiiv Ad Network), Slack/Discord community lists (Disboard,
  Discord.me, Discadia, Slofile), and vertical-SaaS/integration-ecosystem directories (Zapier,
  Make, Slack App Directory, Zoom, Shopify, WooCommerce, WordPress, Notion, Atlassian, Google
  Workspace, Salesforce AppExchange, HubSpot, GetApp, Software Advice, TrustRadius, SourceForge,
  Crozdesk, GoodFirms, FeaturedCustomers, Slant, AppSumo Partners, Crunchbase, BetaPage,
  NoCodeList, NoCodeFinder, YC Launches, StackShare, Console.dev, plus four more Reddit
  communities). Every URL live-verified by direct HTTP fetch on 2026-10-23.
- **`dashboard`/`serve` -- a shareable static HTML visual artifact.** New `dashboard.py` module
  renders the full `track` payload as one self-contained HTML file with inline CSS/SVG progress
  rings and a submission timeline (no CDN asset, no network request). `launchmaxxing dashboard`
  writes it to disk; `launchmaxxing serve` runs a localhost-only `http.server` that re-renders on
  every request for a live view. `report --html` reuses the same template; `report --json` emits
  the raw dashboard payload.
- **`dogfood` -- launchmaxxing submits itself.** New `dogfood.py` module runs the tool's own
  `content` generator against launchmaxxing's real product profile for every catalog directory
  it has added but not yet self-submitted to (PeerPush, Turbo0, Smol Launch, StartupBase,
  Microlaunch, Findly Tools), writing ready-to-paste copy to `launch-evidence/`. Never
  auto-submits anywhere; `--mark-submitted` only records the tracker status after a human
  confirms they did the real paste-and-click submission.
- **`init --interactive` -- a step-by-step onboarding wizard.** Prompts for
  tagline/problem/audience/differentiator/url/pricing/subreddit and saves the answers as the
  product's default profile (`state.set_default_profile`/`get_default_profile`); `content` and
  `outreach draft` now read that default automatically, so neither needs every flag re-supplied
  on every call once a product has been initialized interactively.
- **`outreach send` -- actually sends a drafted message.** New SMTP sending path in `outreach.py`
  (`send_email`, reading `LAUNCHMAXXING_SMTP_*` env vars -- the user's own mail provider, zero
  third-party account) moves outreach from draft-only to drafted-and-actually-sent-and-tracked.
  `outreach_contacts` gained `email`/`sent_at`/`send_status`/`send_error` columns (migrated onto
  existing databases automatically via `ALTER TABLE`); a successful send auto-advances a
  `not_contacted` contact to `contacted`.
- **`portfolio` -- cross-product rollup.** New `portfolio.py` module/command aggregates every
  product with recorded activity (JSON state or SQLite) into one table: directory/checklist
  completion %, outreach replies, and last-active/stale flag -- for a founder or studio running
  several launches at once.
- **`content` gained five more platform generators.** `indie_hackers`, `ask_hn`,
  `cold_pitch_email`, `community_intro`, and `newsletter_sponsor_pitch`, each with its own
  tone/length rules (mirroring the existing Show HN/Product Hunt generators), bringing
  `CONTENT_PLATFORMS` from 5 to 10.
- **Pain-point search merged across three sources.** New `painpoints.py` module adds Hacker News
  (Algolia's free, keyless HN Search API) and a best-effort Indie Hackers source (honestly
  reports itself as blocked -- confirmed Cloudflare-gated on every route tried -- rather than
  faking coverage) alongside the existing Reddit search. `pain-points` gained `--source` to
  restrict to one source; one source failing no longer fails the whole command.
- **`watch` -- always-on background poll.** New `watch.py` module/command re-runs
  `directories --check-links` and `track`'s stale-directory/stale-outreach detection on an
  interval, firing a native macOS notification (`osascript`, no account/server) the moment
  something *newly* breaks or goes stale -- degrades to a stdout log on non-macOS instead of
  crashing.
- **`backlinks --competitors file.txt`.** Multi-competitor mode (`fetch_many`) runs the lookup
  across a list of named competitor domains in one pass and unions/dedupes the directories
  they're findable through (cross-referenced against real backlink data when `--allow-live` is
  set, or the category fallback otherwise) into one combined "submit here too" list, exportable
  via `--export csv`.
- **`report --html`/`--json`.** The one-page summary is no longer Markdown-only; `--html` reuses
  the `dashboard` template, `--json` exposes the full `track` payload for piping into other tools.
- **Checklist auto-derivation expanded.** `cold_outreach` now auto-derives once any outreach
  contact moves past `not_contacted`; `reddit_pain_points` auto-derives once any pain-point draft
  (any source) is approved or dismissed -- previously only `launch_everywhere` auto-derived.
- **`compare` -- the competitor comparison table as data.** New `compare.py` module holds the
  factual launchmaxxing-vs-SubmitMap/OpenLaunch/SubmitFleet/paid-services comparison already
  researched in `STRATEGY-2026-10-23.md`, printable as text/JSON or a ready-to-paste README
  Markdown table (`--markdown`/`--out`) -- regenerable, not hand-written prose that goes stale.
- **`directories --export csv|json|opml`.** The full (optionally `--category`-filtered) catalog
  can now be exported for a spreadsheet, script, or feed-reader/bookmark-tool import, instead of
  only being consumable through the CLI's own commands.

## 0.2.6 -- 2026-10-23

### Fixed

- **`state.save()` writes atomically.** Previously `state.json` was written with a
  single direct `write_text()` call; a process killed mid-write (crash, `kill -9`,
  power loss) could leave a truncated or corrupted file with no recovery path, since
  `load()`'s `json.JSONDecodeError` handler would then silently reset to empty state
  on the next run, discarding all saved progress. `save()` now writes to a temp file
  in the same directory (`tempfile.mkstemp`), `fsync`s it, then `os.replace()`s it
  into place -- a process killed at any point leaves either the complete old file or
  the complete new one, never a partial write; on an unexpected error the temp file
  is removed and the original `state.json` is left untouched. 2 new tests
  (`tests/test_state.py`); 214/214 passing.

## 0.2.5 -- 2026-10-23

### Added

- **`backlinks` now accepts `--category`/`--account-free`, same as `directories`.**
  Previously `backlinks <domain>`'s free fallback always returned all 24 catalog
  directories regardless of the competitor's actual category, even though `directories`
  has supported `--category`/`--account-free` filtering since 0.1. A founder in `ai` or
  `dev_tool` got the same generic "submit here too" list as a general SaaS founder,
  diluting the one piece of free value `backlinks` offers when no CrawlGraph/DataForSEO
  key is configured (the common case -- neither is set up yet for this repo). Added
  `category`/`account_free_only` params to `backlinks.fetch()`/`_fallback()` (ignored
  once a live provider answers, since live rows come from the real link graph, not the
  catalog) and matching `--category`/`--account-free` flags on the CLI. 6 new tests
  (`test_backlinks.py`, `test_cli.py`); 212/212 passing.

## 0.2.4 -- 2026-10-22

### Fixed

- **`launching_next`'s submit URL was stale and 404ing live.** The catalog stored
  `https://launchingnext.com/submit` (no `www.`, no trailing slash); the live site now
  enforces both the `www.` host and the trailing slash, so the stored URL 404ed while
  `https://www.launchingnext.com/submit/` returns a real `200` with a plain,
  account-free `<form method="post">`. Found by running the `0.2.3 directories
  --check-links` feature against the live catalog the day after it shipped -- exactly
  the kind of regression it exists to catch. Notable because Launching Next was the one
  directory CHANGELOG 0.2.1 confirmed "genuinely account-free end-to-end" via a real
  POST, and real submissions for ereboslab, lawsynth and scribase went through it (see
  `launch-evidence/`); a stale URL here would have silently broken the most-trusted
  account-free directory in the catalog. Corrected the URL, added a regression test
  (`test_launching_next_url_is_the_live_www_and_trailing_slash_form`) pinning the exact
  live form, and re-ran `--check-links` against the full catalog: of the 24 entries, only
  5 now fail, all already-documented Cloudflare/bot-wall cases (`indie_hackers`,
  `alternativeto`, `there_is_an_ai_for_that`, `g2`, `capterra`) with notes that already
  explain why -- no other stale URLs.

### Distribution

- **A third real `github_awesome` submission for launchmaxxing itself**: opened
  [bekatom/awesome-growth-hacking#111](https://github.com/bekatom/awesome-growth-hacking/pull/111),
  adding launchmaxxing to that list's `Tools` section (540-star awesome list, actively
  merging CLI-tool entries in the same format). Joins the existing Launching Next
  submission (queue `#165019`) and the
  [toolleeo/awesome-cli-apps-in-a-csv#536](https://github.com/toolleeo/awesome-cli-apps-in-a-csv/pull/536)
  PR as the tool's own real, tracked launch -- recorded with its own `submit` command
  (`launchmaxxing submit launchmaxxing github_awesome submitted --note ...`), confirming
  `submit --history` and `track` surface all three events correctly end to end. Full
  `pytest` suite re-run clean (206 passed) and `directories --check-links` re-verified
  against the live catalog (19/24 reachable, same 5 already-documented cases) as part of
  this pass.

## 0.2.3 -- 2026-10-21

### Added

- **`directories --check-links`** -- a live HTTP check of every submit URL
  in the catalog (or one `--category`'s), flagging dead links (4xx/5xx) and
  redirects straight to a login/sign-in page, with a non-zero exit code so
  it can gate a release. This automates exactly the manual "try to submit,
  hit a 404" discovery process that produced the stale-URL fixes in 0.2.1
  and 0.2.2 -- the catalog's own accuracy is this tool's core promise, and
  it was previously only checked by hand.

### Fixed

- **Generated X/Twitter launch thread had no character-limit enforcement.**
  Unlike every other platform template here (Product Hunt tagline/
  description, Show HN title all cap to their real limits), a profile with
  a longer-than-average problem/audience/differentiator produced tweets up
  to 365 characters -- well over X/Twitter's real 280-character-per-post
  limit, so the generated thread would fail to post as written. Added
  `content.TWITTER_TWEET_MAX` and truncate each tweet on a word boundary.
- **`indie_hackers`'s catalog note didn't mention its Cloudflare bot
  check** -- found dogfooding the new `--check-links` feature against the
  live catalog: `/post/new` returns a 403 even with a real-browser
  User-Agent via `curl` (confirmed separately from the automated check).
  Noted as a bot-check, not a dead URL, matching the existing notes on
  `alternativeto`, `there_is_an_ai_for_that`, `g2` and `capterra`.

## 0.2.2 -- 2026-10-21

Dogfooded by launching `launchmaxxing` itself through its own catalog: real
submission to Launching Next (queue `#165019`) and a real pull request
adding it to `toolleeo/awesome-cli-apps-in-a-csv` (a 2.6k-star awesome
list), which is exactly what the `github_awesome` playbook step describes.
The two fixes below were both found during that dogfooding pass.

### Fixed

- **`launchmaxxing --version` reported a stale version.** `__version__` in
  `src/launchmaxxing/__init__.py` was never bumped past `"0.2.0"` across the
  0.2.0 -> 0.2.1 release, so the CLI's own `--version` flag silently lied
  about what was installed. Bumped to match `pyproject.toml` and added a
  regression test that keeps the two in sync going forward.
- **Generated launch copy truncated mid-word.** `_truncate` (used by the
  Product Hunt description, Show HN title, etc.) was a hard character cut
  that could land in the middle of a word (e.g. "...no account or se..."
  instead of "...no account or..."). Found dogfooding `content` on
  `launchmaxxing` itself. Now prefers the nearest word boundary within the
  character budget, falling back to a hard cut only when there's no usable
  space to break on (e.g. a single long token) or breaking there would
  waste too much of the budget.
- **`account_free` mistagged for 3 directories** -- `g2`, `capterra` and
  `alternativeto` were tagged `account_free: True` even though their own
  submit URLs are literally account/vendor sign-up pages
  (`capterra.com/vendors/sign-up`, `g2.com` requires a seller account via
  sell.g2.com, `alternativeto.net/account/add-software/`). This matters
  because `directories --account-free` is the tool's own promise of "only
  the ones you can submit to without creating an account anywhere in the
  flow" -- these three broke that promise. Corrected to `account_free:
  False` with notes explaining why.

## 0.2.1 -- 2026-10-18

Dogfooded end-to-end on two real products (a live-traffic AI VTuber site and
an open-source "awesome" list). Patches catalog accuracy issues found during
that real launch, same day as the catalog's last "verified live" pass.

### Fixed

- **3 stale submit URLs** now 404 and have been corrected or pointed at a
  stable fallback: `devhunt` (`/submit` -> `/login`, the site's own nav now
  sends "Submit" straight to login), `tinylaunch` (`/launches/new` -> the
  homepage; no stable direct submit URL exists in the static page anymore),
  `futurepedia` (`/submit-tool` -> the homepage; submit flow is behind
  client-side JS with no stable direct URL).
- **Login-required reality corrected in notes** for `uneed`, `peerpush`,
  `turbo0`, `smol_launch`, `startupbase`, `findly_tools`: all six either
  redirect straight to a login/sign-in route, or let you paste a URL for
  free but then gate finishing/publishing the listing behind account
  creation. The notes previously read as more account-free than they are in
  practice; they now say exactly what was observed on a real submission
  attempt that day.
- `there_is_an_ai_for_that`'s note now mentions the Cloudflare JS challenge
  on `/add/` that blocks plain HTTP clients.
- Only `launching_next` was confirmed genuinely account-free end-to-end: a
  plain HTML POST to `https://www.launchingnext.com/submit/` with no cookies
  or CSRF token returns a real `302` to a `/thanks/?i=...` confirmation page.

## 0.2.0 -- 2026-10-18

Renamed from `launchroster` to `launchmaxxing` (GitHub repo renamed in
place; old clones/stars carry over via GitHub's redirect). Everything below
shipped in the same pass as a genuine v2, not a cosmetic rename.

### Added

- **SQLite-backed history layer** (`launchmaxxing.db`, default
  `~/.launchmaxxing/launchmaxxing.db`, override with `--db-file` /
  `$LAUNCHMAXXING_DB`) for everything that needs an append-only history
  instead of a current-status snapshot: submission events, outreach
  contacts, content drafts, UTM links. The original JSON state file stays
  the source of truth for current directory/checklist status.
- **`submit`** -- the new primary command for recording directory
  submissions, replacing `platform-status` (kept working as a deprecated
  alias). Every status change is now logged with a timestamp;
  `submit <product> --history` shows the full timeline, optionally scoped
  to one platform.
- **`content`** -- local, template-based launch-copy generation for
  Product Hunt (tagline + description, with character limits enforced and
  hype words flagged), Show HN (real title format, hype words stripped,
  hard-capped at HN's 80-character limit), X/Twitter (6-tweet thread),
  Reddit (problem-first post) and LinkedIn (build-in-public post). Pure
  text templating -- no LLM call, no API key, deterministic.
- **`outreach`** -- a local contact pipeline (`add`/`list`/`status`) for
  creator/press/community/user outreach, plus `outreach draft` for a
  per-channel cold-message starting point.
- **`utm`** -- a local UTM link builder (`build`/`list`) with sensible
  per-directory source/medium defaults for all 24 catalog entries.
- **`track`** -- a cross-cutting status dashboard for one product:
  directories, checklist, outreach and content in one view, plus stale/
  overdue reminders (directories untouched past a threshold, outreach
  contacts owed a follow-up).
- **`report`** -- a shareable one-page Markdown launch summary assembled
  from the `track` dashboard.
- **6 new launch directories**, researched and verified live on 2026-10-18:
  PeerPush (explicitly GEO/AI-assistant-optimized), Turbo0, Smol Launch,
  StartupBase, Microlaunch, Findly Tools. Catalog grew from 18 to 24
  entries; a new `ai_discovery` category tags AI-assistant-discovery-first
  directories.
- `state.get_product_created_at` -- tracks when a product was first
  touched, powering `track`'s staleness reminders.

### Changed

- Package, CLI entry point, internal imports, and all documentation renamed
  from `launchroster` to `launchmaxxing`.

## 0.1.0 -- 2026-10-18

Initial release: 18 launch directories, the 10-step first-100-users
playbook, read-only Reddit pain-point search with draft replies, and
competitor backlink lookup (free fallback, optional bring-your-own-key
live lookups). Extracted from Menivor's internal Launch Kit feature.
