"""Builds the 10-step first-100-users checklist for one product by combining
the static playbook (:mod:`launchmaxxing.catalog`) with saved progress
(:mod:`launchmaxxing.state`) and, for the two steps that have a real signal
elsewhere in the data model, the local SQLite outreach pipeline
(:mod:`launchmaxxing.db`).

Auto-derivation removes manual step-marking friction for the steps that
already have a real signal somewhere else in this tool, instead of making a
human separately run ``checklist-step ... done`` for progress the tool
already recorded:

* ``launch_everywhere`` -- done once any catalog platform is submitted/live.
* ``cold_outreach`` -- done once any tracked outreach contact has moved past
  ``not_contacted`` (i.e. :mod:`launchmaxxing.outreach`/``outreach add`` or
  ``outreach status`` recorded real contact activity).
* ``reddit_pain_points`` -- done once any saved pain-point draft (from
  ``pain-points``, across any source -- Reddit, Hacker News, Indie Hackers)
  has been reviewed (``approved`` or ``dismissed``, never just left
  ``drafted``).

Every other step still has no independent signal to derive from (there is
nothing elsewhere in the data model that proves a demo video got recorded,
or a UGC creator got DM'd) and keeps reading saved step status exactly as
before. An explicit ``checklist-step ... done/pending`` always overrides the
derived value for the three steps above, same precedence rule as
``launch_everywhere`` already had.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from launchmaxxing import catalog, state


def _derive_launch_everywhere(app_state: dict[str, Any], title: str) -> tuple[str, str] | None:
    platform_statuses = state.get_platform_statuses(app_state, title)
    submitted = [pid for pid, row in platform_statuses.items() if row.get("status") in ("submitted", "live")]
    if not submitted:
        return None
    return "done", f"{len(submitted)} platform(s) submitted/live."


def _derive_cold_outreach(conn: sqlite3.Connection | None, title: str) -> tuple[str, str] | None:
    if conn is None:
        return None
    from launchmaxxing import db

    contacted = [c for c in db.list_outreach_contacts(conn, product_name=title) if c["status"] != "not_contacted"]
    if not contacted:
        return None
    return "done", f"{len(contacted)} outreach contact(s) past not_contacted."


def _derive_reddit_pain_points(app_state: dict[str, Any], title: str) -> tuple[str, str] | None:
    drafts = state.list_pain_point_drafts(app_state, product_name=title)
    reviewed = [d for d in drafts if d.get("status") in ("approved", "dismissed")]
    if not reviewed:
        return None
    return "done", f"{len(reviewed)} pain-point draft(s) reviewed (approved/dismissed)."


#: Per-step auto-derivation rules: ``step_key -> (app_state, title, conn) -> (status, note) | None``.
#: A rule returning ``None`` means "no independent signal yet", so :func:`build` falls back to the
#: saved step status (or ``pending`` if that was never touched either).
_DERIVATIONS: dict[str, Any] = {
    "launch_everywhere": lambda app_state, title, conn: _derive_launch_everywhere(app_state, title),
    "cold_outreach": lambda app_state, title, conn: _derive_cold_outreach(conn, title),
    "reddit_pain_points": lambda app_state, title, conn: _derive_reddit_pain_points(app_state, title),
}


def build(app_state: dict[str, Any], product_name: str, *,
          conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Per-product status of the 10-step playbook. An explicit saved step status (from
    ``checklist-step``) always wins; otherwise a step with an auto-derivation rule (see module
    docstring) is marked done once its real signal exists, and every other step defaults to
    pending. ``conn`` is optional -- without it, ``cold_outreach`` simply can't be auto-derived
    (falls back to pending/saved status) since that signal lives in SQLite, not the JSON state
    file; ``launch_everywhere`` and ``reddit_pain_points`` still auto-derive either way."""
    title = product_name.strip()
    if not title:
        raise ValueError("product_name is required")
    platform_statuses = state.get_platform_statuses(app_state, title)
    submitted_platforms = [pid for pid, row in platform_statuses.items() if row.get("status") in ("submitted", "live")]
    step_statuses = state.get_step_statuses(app_state, title)
    steps = []
    for s in catalog.PLAYBOOK_STEPS:
        row = step_statuses.get(s["key"])
        derived = _DERIVATIONS.get(s["key"])
        if row is not None:
            status, note, updated_at = row["status"], row["note"], row.get("updated_at")
        elif derived is not None and (result := derived(app_state, title, conn)) is not None:
            status, note, updated_at = result[0], result[1], None
        else:
            status, note, updated_at = "pending", "", None
        steps.append({"key": s["key"], "title": s["title"], "detail": s["detail"], "status": status, "note": note,
                      "updated_at": updated_at})
    done = sum(1 for s in steps if s["status"] == "done")
    return {"product_name": title, "steps": steps, "done": done, "total": len(steps),
            "platforms_submitted": submitted_platforms}


__all__ = ["build"]
