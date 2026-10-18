"""The cross-cutting status dashboard: one view of everything tracked for a product across the
JSON state file (directories, checklist) and the SQLite database (outreach, content, UTM links),
plus the reminders a human would otherwise have to notice by hand -- which directories have gone
untouched for a while, and which outreach contacts are owed a follow-up.

This is what makes launchmaxxing a tool you run repeatedly over a multi-week launch instead of a
one-shot generator: ``launchmaxxing init`` gives you the plan once; ``launchmaxxing track`` tells
you, days or weeks later, what's actually still open.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from launchmaxxing import catalog, checklist, db, state

DEFAULT_STALE_DAYS = 5


def _days_since(iso_timestamp: str | None, *, now: datetime) -> int | None:
    if not iso_timestamp:
        return None
    try:
        then = datetime.fromisoformat(iso_timestamp)
    except ValueError:
        return None
    return (now - then).days


def build(app_state: dict[str, Any], conn: sqlite3.Connection, product_name: str, *,
          stale_days: int = DEFAULT_STALE_DAYS, now: datetime | None = None) -> dict[str, Any]:
    """Assemble the full dashboard for one product. ``stale_days`` controls both "directory not
    submitted after N days since the product first appeared" and "outreach contact awaiting
    reply after N days" -- one knob, two reminder types, same default."""
    title = product_name.strip()
    if not title:
        raise ValueError("product_name is required")
    moment = now or datetime.now(timezone.utc)

    created_at = state.get_product_created_at(app_state, title)
    age_days = _days_since(created_at, now=moment)

    platform_statuses = state.get_platform_statuses(app_state, title)
    stale_platforms: list[dict[str, Any]] = []
    not_started_count = 0
    submitted_or_live = 0
    for platform in catalog.PLATFORMS:
        row = platform_statuses.get(platform["id"])
        status = row["status"] if row else "not_started"
        if status == "not_started":
            not_started_count += 1
            if age_days is not None and age_days >= stale_days:
                stale_platforms.append({"id": platform["id"], "name": platform["name"], "url": platform["url"]})
        else:
            submitted_or_live += 1

    checklist_result = checklist.build(app_state, title)

    outreach_contacts = db.list_outreach_contacts(conn, product_name=title)
    outreach_by_status: dict[str, int] = {}
    for contact in outreach_contacts:
        outreach_by_status[contact["status"]] = outreach_by_status.get(contact["status"], 0) + 1
    stale_outreach = db.stale_outreach_contacts(conn, title, stale_days=stale_days, now=moment)

    content_drafts = db.list_content_drafts(conn, product_name=title)
    utm_links = db.list_utm_links(conn, product_name=title)

    return {
        "product_name": title,
        "created_at": created_at,
        "age_days": age_days,
        "directories": {
            "total": len(catalog.PLATFORMS),
            "submitted_or_live": submitted_or_live,
            "not_started": not_started_count,
            "stale": stale_platforms,
        },
        "checklist": {"done": checklist_result["done"], "total": checklist_result["total"]},
        "outreach": {
            "total": len(outreach_contacts),
            "by_status": outreach_by_status,
            "stale_followups": [{"id": c["id"], "name": c["name"], "channel": c["channel"]}
                                 for c in stale_outreach],
        },
        "content_drafts": len(content_drafts),
        "utm_links": len(utm_links),
        "stale_days": stale_days,
    }


__all__ = ["DEFAULT_STALE_DAYS", "build"]
