# launchmaxxing

A founder's first-100-users toolkit, as a single local CLI. No signup, no
server -- local state (JSON) plus a local SQLite database for history, both
on your own machine.

## Why

Getting your first 100 users is mostly an unglamorous checklist and pipeline
problem: which directories to submit to (and whether you actually did),
which outreach you sent and who still owes you a reply, what the launch
copy for each platform should say, which Reddit threads are worth replying
to, which competitors you should get backlinks from -- and whether, two
weeks into a launch, any of that is actually still moving. None of that
should require creating an account somewhere. `launchmaxxing` is that whole
loop, as a CLI you run once to plan a launch and keep running for weeks
after to track it.

## What's in it

- **82 real launch directories**, kept current for 2026 -- Product Hunt,
  BetaList, DevHunt, Peerlist, Hacker News (Show HN), Indie Hackers,
  Launching Next, SaaSHub, AlternativeTo, Futurepedia, There's An AI For
  That, G2, Capterra, Fazier, Uneed, TinyLaunch, r/SideProject, GitHub's
  awesome-lists, PeerPush (explicitly GEO-optimized for AI-assistant
  discovery -- ChatGPT, Perplexity, Claude/MCP, not just human visitors),
  Turbo0, Smol Launch, StartupBase, Microlaunch, Findly Tools, plus a
  2026-10-23 breadth pass that added 58 more across six new category
  families: AI-tool/GEO directories (AITools.fyi, Dang.ai, Future Tools,
  Aixploria, Toolify.ai, ...), browser-extension stores (Chrome Web Store,
  Edge, Firefox, Opera), API marketplaces (RapidAPI, Postman API Network,
  APIs.guru, the public-apis GitHub list), newsletter sponsor slots
  (Paved, Swapstack, Sidebar.io, beehiiv Ad Network), Slack/Discord
  community lists (Disboard, Discord.me, Discadia, Slofile), and
  vertical-SaaS/integration-ecosystem directories (Zapier, Make, Slack App
  Directory, Shopify App Store, WordPress Plugin Directory, Salesforce
  AppExchange, GetApp, TrustRadius, AppSumo Partners, and more) -- each
  with its real submission URL (verified live, not just the homepage) and
  a one-line note on how to use it well. Each
  directory is also tagged with a real `account_free` flag, so
  `directories --account-free` (combinable with `--category`) lists only
  the ones you can submit to without creating an account anywhere in the flow.
- **Live link check for the whole catalog (`directories --check-links`)** --
  the catalog's own accuracy is the tool's core promise, and three past
  releases (0.1.0 -> 0.2.1 -> 0.2.2) were all fixes for stale submit URLs or
  wrong `account_free` tags found only by manually trying to submit and
  hitting a 404 or an unexpected login wall. This automates that first
  check: a real HTTP request against every submit URL, flagging dead links,
  server errors, and redirects straight to a login/sign-in page, with a
  non-zero exit code for CI/scripting. Doesn't require an account or API
  key; `--category` scopes it to one category.
- **Submission tracking with full history**, not just current status --
  `submit` records every status change (not_started -> submitted -> live)
  with a timestamp in a local SQLite database, so `submit --history` shows
  the whole timeline, not just where things stand right now.
- **A 10-step first-100-users playbook** -- launch everywhere, cold
  outreach, Reddit pain-point threads, UGC creator outreach, where your
  ICP hangs out, competitor backlinks, a demo video, riding X/Twitter
  trends, building in public, and replying to viral tweets -- tracked
  per-product, locally.
- **A cross-cutting status dashboard (`track`)** -- one view of directories,
  checklist, outreach and content for one product, plus the reminders a
  human would otherwise forget: which directories have sat untouched past a
  threshold, and which outreach contacts are owed a follow-up.
- **Local, template-based launch-copy generation (`content`)** -- a
  Product Hunt tagline (hard-capped at 60 characters, hype words flagged)
  and description, a Show HN title in the real "Show HN: Name - what it is"
  format (hype words stripped, hard-capped at HN's real 80-character site
  limit), a 6-tweet X/Twitter launch thread, a problem-first Reddit post,
  and a LinkedIn build-in-public post -- generated locally from a small
  product profile you supply. No LLM call, no API key, deterministic output.
- **Local outreach pipeline (`outreach`)** -- track creator/press/
  community/user contacts with a status (not_contacted/contacted/replied/
  booked/declined) in the local database, plus a cold-outreach message
  draft per channel; `outreach send <contact_id>` actually sends a drafted
  message via your own SMTP credentials and records delivery status.
  `outreach list --csv contacts.csv` exports tracked contacts for a
  spreadsheet, and `outreach import "My Product" contacts.csv` bulk-adds
  them back (deduped by email/handle, so re-importing an updated list never
  creates duplicates) -- the real mail-merge loop. `outreach send-batch
  "My Product"` then drafts and actually sends to every matching contact
  with an email on file, one real SMTP send at a time with a polite
  `--delay`, `--limit` to cap a run, and `--dry-run` to preview first.
- **Local UTM link builder (`utm`)** -- this tool has no server to receive
  clicks, so instead of faking analytics it builds correctly tagged links
  (hand-curated per-directory source/medium defaults for all 82 catalog
  entries) and saves them locally, so you know which exact link you used
  where. Paste the result into whatever analytics you already run;
  `utm list --csv links.csv` exports the saved links to a CSV file.
- **Shareable one-page launch report (`report`)** -- a Markdown summary of
  everything tracked for one product, to paste into a doc or Slack instead
  of re-explaining launch status by hand.
- **Read-only pain-point search across Reddit, Hacker News and Stack
  Overflow** -- finds threads/questions where people complain about (or
  ask how to solve) the problem your product solves, and drafts a reply
  for each one. Stack Overflow searches both question titles and bodies
  via the free, keyless Stack Exchange API -- some of the highest-signal
  pain points anywhere, since the asker is already looking for exactly
  what a dev tool usually offers. It never posts, comments or votes on
  anything: every reply is a draft for you to read, edit and post
  yourself.
- **Competitor backlink lookup** -- "where is this competitor listed, so I
  submit there too." Works with zero setup (a free directory fallback
  list); add your own free [CrawlGraph](https://crawlgraph.com) API key
  (15 calls/month, no card) or a DataForSEO account for live backlink
  data. Never spends API credits unless you pass `--allow-live`.
- **Always-on watcher (`watch`)** -- polls the catalog's link health and
  outreach/directory staleness on an interval and fires a real native
  notification the moment something newly breaks: macOS Notification
  Center, Linux `notify-send`, or a Windows balloon tip. Falls back to a
  stdout log line anywhere none of those is available; never crashes for
  lacking one.

Nothing here auto-posts, auto-emails or auto-DMs anything, anywhere. Every
write is local, and every "share this" action is a draft a human reviews
and sends themselves.

## Install

Not yet on PyPI (see [RELEASE.md](./RELEASE.md)) -- `pip install` directly
from the tagged GitHub release works today, no local clone required:

```bash
pip install "git+https://github.com/caelum0x/launchmaxxing.git@v0.2.4"
# or, once published to PyPI:
pip install launchmaxxing
```

From a local clone instead:

```bash
git clone https://github.com/caelum0x/launchmaxxing.git
cd launchmaxxing
pip install -e .
```

Requires Python 3.10+. No other services required -- the local SQLite
database uses Python's built-in `sqlite3`, no extra dependency.

## Get value in under 5 minutes

```bash
launchmaxxing init "My Product"
```

This prints your full launch plan: all 82 directories to submit to, plus
the 10-step playbook with progress tracked locally, and the commands to
keep working the launch afterward.

## Run it repeatedly over a multi-week launch

`init` gives you the plan once. These are the commands you come back to:

```bash
# Record a submission -- full history is kept, not just current status
launchmaxxing submit "My Product" product_hunt submitted --note "posted 00:01 PT"
launchmaxxing submit "My Product" product_hunt live
launchmaxxing submit "My Product" --history           # the whole timeline
launchmaxxing submit "My Product" product_hunt --history   # one platform's timeline

# Generate launch copy for one platform, or all of them
launchmaxxing content "My Product" product_hunt \
  --tagline "Ship launch-ready copy in one command" \
  --problem "Founders waste hours retyping launch copy for every directory" \
  --audience "founders and small teams launching SaaS" \
  --differentiator "generates platform-correct copy locally, no API key" \
  --save
launchmaxxing content "My Product" all --profile-file profile.json --save

# Track outreach -- creators, press, communities, individual users
launchmaxxing outreach add "My Product" "Jane Creator" creator --handle "@jane"
launchmaxxing outreach draft "My Product" creator --profile-file profile.json
launchmaxxing outreach list "My Product" --status contacted
launchmaxxing outreach list "My Product" --csv contacts.csv
launchmaxxing outreach status <contact_id> replied --note "said yes, posting Friday"

# Build + save a UTM-tagged link for one directory
launchmaxxing utm build "My Product" https://myproduct.example --platform-id product_hunt
launchmaxxing utm list "My Product"
launchmaxxing utm list "My Product" --csv links.csv

# The cross-cutting dashboard: directories, checklist, outreach, content, stale reminders
launchmaxxing track "My Product"
launchmaxxing track "My Product" --stale-days 3 --json

# A shareable one-page Markdown report
launchmaxxing report "My Product" --out launch-report.md
```

`--profile-file profile.json` is a small JSON file so you don't retype the
product profile on every call:

```json
{
  "tagline": "Ship launch-ready copy in one command",
  "problem": "Founders waste hours retyping launch copy for every directory",
  "audience": "founders and small teams launching SaaS",
  "differentiator": "generates platform-correct copy locally, no API key",
  "url": "https://myproduct.example",
  "subreddit": "SaaS"
}
```

## All commands

```bash
# Directories, optionally filtered by category
# (ai, ai_discovery, saas, dev_tool, oss, app, general)
launchmaxxing directories --category ai

# Live-check every submit URL in the catalog (or one category's); exits 1 if any are broken
launchmaxxing directories --check-links
launchmaxxing directories --category ai --check-links --json

# Submission tracking with history (submit is the current command;
# platform-status is kept working as a deprecated alias)
launchmaxxing submit "My Product" product_hunt submitted
launchmaxxing submit "My Product" --history

# The 10-step checklist for one product
launchmaxxing checklist "My Product"
launchmaxxing checklist-step "My Product" cold_outreach done

# Local, template-based launch copy (product_hunt, show_hn, twitter, reddit, linkedin, all)
launchmaxxing content "My Product" product_hunt --tagline "..." --problem "..." \
  --audience "..." --differentiator "..."

# Local outreach pipeline
launchmaxxing outreach add "My Product" "Some Creator" creator
launchmaxxing outreach list "My Product"
launchmaxxing outreach status <contact_id> replied
launchmaxxing outreach draft "My Product" press --profile-file profile.json

# Local UTM link builder
launchmaxxing utm build "My Product" https://myproduct.example
launchmaxxing utm list "My Product"

# Cross-cutting status dashboard + shareable report
launchmaxxing track "My Product"
launchmaxxing report "My Product"

# Competitor backlinks (free fallback by default)
launchmaxxing backlinks competitor.com
launchmaxxing backlinks competitor.com --category ai --account-free  # narrow the free fallback list
CRAWLGRAPH_API_KEY=... launchmaxxing backlinks competitor.com --allow-live

# Reddit pain-point threads + draft replies (read-only, nothing is posted)
launchmaxxing pain-points "struggling with onboarding" --subreddit SaaS --product "My Product"
launchmaxxing drafts --status drafted
launchmaxxing draft-status <draft_id> approved

# Machine-readable output for any command
launchmaxxing checklist "My Product" --json
```

Current-status state is stored at `~/.launchmaxxing/state.json` by default
(override with `--state-file <path>` or `$LAUNCHMAXXING_STATE`). History --
submission events, outreach contacts, content drafts, UTM links -- lives in
a local SQLite database at `~/.launchmaxxing/launchmaxxing.db` by default
(override with `--db-file <path>` or `$LAUNCHMAXXING_DB`). Both are plain
files you own; inspect the database directly with
`sqlite3 ~/.launchmaxxing/launchmaxxing.db` any time.

## Development

```bash
pip install -e ".[dev]"
pytest --cov=launchmaxxing --cov-report=term-missing
```

## License

MIT, see [LICENSE](./LICENSE).

---

Built by the team behind [Menivor](https://menivor.com) -- AI video
creation for founders launching products. `launchmaxxing` is free and open
source, built to scratch our own itch while shipping Menivor; Menivor is
the paid product that funds it.
