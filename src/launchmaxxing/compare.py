"""The factual competitor comparison table already researched in
``STRATEGY-2026-10-23.md`` sections 1-2, as maintainable, regenerable data instead of hand-written
prose that silently goes stale. Every number here is sourced from that research pass (competitor
pricing pages, public GitHub repo state, third-party revenue trackers) -- this module does not
fetch anything live; re-verify and bump ``updated_at`` by hand when a competitor's pricing or repo
state changes, the same curation model as :mod:`launchmaxxing.catalog`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

#: One row per named competitor (or competitor *class*, for the one-time paid services and static
#: checklists, which are numerous enough that naming all of them would duplicate STRATEGY's prose
#: rather than summarize it). ``directories`` is a plain int where one number is meaningful, or a
#: short string where it genuinely varies by tier/vendor.
COMPETITORS: tuple[dict[str, Any], ...] = (
    {
        "name": "launchmaxxing", "price": "$0, forever, every feature",
        "directories": 82,
        "automation_state": "Deterministic local automation (copy generation, link-checking, "
                            "tracking, dashboard); directory submission itself is still a human "
                            "clicking \"submit\" -- this tool never claims otherwise.",
        "account_required": "None, for any command.",
        "notes": "MIT, local-only, SQLite + JSON on disk. Reusable across every future product "
                "the same founder launches, at no extra cost.",
    },
    {
        "name": "SubmitMap", "price": "Free tier: browse only. Paid: ~$33/mo (third-party "
                                      "Stripe-revenue estimate -- vendor does not publish a price).",
        "directories": 366,
        "automation_state": "Paid tier only: an MCP-based AI agent that fills submission forms "
                            "in the user's own browser.",
        "account_required": "Paid cloud account required for the submission dashboard and any "
                            "tracking/automation feature.",
        "notes": "Strongest breadth (366 directories) and per-platform disqualifier data (which "
                "free tiers closed, which platforms reject which product types).",
    },
    {
        "name": "OpenLaunch", "price": "$0 (MIT, open source).",
        "directories": 239,
        "automation_state": "Agent-native: requires the user's own AI coding agent (Claude, "
                            "Cursor, Devin) with live browser automation, burning that agent's "
                            "own API spend per submission -- no standalone CLI path.",
        "account_required": "No launchmaxxing-style account, but effectively requires an already-"
                            "configured AI coding agent with browser-automation capability.",
        "notes": "Largest *open* platform registry with real reconnaissance data (66/239 "
                "platforms have detailed field-level data); explicit AGENTS.md contract gating "
                "account/payment/public actions. No outreach tracking, content generation, or "
                "historical analytics.",
    },
    {
        "name": "SubmitFleet", "price": "$0 (MIT, open source, self-hosted).",
        "directories": 339,
        "automation_state": "0 of 339 catalogued directories have a working automated submit "
                            "adapter as of the current repo state (only TinyLaunch is contract-"
                            "tested, not actually live) -- the flagship automated-submission "
                            "promise does not work yet.",
        "account_required": "Self-hosted; requires provisioning Node/pnpm plus a database "
                            "(local SQLite or Turso/libsql) before first use.",
        "notes": "The most production-grade architecture of any competitor here (atomic "
                "intents, submission leasing/fencing, audit trail, AES-256 credential sealing) "
                "-- clearly built for teams/repeat campaigns, just not functional yet.",
    },
    {
        "name": "\"Done for you\" manual services (LaunchDirectories, StartupSubmit, SubmitSaaS, "
                "SubmitStorm, ListingSaaS)",
        "price": "$60-$299 one-time, per product launched (re-pay in full for the next product).",
        "directories": "30-200+ depending on vendor/tier",
        "automation_state": "A human does the manual form-filling labor for you and hands back "
                            "screenshot proof; nothing ongoing.",
        "account_required": "No reusable account/tool -- each payment buys one delivery for one "
                            "product.",
        "notes": "Genuinely saves ~20 hours of manual labor for a non-technical founder, but "
                "there is no ongoing checklist, outreach pipeline, content generation, or UTM "
                "tracking bundled in, and none of it is reusable for the founder's next launch.",
    },
    {
        "name": "Static launch checklists (PHLaunchChecklist.com, TheLaunchChecklist.com, and "
                "similar Notion/Airtable/Google-Sheet products)",
        "price": "Free to $79-$299, one-time.",
        "directories": "Varies (a reading list, not a submission tool)",
        "automation_state": "None -- a static document, not software.",
        "account_required": "No account, but also no software: nothing is tracked once the tab "
                            "closes.",
        "notes": "Zero setup, works for a non-technical founder with no terminal -- the one real "
                "advantage over every tool-shaped competitor here, launchmaxxing included.",
    },
)
COMPETITOR_BY_NAME: dict[str, dict[str, Any]] = {c["name"]: c for c in COMPETITORS}

#: Markdown table column order + header labels, shared by :func:`render_markdown` and the README
#: export so the two never drift out of sync with each other.
_MARKDOWN_COLUMNS: tuple[tuple[str, str], ...] = (
    ("name", "Tool"), ("price", "Price"), ("directories", "Directories"),
    ("automation_state", "Automation"), ("account_required", "Account required"),
)


def render_text() -> str:
    """A plain-text comparison, one block per competitor -- what ``launchmaxxing compare``
    prints by default."""
    lines: list[str] = []
    for c in COMPETITORS:
        lines += [
            f"{c['name']} -- {c['price']}", f"  Directories: {c['directories']}",
            f"  Automation: {c['automation_state']}", f"  Account required: {c['account_required']}",
            f"  Notes: {c['notes']}", "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def render_markdown() -> str:
    """A ready-to-paste README Markdown table -- what ``launchmaxxing compare --markdown``
    prints, and what the README's own comparison section should be regenerated from (by hand,
    copy-paste) whenever a competitor's pricing or repo state changes, instead of hand-editing
    prose that silently goes stale."""
    header = "| " + " | ".join(label for _, label in _MARKDOWN_COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in _MARKDOWN_COLUMNS) + " |"
    rows = []
    for c in COMPETITORS:
        cells = [str(c[key]).replace("\n", " ").replace("|", "\\|") for key, _ in _MARKDOWN_COLUMNS]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep, *rows]) + "\n"


def write_markdown(path: Path | str) -> Path:
    out_path = Path(path)
    out_path.write_text(render_markdown(), encoding="utf-8")
    return out_path


__all__ = [
    "COMPETITORS",
    "COMPETITOR_BY_NAME",
    "render_markdown",
    "render_text",
    "write_markdown",
]
