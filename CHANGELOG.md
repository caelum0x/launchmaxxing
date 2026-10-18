# Changelog

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
