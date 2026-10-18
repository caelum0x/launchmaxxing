"""launchmaxxing: a founder's first-100-users toolkit.

Four pieces, each useful standalone:

* :mod:`launchmaxxing.catalog` -- 18 real launch-directory listings (Product
  Hunt, BetaList, Hacker News, ...) and the 10-step first-100-users
  distribution playbook, as curated reference data.
* :mod:`launchmaxxing.backlinks` -- "where is my competitor listed/linked, so
  I submit there too" -- a free fallback list plus optional live lookups via
  a bring-your-own API key (CrawlGraph's free tier, or DataForSEO).
* :mod:`launchmaxxing.reddit_search` -- read-only Reddit search for threads
  where people complain about the problem your product solves, with a
  draft reply for each one. Nothing here posts, comments or votes; a human
  reviews and posts everything by hand.
* :mod:`launchmaxxing.state` -- a local JSON file that tracks which
  directories you have submitted to and which playbook steps you have done,
  per product, with zero server/database/account required.

:mod:`launchmaxxing.cli` wires all four into one command-line tool.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
