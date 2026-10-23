"""Local, file-based state: no server, no database, no account.

The hosted version this was extracted from kept per-user rows in Postgres.
A standalone CLI tool has no "user" to scope rows to, so this module
replaces that with one JSON file on disk (default
``~/.launchmaxxing/state.json``, overridable via ``LAUNCHMAXXING_STATE`` or
an explicit path) holding:

* per-product launch-directory submission status (not_started / submitted / live)
* per-product playbook step status (pending / done)
* saved Reddit pain-point drafts (drafted / approved / dismissed -- never
  "posted"; posting is always a human, on Reddit, by hand)

Every function here takes the whole state dict in and returns a new dict
out (or mutates the loaded dict and the caller re-saves it) -- there is no
hidden global; :func:`load` / :func:`save` are the only I/O.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PLATFORM_STATUSES = ("not_started", "submitted", "live")
STEP_STATUSES = ("pending", "done")
DRAFT_STATUSES = ("drafted", "approved", "dismissed")

DEFAULT_STATE_PATH = Path.home() / ".launchmaxxing" / "state.json"


def default_path() -> Path:
    override = os.environ.get("LAUNCHMAXXING_STATE")
    return Path(override).expanduser() if override else DEFAULT_STATE_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_state() -> dict[str, Any]:
    return {"products": {}, "pain_point_drafts": []}


def load(path: Path | None = None) -> dict[str, Any]:
    target = path or default_path()
    if not target.is_file():
        return _empty_state()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state()
    if not isinstance(data, dict):
        return _empty_state()
    data.setdefault("products", {})
    data.setdefault("pain_point_drafts", [])
    return data


def save(state: dict[str, Any], path: Path | None = None) -> Path:
    """Write ``state`` to ``path`` atomically: serialize to a temp file in the same
    directory, flush+fsync it, then ``os.replace()`` it into place. A process killed
    mid-write leaves either the old file or the new one intact -- never a truncated or
    half-written ``state.json``."""
    target = path or default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, sort_keys=True)
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return target


def _product_bucket(state: dict[str, Any], product_name: str) -> dict[str, Any]:
    title = product_name.strip()
    if not title:
        raise ValueError("product_name is required")
    products = state.setdefault("products", {})
    return products.setdefault(title, {"platforms": {}, "steps": {}, "created_at": _now_iso()})


def get_product_created_at(state: dict[str, Any], product_name: str) -> str | None:
    """ISO timestamp of when ``product_name`` was first touched (any platform/step write), or
    ``None`` if the product has no saved state yet. Used to flag stale/overdue reminders in
    :mod:`launchmaxxing.track` without requiring a separate "project start date" to be set by hand."""
    title = product_name.strip()
    bucket = state.get("products", {}).get(title)
    return bucket.get("created_at") if bucket else None


def set_platform_status(state: dict[str, Any], *, product_name: str, platform_id: str, status: str,
                        note: str = "") -> dict[str, Any]:
    from launchmaxxing import catalog

    if platform_id not in catalog.PLATFORM_BY_ID:
        raise ValueError(f"unknown platform_id {platform_id!r}")
    if status not in PLATFORM_STATUSES:
        raise ValueError(f"status must be one of {', '.join(PLATFORM_STATUSES)}")
    bucket = _product_bucket(state, product_name)
    row = bucket["platforms"].get(platform_id, {})
    moment = _now_iso()
    submitted_at = row.get("submitted_at")
    if status != "not_started" and submitted_at is None:
        submitted_at = moment
    if status == "not_started":
        submitted_at = None
    bucket["platforms"][platform_id] = {
        "status": status, "note": note.strip(), "submitted_at": submitted_at, "updated_at": moment,
    }
    return bucket["platforms"][platform_id]


def get_platform_statuses(state: dict[str, Any], product_name: str) -> dict[str, dict[str, Any]]:
    title = product_name.strip()
    return dict(state.get("products", {}).get(title, {}).get("platforms", {}))


def set_step_status(state: dict[str, Any], *, product_name: str, step_key: str, status: str,
                    note: str = "") -> dict[str, Any]:
    from launchmaxxing import catalog

    if step_key not in catalog.STEP_BY_KEY:
        raise ValueError(f"unknown step_key {step_key!r}")
    if status not in STEP_STATUSES:
        raise ValueError(f"status must be one of {', '.join(STEP_STATUSES)}")
    bucket = _product_bucket(state, product_name)
    bucket["steps"][step_key] = {"status": status, "note": note.strip(), "updated_at": _now_iso()}
    return bucket["steps"][step_key]


def get_step_statuses(state: dict[str, Any], product_name: str) -> dict[str, dict[str, Any]]:
    title = product_name.strip()
    return dict(state.get("products", {}).get(title, {}).get("steps", {}))


def set_default_profile(state: dict[str, Any], product_name: str, profile: dict[str, Any]) -> dict[str, Any]:
    """Save ``profile`` (name/tagline/problem/audience/differentiator/url/pricing/subreddit) as
    this product's default -- set once via ``launchmaxxing init --interactive``, read back by
    every later ``content``/``outreach draft`` call for the same product so a founder doesn't
    have to re-supply every flag each time they want another platform's copy."""
    bucket = _product_bucket(state, product_name)
    bucket["profile"] = dict(profile)
    return bucket["profile"]


def get_default_profile(state: dict[str, Any], product_name: str) -> dict[str, Any] | None:
    """This product's saved default profile, or ``None`` if ``init --interactive`` (or a direct
    ``set_default_profile`` call) was never run for it."""
    title = product_name.strip()
    bucket = state.get("products", {}).get(title)
    saved = bucket.get("profile") if bucket else None
    return dict(saved) if saved else None


def add_pain_point_drafts(state: dict[str, Any], *, query: str, product_name: str,
                          threads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Append one draft per new thread (deduped by thread_url + query); returns every draft for
    this query (new and pre-existing) in search-result order."""
    drafts: list[dict[str, Any]] = state.setdefault("pain_point_drafts", [])
    existing_urls = {d["thread_url"] for d in drafts if d.get("query") == query}
    out: list[dict[str, Any]] = []
    for thread in threads:
        if thread["thread_url"] not in existing_urls:
            community = thread.get("community", thread.get("subreddit", ""))
            row = {
                "id": uuid.uuid4().hex, "product_name": product_name.strip(), "query": query,
                "source": thread.get("source", "reddit"), "subreddit": community, "community": community,
                "thread_url": thread["thread_url"],
                "thread_title": thread.get("thread_title", ""), "snippet": thread.get("snippet", ""),
                "upvotes": thread.get("upvotes", 0), "age_days": thread.get("age_days", 0),
                "draft_reply": thread.get("draft_reply", ""), "status": "drafted", "created_at": _now_iso(),
            }
            drafts.append(row)
            existing_urls.add(thread["thread_url"])
            out.append(row)
        else:
            out.append(next(d for d in drafts if d["thread_url"] == thread["thread_url"] and d.get("query") == query))
    return out


def list_pain_point_drafts(state: dict[str, Any], *, status: str | None = None,
                           product_name: str | None = None) -> list[dict[str, Any]]:
    drafts = state.get("pain_point_drafts", [])
    out = list(drafts)
    if status:
        out = [d for d in out if d.get("status") == status]
    if product_name:
        out = [d for d in out if d.get("product_name") == product_name.strip()]
    return sorted(out, key=lambda d: d.get("created_at", ""), reverse=True)


def set_draft_status(state: dict[str, Any], draft_id: str, status: str) -> dict[str, Any]:
    if status not in DRAFT_STATUSES:
        raise ValueError(f"status must be one of {', '.join(DRAFT_STATUSES)}")
    for draft in state.get("pain_point_drafts", []):
        if draft.get("id") == draft_id:
            draft["status"] = status
            return draft
    raise ValueError(f"draft not found: {draft_id!r}")


__all__ = [
    "DRAFT_STATUSES", "PLATFORM_STATUSES", "STEP_STATUSES", "add_pain_point_drafts", "default_path",
    "get_default_profile", "get_platform_statuses", "get_product_created_at", "get_step_statuses",
    "list_pain_point_drafts", "load", "save", "set_default_profile", "set_draft_status",
    "set_platform_status", "set_step_status",
]
