"""Cross-product rollup: one table summarizing every product tracked locally (across the JSON
state file and the SQLite database combined), instead of running ``launchmaxxing track`` once per
product and comparing by hand. Directly useful for a founder or small studio running several
simultaneous launches -- a natural fit for a multi-product audience, not just a single-product
founder running this tool once.

Nothing here is a new data store: every number is re-derived from the exact same
:mod:`launchmaxxing.state`/:mod:`launchmaxxing.db`/:mod:`launchmaxxing.checklist` functions
``track``/``report``/``dashboard`` already use for one product, just run once per product found
in either store and assembled into rows.
"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from launchmaxxing import catalog, checklist, db, state

#: Columns :func:`write_csv` writes, in the same order :func:`build` returns in each row --
#: everything a founder or studio lead would want in a spreadsheet/board-deck export of the
#: rollup table ``portfolio`` prints, nothing derived only for the terminal's display formatting
#: (e.g. the combined "3/10 (30%)" strings the text renderer builds -- a spreadsheet wants the
#: numerator/denominator/percentage as separate sortable columns instead).
CSV_FIELDS = (
    "product_name", "directories_submitted", "directories_total", "directories_pct",
    "checklist_done", "checklist_total", "checklist_pct", "outreach_total", "outreach_replied",
    "last_active", "days_since_active", "stale",
)

#: Tables (and their own "last touched" column) that can contain activity for a product that was
#: never written to the JSON state file at all -- e.g. a product only ever used via
#: ``outreach add``/``content ... --save``, never ``submit``/``checklist-step``.
_DB_TABLES_FOR_NAMES: tuple[str, ...] = ("submission_events", "outreach_contacts", "content_drafts", "utm_links")
_DB_LAST_ACTIVE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("submission_events", "created_at"), ("outreach_contacts", "updated_at"),
    ("content_drafts", "created_at"), ("utm_links", "created_at"),
)


def all_product_names(app_state: dict[str, Any], conn: sqlite3.Connection) -> tuple[str, ...]:
    """Every product name that has *any* recorded activity, in either store, case-insensitively
    sorted. A product only ever touched through a DB-only command (``outreach add``, ``content
    --save``, ``utm build``) still shows up here even with zero JSON state."""
    names: set[str] = set(app_state.get("products", {}).keys())
    for table in _DB_TABLES_FOR_NAMES:
        rows = conn.execute(f"SELECT DISTINCT product_name FROM {table}").fetchall()
        names.update(str(r[0]) for r in rows if r[0])
    return tuple(sorted(names, key=str.lower))


def _last_active(app_state: dict[str, Any], conn: sqlite3.Connection, product_name: str) -> str | None:
    """The most recent ISO timestamp across every per-product signal this tool records (directory
    status change, checklist step, outreach contact, content draft, UTM link) -- the "when did I
    last touch this launch" a founder juggling several of these actually wants, not just one
    narrow slice of the data."""
    candidates: list[str] = []
    for row in state.get_platform_statuses(app_state, product_name).values():
        if row.get("updated_at"):
            candidates.append(row["updated_at"])
    for row in state.get_step_statuses(app_state, product_name).values():
        if row.get("updated_at"):
            candidates.append(row["updated_at"])
    for table, column in _DB_LAST_ACTIVE_COLUMNS:
        result = conn.execute(
            f"SELECT MAX({column}) FROM {table} WHERE product_name = ?", (product_name,)
        ).fetchone()
        if result and result[0]:
            candidates.append(str(result[0]))
    return max(candidates) if candidates else None


def _pct(done: int, total: int) -> float:
    return round(100.0 * done / total, 1) if total else 0.0


def build(app_state: dict[str, Any], conn: sqlite3.Connection, *, stale_days: int = 5,
          now: datetime | None = None) -> dict[str, Any]:
    """One row per product with directory/checklist completion percentages, outreach reply
    counts, and a last-active/stale flag, sorted by most-recently-active first (the products a
    founder is mid-launch on surface above ones that haven't been touched in weeks)."""
    moment = now or datetime.now(timezone.utc)
    total_directories = len(catalog.PLATFORMS)
    rows: list[dict[str, Any]] = []
    for name in all_product_names(app_state, conn):
        platform_statuses = state.get_platform_statuses(app_state, name)
        submitted = sum(1 for r in platform_statuses.values() if r.get("status") in ("submitted", "live"))
        checklist_result = checklist.build(app_state, name, conn=conn)
        contacts = db.list_outreach_contacts(conn, product_name=name)
        replied = sum(1 for c in contacts if c["status"] in ("replied", "booked"))
        last_active = _last_active(app_state, conn, name)
        days_since_active: int | None = None
        if last_active:
            try:
                days_since_active = (moment - datetime.fromisoformat(last_active)).days
            except ValueError:
                days_since_active = None
        rows.append({
            "product_name": name,
            "directories_submitted": submitted, "directories_total": total_directories,
            "directories_pct": _pct(submitted, total_directories),
            "checklist_done": checklist_result["done"], "checklist_total": checklist_result["total"],
            "checklist_pct": _pct(checklist_result["done"], checklist_result["total"]),
            "outreach_total": len(contacts), "outreach_replied": replied,
            "last_active": last_active, "days_since_active": days_since_active,
            "stale": days_since_active is not None and days_since_active >= stale_days,
        })
    rows.sort(key=lambda r: (r["last_active"] or ""), reverse=True)
    return {"products": rows, "count": len(rows), "stale_days": stale_days}


def write_csv(rows: list[dict[str, Any]], path: Path | str) -> Path:
    """Write the portfolio rollup's ``rows`` (as returned by :func:`build`'s ``"products"`` key)
    to a CSV file at ``path`` with a header row -- for a founder/studio's board update or
    spreadsheet, the same export pattern :mod:`launchmaxxing.outreach`'s
    ``write_contacts_csv``/:mod:`launchmaxxing.catalog`'s ``export_csv`` already use. Returns the
    resolved :class:`~pathlib.Path` written to."""
    out_path = Path(path)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})
    return out_path


__all__ = ["CSV_FIELDS", "all_product_names", "build", "write_csv"]
