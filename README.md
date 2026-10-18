# launchroster

A founder's first-100-users toolkit, as a single local CLI. No signup, no
server, no database -- state lives in one JSON file on your own machine.

## Why

Getting your first 100 users is mostly a checklist problem: which
directories to submit to, which Reddit threads to reply to, which
competitors you should get backlinks from, and whether you actually did any
of it last week. That checklist shouldn't require creating an account
somewhere. `launchroster` is that checklist, as a CLI you run locally.

## What's in it

- **18 real launch directories** -- Product Hunt, BetaList, DevHunt,
  Peerlist, Hacker News (Show HN), Indie Hackers, Launching Next, SaaSHub,
  AlternativeTo, Futurepedia, There's An AI For That, G2, Capterra, Fazier,
  Uneed, TinyLaunch, r/SideProject, and GitHub's awesome-lists -- each with
  its real submission URL (not just the homepage) and a one-line note on
  how to use it well.
- **A 10-step first-100-users playbook** -- launch everywhere, cold
  outreach, Reddit pain-point threads, UGC creator outreach, where your
  ICP hangs out, competitor backlinks, a demo video, riding X/Twitter
  trends, building in public, and replying to viral tweets -- tracked
  per-product, locally.
- **Read-only Reddit pain-point search** -- finds threads where people
  complain about the problem your product solves, and drafts a reply for
  each one. It never posts, comments or votes on anything: every reply is
  a draft for you to read, edit and post yourself.
- **Competitor backlink lookup** -- "where is this competitor listed, so I
  submit there too." Works with zero setup (a free directory fallback
  list); add your own free [CrawlGraph](https://crawlgraph.com) API key
  (15 calls/month, no card) or a DataForSEO account for live backlink
  data. Never spends API credits unless you pass `--allow-live`.

Nothing here auto-posts anything, anywhere. Every write is local, and
every "share this" action is a draft a human reviews.

## Install

```bash
pip install -e .
# or, once published:
pip install launchroster
```

Requires Python 3.10+.

## Get value in under 5 minutes

```bash
launchroster init "My Product"
```

This prints your full launch plan: all 18 directories to submit to, plus
the 10-step playbook with progress tracked locally. Example output:

```
Launch plan for My Product
===========================

Step 1: submit to these 18 directories

  - Product Hunt -- https://www.producthunt.com/posts/new
  - BetaList -- https://betalist.com/submit
  ...

Full 10-step playbook (0/10 done):

  [ ] Launch everywhere -- Product Hunt, DevHunt, BetaList, Peerlist, Show HN and the other listing sites.
  [ ] Network + cold outreach -- Friends, ex-colleagues, LinkedIn, one-sentence personalized cold email.
  ...

Mark progress any time with:
  launchroster platform-status "My Product" product_hunt submitted
  launchroster checklist-step "My Product" cold_outreach done
```

## All commands

```bash
# Directories, optionally filtered by category (ai, saas, dev_tool, oss, app, general)
launchroster directories --category ai

# Record what you actually submitted
launchroster platform-status "My Product" product_hunt submitted

# The 10-step checklist for one product
launchroster checklist "My Product"
launchroster checklist-step "My Product" cold_outreach done

# Competitor backlinks (free fallback by default)
launchroster backlinks competitor.com
CRAWLGRAPH_API_KEY=... launchroster backlinks competitor.com --allow-live

# Reddit pain-point threads + draft replies (read-only, nothing is posted)
launchroster pain-points "struggling with onboarding" --subreddit SaaS --product "My Product"
launchroster drafts --status drafted
launchroster draft-status <draft_id> approved

# Machine-readable output for any command
launchroster checklist "My Product" --json
```

State is stored at `~/.launchroster/state.json` by default; override with
`--state-file <path>` or the `LAUNCHROSTER_STATE` environment variable.

## Development

```bash
pip install -e ".[dev]"
pytest --cov=launchroster --cov-report=term-missing
```

## License

MIT, see [LICENSE](./LICENSE).

---

Built by the team behind [Menivor](https://menivor.com) -- AI video
creation for founders launching products. `launchroster` is free and open
source, built to scratch our own itch while shipping Menivor; Menivor is
the paid product that funds it.
