"""launchmaxxing: a founder's first-100-users toolkit.

Seventeen pieces, each useful standalone:

* :mod:`launchmaxxing.catalog` -- 80+ real launch-directory listings (Product
  Hunt, BetaList, Hacker News, PeerPush, Turbo0, browser-extension stores,
  API marketplaces, newsletter sponsor slots, Slack/Discord community
  lists, integration marketplaces, and more) and the 10-step
  first-100-users distribution playbook, as curated reference data.
* :mod:`launchmaxxing.state` -- a local JSON file that tracks which
  directories you have submitted to and which playbook steps you have done,
  per product, with zero server/database/account required.
* :mod:`launchmaxxing.db` -- a local SQLite database for everything that
  needs real history instead of a current-status snapshot: submission
  events, an outreach-contact pipeline, generated content drafts and UTM
  links. Still one file on disk, still zero signup.
* :mod:`launchmaxxing.track` -- the cross-cutting status dashboard for one
  product: directories, checklist, outreach and content, plus stale/overdue
  reminders.
* :mod:`launchmaxxing.content` -- a deterministic, template-based launch-copy
  generator (Product Hunt, Show HN, Ask HN, X/Twitter, Reddit, LinkedIn,
  Indie Hackers, cold-pitch email, Discord/Slack community intro, newsletter
  sponsor pitch) from a small local product profile. No LLM call, no API key.
* :mod:`launchmaxxing.outreach` -- cold-outreach message drafts per channel
  (creator/press/community/user), paired with the SQLite contact pipeline,
  plus actually *sending* a drafted message via the user's own SMTP
  credentials (zero third-party account), a CSV mail-merge importer for
  bulk-adding contacts, and a batch sender that mail-merges and actually
  sends to every matching tracked contact with a polite delay between
  sends.
* :mod:`launchmaxxing.utm` -- a local UTM link builder so you know which
  tagged link you used where, for whatever analytics you already run.
* :mod:`launchmaxxing.report` -- a shareable launch summary assembled from
  the dashboard, as Markdown (default), JSON, or the full HTML dashboard.
* :mod:`launchmaxxing.dashboard` -- a self-contained static HTML dashboard
  (inline CSS/SVG progress rings + a submission timeline), plus a localhost-
  only live-refreshing ``serve`` view.
* :mod:`launchmaxxing.backlinks` -- "where is my competitor listed/linked, so
  I submit there too" -- a free fallback list plus optional live lookups via
  a bring-your-own API key (CrawlGraph's free tier, or DataForSEO), with a
  multi-competitor mode that unions/dedupes a combined "submit here too" CSV.
* :mod:`launchmaxxing.reddit_search` -- read-only Reddit search for threads
  where people complain about the problem your product solves, with a
  draft reply for each one. Nothing here posts, comments or votes; a human
  reviews and posts everything by hand.
* :mod:`launchmaxxing.painpoints` -- the same read-only pain-point search,
  merged across Reddit, Hacker News (Algolia's free HN Search API) and a
  best-effort Indie Hackers source that honestly reports itself as blocked
  rather than faking coverage.
* :mod:`launchmaxxing.linkcheck` -- a live reachability check for every
  catalog submit URL, flagging dead links and redirects to a login page so
  catalog staleness is caught automatically instead of by manually
  submitting and hitting a 404.
* :mod:`launchmaxxing.watch` -- an always-on background poll that re-runs
  the link-check/stale-reminder detection on an interval and fires a native
  notification (macOS Notification Center, Linux ``notify-send``, or a
  Windows balloon tip) the moment something newly breaks or goes stale.
* :mod:`launchmaxxing.portfolio` -- a cross-product rollup table for a
  founder or studio running several simultaneous launches.
* :mod:`launchmaxxing.compare` -- the factual competitor comparison table
  (vs. SubmitMap/OpenLaunch/SubmitFleet/paid services) as regenerable data,
  not hand-written prose that goes stale.
* :mod:`launchmaxxing.dogfood` -- runs this tool's own content generator
  against launchmaxxing's real product profile for every catalog directory
  it has added but not yet self-submitted to, writing ready-to-paste copy
  (never auto-submitting anything).

:mod:`launchmaxxing.cli` wires all of it into one command-line tool.
"""

from __future__ import annotations

__version__ = "0.3.1"

__all__ = ["__version__"]
