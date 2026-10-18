"""Local SQLite-backed history layer for launchmaxxing's v2 features.

:mod:`launchmaxxing.state` (one JSON file) stays the source of truth for the
original *current-status* snapshot -- what a product's directory/checklist
status is *right now*. As the feature set grew (outreach pipelines, content
drafts, UTM links, a full submission history instead of "when was this last
touched"), a flat JSON blob stopped being the right data model: history needs
append-only rows, not an overwritten dict. This module adds a local SQLite
database for exactly that -- still zero signup, zero server, one file on
disk (default ``~/.launchmaxxing/launchmaxxing.db``, overridable via
``--db-file`` or the ``LAUNCHMAXXING_DB`` environment variable, same pattern
as :func:`launchmaxxing.state.default_path`).

Nothing here talks to a network. Every table is local-only history that a
human can inspect with ``sqlite3 ~/.launchmaxxing/launchmaxxing.db`` if they
want to; there is no hidden telemetry and no account.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTREACH_CHANNELS = ("creator", "press", "community", "user")
OUTREACH_STATUSES = ("not_contacted", "contacted", "replied", "booked", "declined")
CONTENT_PLATFORMS = ("product_hunt", "show_hn", "twitter", "reddit", "linkedin")

DEFAULT_DB_PATH = Path.home() / ".launchmaxxing" / "launchmaxxing.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS submission_events (
    id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    platform_id TEXT NOT NULL,
    status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_submission_events_product
    ON submission_events (product_name, platform_id, created_at);

CREATE TABLE IF NOT EXISTS outreach_contacts (
    id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    name TEXT NOT NULL,
    channel TEXT NOT NULL,
    handle TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outreach_contacts_product
    ON outreach_contacts (product_name, status);

CREATE TABLE IF NOT EXISTS content_drafts (
    id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    platform TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_content_drafts_product
    ON content_drafts (product_name, platform);

CREATE TABLE IF NOT EXISTS utm_links (
    id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    platform_id TEXT NOT NULL DEFAULT '',
    base_url TEXT NOT NULL,
    source TEXT NOT NULL,
    medium TEXT NOT NULL,
    campaign TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    full_url TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_utm_links_product
    ON utm_links (product_name);
"""


def default_path() -> Path:
    override = os.environ.get("LAUNCHMAXXING_DB")
    return Path(override).expanduser() if override else DEFAULT_DB_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Open (creating if needed) the local SQLite database and ensure its schema exists.
    Callers own the connection and should close it; :func:`launchmaxxing.cli` opens one per
    invocation and closes it before exiting, the same lifecycle as a short-lived CLI process."""
    target = path or default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


# --------------------------------------------------------------------------- #
# submission history
# --------------------------------------------------------------------------- #
def log_submission_event(conn: sqlite3.Connection, *, product_name: str, platform_id: str, status: str,
                          note: str = "") -> dict[str, Any]:
    """Append one immutable history row for a directory status change. Unlike
    :mod:`launchmaxxing.state`'s current-status snapshot, nothing here is ever overwritten -- this
    is the full "what happened, when" log behind ``launchmaxxing submit --history``."""
    row = {"id": uuid.uuid4().hex, "product_name": product_name.strip(), "platform_id": platform_id,
           "status": status, "note": note.strip(), "created_at": _now_iso()}
    conn.execute(
        "INSERT INTO submission_events (id, product_name, platform_id, status, note, created_at) "
        "VALUES (:id, :product_name, :platform_id, :status, :note, :created_at)", row,
    )
    conn.commit()
    return row


def list_submission_events(conn: sqlite3.Connection, product_name: str,
                            platform_id: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM submission_events WHERE product_name = ?"
    params: list[Any] = [product_name.strip()]
    if platform_id:
        query += " AND platform_id = ?"
        params.append(platform_id)
    query += " ORDER BY created_at ASC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


# --------------------------------------------------------------------------- #
# outreach contacts
# --------------------------------------------------------------------------- #
def add_outreach_contact(conn: sqlite3.Connection, *, product_name: str, name: str, channel: str,
                          handle: str = "", status: str = "not_contacted", note: str = "") -> dict[str, Any]:
    if channel not in OUTREACH_CHANNELS:
        raise ValueError(f"channel must be one of {', '.join(OUTREACH_CHANNELS)}")
    if status not in OUTREACH_STATUSES:
        raise ValueError(f"status must be one of {', '.join(OUTREACH_STATUSES)}")
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("name is required")
    moment = _now_iso()
    row = {"id": uuid.uuid4().hex, "product_name": product_name.strip(), "name": clean_name, "channel": channel,
           "handle": handle.strip(), "status": status, "note": note.strip(), "created_at": moment,
           "updated_at": moment}
    conn.execute(
        "INSERT INTO outreach_contacts (id, product_name, name, channel, handle, status, note, created_at, "
        "updated_at) VALUES (:id, :product_name, :name, :channel, :handle, :status, :note, :created_at, "
        ":updated_at)", row,
    )
    conn.commit()
    return row


def update_outreach_status(conn: sqlite3.Connection, contact_id: str, status: str,
                            note: str | None = None) -> dict[str, Any]:
    if status not in OUTREACH_STATUSES:
        raise ValueError(f"status must be one of {', '.join(OUTREACH_STATUSES)}")
    existing = conn.execute("SELECT * FROM outreach_contacts WHERE id = ?", (contact_id,)).fetchone()
    if existing is None:
        raise ValueError(f"contact not found: {contact_id!r}")
    new_note = existing["note"] if note is None else note.strip()
    moment = _now_iso()
    conn.execute("UPDATE outreach_contacts SET status = ?, note = ?, updated_at = ? WHERE id = ?",
                 (status, new_note, moment, contact_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM outreach_contacts WHERE id = ?", (contact_id,)).fetchone())


def list_outreach_contacts(conn: sqlite3.Connection, product_name: str | None = None,
                            status: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM outreach_contacts WHERE 1 = 1"
    params: list[Any] = []
    if product_name:
        query += " AND product_name = ?"
        params.append(product_name.strip())
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def stale_outreach_contacts(conn: sqlite3.Connection, product_name: str, *, stale_days: int = 5,
                             now: datetime | None = None) -> list[dict[str, Any]]:
    """Contacts stuck in ``contacted`` with no reply for ``stale_days`` -- the follow-up queue."""
    moment = now or datetime.now(timezone.utc)
    out = []
    for row in list_outreach_contacts(conn, product_name=product_name, status="contacted"):
        updated = datetime.fromisoformat(row["updated_at"])
        if (moment - updated).days >= stale_days:
            out.append(row)
    return out


# --------------------------------------------------------------------------- #
# content drafts
# --------------------------------------------------------------------------- #
def add_content_draft(conn: sqlite3.Connection, *, product_name: str, platform: str, body: str,
                       kind: str = "") -> dict[str, Any]:
    row = {"id": uuid.uuid4().hex, "product_name": product_name.strip(), "platform": platform, "kind": kind,
           "body": body, "created_at": _now_iso()}
    conn.execute(
        "INSERT INTO content_drafts (id, product_name, platform, kind, body, created_at) "
        "VALUES (:id, :product_name, :platform, :kind, :body, :created_at)", row,
    )
    conn.commit()
    return row


def list_content_drafts(conn: sqlite3.Connection, product_name: str | None = None,
                         platform: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM content_drafts WHERE 1 = 1"
    params: list[Any] = []
    if product_name:
        query += " AND product_name = ?"
        params.append(product_name.strip())
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    query += " ORDER BY created_at DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


# --------------------------------------------------------------------------- #
# UTM links
# --------------------------------------------------------------------------- #
def add_utm_link(conn: sqlite3.Connection, *, product_name: str, base_url: str, source: str, medium: str,
                  campaign: str, full_url: str, platform_id: str = "", content: str = "") -> dict[str, Any]:
    row = {"id": uuid.uuid4().hex, "product_name": product_name.strip(), "platform_id": platform_id,
           "base_url": base_url, "source": source, "medium": medium, "campaign": campaign, "content": content,
           "full_url": full_url, "created_at": _now_iso()}
    conn.execute(
        "INSERT INTO utm_links (id, product_name, platform_id, base_url, source, medium, campaign, content, "
        "full_url, created_at) VALUES (:id, :product_name, :platform_id, :base_url, :source, :medium, "
        ":campaign, :content, :full_url, :created_at)", row,
    )
    conn.commit()
    return row


def list_utm_links(conn: sqlite3.Connection, product_name: str | None = None) -> list[dict[str, Any]]:
    query = "SELECT * FROM utm_links WHERE 1 = 1"
    params: list[Any] = []
    if product_name:
        query += " AND product_name = ?"
        params.append(product_name.strip())
    query += " ORDER BY created_at DESC"
    return [dict(r) for r in conn.execute(query, params).fetchall()]


__all__ = [
    "CONTENT_PLATFORMS", "DEFAULT_DB_PATH", "OUTREACH_CHANNELS", "OUTREACH_STATUSES", "add_content_draft",
    "add_outreach_contact", "add_utm_link", "connect", "default_path", "list_content_drafts",
    "list_outreach_contacts", "list_submission_events", "list_utm_links", "log_submission_event",
    "stale_outreach_contacts", "update_outreach_status",
]
