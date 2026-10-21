# Changelog

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
