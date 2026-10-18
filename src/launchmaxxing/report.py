"""A shareable, one-page Markdown launch summary -- the thing you paste into a team doc, a
Notion page, or an investor update, instead of re-explaining launch status in a Slack message
every time someone asks "where are we on the launch." Pulls together the same data
:mod:`launchmaxxing.track` shows interactively, rendered as static Markdown you can commit,
email, or print.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def render_markdown(dashboard: dict[str, Any], *, now: datetime | None = None) -> str:
    """Render a :func:`launchmaxxing.track.build` dashboard dict into one Markdown document."""
    moment = now or datetime.now(timezone.utc)
    title = dashboard["product_name"]
    lines: list[str] = [f"# Launch report: {title}", "", f"_Generated {moment.date().isoformat()}_", ""]

    age = dashboard.get("age_days")
    if age is not None:
        lines.append(f"Launch tracking started {age} day(s) ago.")
        lines.append("")

    d = dashboard["directories"]
    lines += [
        "## Directories",
        f"- {d['submitted_or_live']}/{d['total']} submitted or live, {d['not_started']} not started.",
    ]
    if d["stale"]:
        lines.append(f"- **{len(d['stale'])} overdue** (not started, tracking stale for "
                      f"{dashboard['stale_days']}+ days):")
        for p in d["stale"]:
            lines.append(f"  - [{p['name']}]({p['url']})")
    lines.append("")

    c = dashboard["checklist"]
    lines += ["## Checklist", f"- {c['done']}/{c['total']} of the 10-step playbook done.", ""]

    o = dashboard["outreach"]
    lines.append("## Outreach")
    if o["total"] == 0:
        lines.append("- No contacts tracked yet.")
    else:
        status_line = ", ".join(f"{count} {status}" for status, count in sorted(o["by_status"].items()))
        lines.append(f"- {o['total']} contact(s) tracked: {status_line}.")
        if o["stale_followups"]:
            lines.append(f"- **{len(o['stale_followups'])} awaiting follow-up:**")
            for contact in o["stale_followups"]:
                lines.append(f"  - {contact['name']} ({contact['channel']})")
    lines.append("")

    lines += [
        "## Content drafted",
        f"- {dashboard['content_drafts']} launch-copy draft(s) generated.",
        "",
        "## UTM links generated",
        f"- {dashboard['utm_links']} tracked link(s).",
        "",
        "---",
        ("_Report generated locally by [launchmaxxing](https://github.com/caelum0x/launchmaxxing) "
         "-- no data leaves your machine._"),
    ]
    return "\n".join(lines)


__all__ = ["render_markdown"]
