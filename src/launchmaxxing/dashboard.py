"""A self-contained, static HTML launch dashboard -- the shareable *visual* artifact version of
``launchmaxxing track``/``report``. Renders the exact same data :mod:`launchmaxxing.track` already
assembles (directories, checklist, outreach, content drafts, UTM links) plus the raw submission
event history already recorded in SQLite, as one HTML file with inline CSS and inline SVG progress
rings/timeline -- no Jinja2, no Flask, no CDN asset, no network call. Opens directly in a browser
by double-clicking the file, or can be served locally with :mod:`launchmaxxing.cli`'s ``serve``
command. Keeps the zero-account/zero-server-dependency positioning of the rest of this tool: the
HTML this module generates never leaves the machine it was generated on unless a human copies it.
"""

from __future__ import annotations

import html
import sqlite3
from datetime import datetime, timezone
from typing import Any

from launchmaxxing import catalog, db, track

_BLUE = "#2563eb"
_GREEN = "#16a34a"
_AMBER = "#d97706"
_RED = "#dc2626"
_GRAY = "#6b7280"

_CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0; background: #0b1120; color: #e2e8f0;
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}
main { max-width: 980px; margin: 0 auto; padding: 32px 20px 64px; }
header.page { margin-bottom: 28px; }
header.page h1 { font-size: 28px; margin: 0 0 4px; letter-spacing: -0.02em; }
header.page p.meta { color: #94a3b8; margin: 0; font-size: 13px; }
.cards { display: flex; flex-wrap: wrap; gap: 16px; margin: 24px 0 32px; }
.card { background: #111a2e; border: 1px solid #1f2b45; border-radius: 14px; padding: 18px 20px; flex: 1 1 200px; min-width: 180px; }
.card h3 { margin: 0 0 10px; font-size: 13px; letter-spacing: 0.04em; text-transform: uppercase; color: #94a3b8; }
.ring-wrap { display: flex; align-items: center; gap: 14px; }
.ring text.ring-num { fill: #e2e8f0; font-size: 20px; font-weight: 700; font-family: inherit; }
.ring text.ring-label { fill: #64748b; font-size: 10px; font-family: inherit; }
.ring-detail { font-size: 13px; color: #cbd5e1; }
.ring-detail strong { color: #e2e8f0; font-size: 15px; }
section.block { margin: 32px 0; }
section.block h2 { font-size: 16px; margin: 0 0 14px; border-bottom: 1px solid #1f2b45; padding-bottom: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
table th, table td { text-align: left; padding: 7px 8px; border-bottom: 1px solid #16213a; }
table th { color: #94a3b8; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.03em; }
.pill { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.pill-live, .pill-done, .pill-replied, .pill-booked { background: rgba(22,163,74,0.18); color: #4ade80; }
.pill-submitted, .pill-contacted { background: rgba(217,119,6,0.18); color: #fbbf24; }
.pill-not_started, .pill-pending, .pill-not_contacted { background: rgba(107,114,128,0.22); color: #94a3b8; }
.pill-declined { background: rgba(220,38,38,0.18); color: #f87171; }
.stale-list, ul.plain { list-style: none; margin: 10px 0 0; padding: 0; }
.stale-list li, ul.plain li { padding: 6px 0; border-bottom: 1px solid #16213a; font-size: 14px; }
.stale-list a { color: #93c5fd; text-decoration: none; }
.stale-list a:hover { text-decoration: underline; }
.empty { color: #64748b; font-style: italic; font-size: 14px; }
.timeline { position: relative; margin: 10px 0 0; padding-left: 20px; border-left: 2px solid #1f2b45; }
.timeline .tl-item { position: relative; padding: 0 0 18px 16px; }
.timeline .tl-item::before {
  content: ""; position: absolute; left: -27px; top: 3px; width: 10px; height: 10px; border-radius: 50%;
  background: var(--dot-color, #2563eb); box-shadow: 0 0 0 3px #0b1120;
}
.timeline .tl-date { color: #64748b; font-size: 12px; }
.timeline .tl-body { font-size: 14px; color: #e2e8f0; }
footer.page { margin-top: 48px; color: #475569; font-size: 12px; border-top: 1px solid #1f2b45; padding-top: 16px; }
footer.page a { color: #64748b; }
"""

_STATUS_COLOR = {
    "live": _GREEN, "done": _GREEN, "replied": _GREEN, "booked": _GREEN,
    "submitted": _AMBER, "contacted": _AMBER,
    "not_started": _GRAY, "pending": _GRAY, "not_contacted": _GRAY,
    "declined": _RED,
}


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _ring_svg(done: int, total: int, *, label: str, size: int = 112, stroke: int = 11,
              color: str = _BLUE) -> str:
    """One donut-style SVG progress ring, hand-built (no chart library): a background track
    circle plus a foreground circle whose ``stroke-dasharray``/``stroke-dashoffset`` is set so
    exactly ``done/total`` of its circumference is drawn, rotated -90 degrees so the ring fills
    starting from 12 o'clock."""
    pct = 0.0 if total <= 0 else max(0.0, min(1.0, done / total))
    radius = (size - stroke) / 2
    circumference = 2 * 3.141592653589793 * radius
    offset = circumference * (1 - pct)
    center = size / 2
    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" class="ring" role="img" '
        f'aria-label="{_esc(label)}: {done} of {total}">'
        f'<circle cx="{center}" cy="{center}" r="{radius:.2f}" fill="none" stroke="#1f2b45" '
        f'stroke-width="{stroke}" />'
        f'<circle cx="{center}" cy="{center}" r="{radius:.2f}" fill="none" stroke="{color}" '
        f'stroke-width="{stroke}" stroke-dasharray="{circumference:.2f}" '
        f'stroke-dashoffset="{offset:.2f}" stroke-linecap="round" '
        f'transform="rotate(-90 {center} {center})" />'
        f'<text x="{center}" y="{center - 2}" text-anchor="middle" class="ring-num">{done}/{total}</text>'
        f'<text x="{center}" y="{center + 18}" text-anchor="middle" class="ring-label">{_esc(label)}</text>'
        f'</svg>'
    )


def _pill(status: str) -> str:
    cls = f"pill pill-{_esc(status)}"
    return f'<span class="{cls}">{_esc(status.replace("_", " "))}</span>'


def _directories_section(dashboard: dict[str, Any]) -> str:
    d = dashboard["directories"]
    ring = _ring_svg(d["submitted_or_live"], d["total"], label="directories", color=_BLUE)
    stale_html = '<p class="empty">Nothing overdue.</p>'
    if d["stale"]:
        items = "".join(
            f'<li><a href="{_esc(p["url"])}" target="_blank" rel="noopener">{_esc(p["name"])}</a></li>'
            for p in d["stale"]
        )
        stale_html = f'<ul class="stale-list">{items}</ul>'
    return (
        '<section class="block"><h2>Directories</h2>'
        '<div class="ring-wrap">'
        f'{ring}'
        f'<div class="ring-detail"><strong>{d["submitted_or_live"]}/{d["total"]}</strong> submitted '
        f'or live<br>{d["not_started"]} not started yet</div>'
        '</div>'
        f'<h3 style="font-size:13px;color:#94a3b8;margin:18px 0 4px;">'
        f'Overdue ({dashboard["stale_days"]}+ days untouched)</h3>{stale_html}'
        '</section>'
    )


def _checklist_section(dashboard: dict[str, Any], app_state_steps: list[dict[str, Any]]) -> str:
    c = dashboard["checklist"]
    ring = _ring_svg(c["done"], c["total"], label="checklist", color=_GREEN)
    rows = "".join(
        f'<tr><td>{_pill(s["status"])}</td><td>{_esc(s["title"])}</td>'
        f'<td style="color:#94a3b8;">{_esc(s["detail"])}</td></tr>'
        for s in app_state_steps
    )
    table = (
        '<table><thead><tr><th>Status</th><th>Step</th><th>Detail</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>' if rows else '<p class="empty">No steps yet.</p>'
    )
    return (
        '<section class="block"><h2>10-step checklist</h2>'
        f'<div class="ring-wrap">{ring}'
        f'<div class="ring-detail"><strong>{c["done"]}/{c["total"]}</strong> playbook steps done</div></div>'
        f'<div style="margin-top:14px;">{table}</div>'
        '</section>'
    )


def _outreach_section(dashboard: dict[str, Any]) -> str:
    o = dashboard["outreach"]
    if o["total"] == 0:
        body = '<p class="empty">No contacts tracked yet.</p>'
    else:
        rows = "".join(
            f'<tr><td>{_pill(status)}</td><td>{count}</td></tr>'
            for status, count in sorted(o["by_status"].items())
        )
        followups = '<p class="empty">None awaiting follow-up.</p>'
        if o["stale_followups"]:
            items = "".join(
                f'<li>{_esc(c["name"])} <span style="color:#64748b;">({_esc(c["channel"])})</span></li>'
                for c in o["stale_followups"]
            )
            followups = f'<ul class="plain">{items}</ul>'
        body = (
            f'<table><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<h3 style="font-size:13px;color:#94a3b8;margin:18px 0 4px;">Awaiting follow-up</h3>{followups}'
        )
    return f'<section class="block"><h2>Outreach ({o["total"]} contact(s))</h2>{body}</section>'


def _content_utm_section(dashboard: dict[str, Any]) -> str:
    return (
        '<section class="block"><h2>Content &amp; links</h2>'
        '<div class="cards">'
        f'<div class="card"><h3>Content drafts</h3><div style="font-size:28px;font-weight:700;">'
        f'{dashboard["content_drafts"]}</div></div>'
        f'<div class="card"><h3>UTM links tracked</h3><div style="font-size:28px;font-weight:700;">'
        f'{dashboard["utm_links"]}</div></div>'
        '</div></section>'
    )


def _timeline_section(events: list[dict[str, Any]]) -> str:
    if not events:
        return (
            '<section class="block"><h2>Submission timeline</h2>'
            '<p class="empty">No submission events recorded yet -- run '
            '<code>launchmaxxing submit</code> to start one.</p></section>'
        )
    items = []
    for e in reversed(events):  # most recent first
        platform = catalog.PLATFORM_BY_ID.get(e["platform_id"])
        name = platform["name"] if platform else e["platform_id"]
        color = _STATUS_COLOR.get(e["status"], _BLUE)
        note = f' -- {_esc(e["note"])}' if e.get("note") else ""
        items.append(
            f'<div class="tl-item" style="--dot-color:{color};">'
            f'<div class="tl-date">{_esc(e["created_at"][:19].replace("T", " "))}</div>'
            f'<div class="tl-body"><strong>{_esc(name)}</strong> &rarr; {_pill(e["status"])}{note}</div>'
            f'</div>'
        )
    return f'<section class="block"><h2>Submission timeline</h2><div class="timeline">{"".join(items)}</div></section>'


def render_html(dashboard: dict[str, Any], checklist_steps: list[dict[str, Any]],
                 events: list[dict[str, Any]], *, now: datetime | None = None) -> str:
    """Render one self-contained HTML page from a :func:`launchmaxxing.track.build` dashboard
    dict, its checklist step rows, and raw submission events -- every byte of CSS/SVG is inlined
    here, so the returned string is the entire file: no external stylesheet, script, font or
    image request, and it still renders correctly with a file:// URL or fully offline."""
    moment = now or datetime.now(timezone.utc)
    title = dashboard["product_name"]
    age = dashboard.get("age_days")
    age_line = f"Tracking started {age} day(s) ago." if age is not None else "Tracking not started yet."
    body = (
        f'<header class="page"><h1>{_esc(title)}</h1>'
        f'<p class="meta">Generated {moment.date().isoformat()} &middot; {_esc(age_line)}</p></header>'
        + _directories_section(dashboard)
        + _checklist_section(dashboard, checklist_steps)
        + _outreach_section(dashboard)
        + _content_utm_section(dashboard)
        + _timeline_section(events)
        + '<footer class="page">Generated locally by '
          '<a href="https://github.com/caelum0x/launchmaxxing">launchmaxxing</a> -- '
          'no data leaves your machine. Re-run <code>launchmaxxing dashboard</code> to refresh, '
          'or <code>launchmaxxing serve</code> for a live-refreshing local view.</footer>'
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<title>Launch dashboard: {_esc(title)}</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<style>{_CSS}</style></head><body><main>{body}</main></body></html>'
    )


def build(app_state: dict[str, Any], conn: sqlite3.Connection, product_name: str, *,
          stale_days: int = track.DEFAULT_STALE_DAYS, now: datetime | None = None) -> str:
    """Assemble + render the full HTML dashboard for one product in one call -- what
    ``launchmaxxing dashboard``/``serve`` use. Reuses :func:`launchmaxxing.track.build` for every
    number shown so the HTML dashboard, the Markdown report, and the interactive ``track`` command
    can never disagree about what "submitted" or "done" means."""
    from launchmaxxing import checklist as checklist_mod

    dashboard = track.build(app_state, conn, product_name, stale_days=stale_days, now=now)
    checklist_steps = checklist_mod.build(app_state, product_name, conn=conn)["steps"]
    events = db.list_submission_events(conn, product_name)
    return render_html(dashboard, checklist_steps, events, now=now)


__all__ = ["build", "render_html"]
