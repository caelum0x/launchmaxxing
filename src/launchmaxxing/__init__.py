"""launchmaxxing: a founder's first-100-users toolkit.

Ten pieces, each useful standalone:

* :mod:`launchmaxxing.catalog` -- 24 real launch-directory listings (Product
  Hunt, BetaList, Hacker News, PeerPush, Turbo0, ...) and the 10-step
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
  generator (Product Hunt tagline/description, Show HN title, X/Twitter
  thread, Reddit post, LinkedIn post) from a small local product profile.
  No LLM call, no API key.
* :mod:`launchmaxxing.outreach` -- cold-outreach message drafts per channel
  (creator/press/community/user), paired with the SQLite contact pipeline.
* :mod:`launchmaxxing.utm` -- a local UTM link builder so you know which
  tagged link you used where, for whatever analytics you already run.
* :mod:`launchmaxxing.report` -- a shareable one-page Markdown launch
  summary assembled from the dashboard.
* :mod:`launchmaxxing.backlinks` -- "where is my competitor listed/linked, so
  I submit there too" -- a free fallback list plus optional live lookups via
  a bring-your-own API key (CrawlGraph's free tier, or DataForSEO).
* :mod:`launchmaxxing.reddit_search` -- read-only Reddit search for threads
  where people complain about the problem your product solves, with a
  draft reply for each one. Nothing here posts, comments or votes; a human
  reviews and posts everything by hand.
* :mod:`launchmaxxing.linkcheck` -- a live reachability check for every
  catalog submit URL, flagging dead links and redirects to a login page so
  catalog staleness is caught automatically instead of by manually
  submitting and hitting a 404.

:mod:`launchmaxxing.cli` wires all of it into one command-line tool.
"""

from __future__ import annotations

__version__ = "0.2.3"

__all__ = ["__version__"]
