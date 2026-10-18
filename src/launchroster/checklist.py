"""Builds the 10-step first-100-users checklist for one product by combining
the static playbook (:mod:`launchroster.catalog`) with saved progress
(:mod:`launchroster.state`).
"""

from __future__ import annotations

from typing import Any

from launchroster import catalog, state


def build(app_state: dict[str, Any], product_name: str) -> dict[str, Any]:
    """Per-product status of the 10-step playbook. ``launch_everywhere`` is derived from
    platform submissions (done once any platform is submitted/live and not overridden); every
    other step reads saved step status, defaulting to pending when never touched."""
    title = product_name.strip()
    if not title:
        raise ValueError("product_name is required")
    platform_statuses = state.get_platform_statuses(app_state, title)
    submitted_platforms = [pid for pid, row in platform_statuses.items() if row.get("status") in ("submitted", "live")]
    step_statuses = state.get_step_statuses(app_state, title)
    steps = []
    for s in catalog.PLAYBOOK_STEPS:
        row = step_statuses.get(s["key"])
        if row is not None:
            status, note, updated_at = row["status"], row["note"], row.get("updated_at")
        elif s["key"] == "launch_everywhere" and submitted_platforms:
            status, note, updated_at = "done", f"{len(submitted_platforms)} platform(s) submitted/live.", None
        else:
            status, note, updated_at = "pending", "", None
        steps.append({"key": s["key"], "title": s["title"], "detail": s["detail"], "status": status, "note": note,
                      "updated_at": updated_at})
    done = sum(1 for s in steps if s["status"] == "done")
    return {"product_name": title, "steps": steps, "done": done, "total": len(steps),
            "platforms_submitted": submitted_platforms}


__all__ = ["build"]
