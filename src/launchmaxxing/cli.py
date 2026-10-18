"""The ``launchmaxxing`` command-line tool.

Everything here is read-only against third parties except the local state
file and local SQLite database: nothing submits to a launch directory, posts
to Reddit, sends a cold email, or spends backlink API credits unless you
explicitly pass ``--allow-live`` with a key configured. Run
``launchmaxxing init "My Product"`` for a one-shot personalized launch plan,
``launchmaxxing track "My Product"`` any time after that to see what's still
open, or any subcommand with ``-h`` for details.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from launchmaxxing import (
    __version__,
    backlinks,
    catalog,
    checklist,
    content,
    db,
    outreach,
    reddit_search,
    report,
    state,
    track,
    utm,
)
from launchmaxxing.transport import RequestsTransport

FOOTER = (
    "\n---\nBuilt by the team behind Menivor (https://menivor.com) -- AI video creation for\n"
    "founders launching products. launchmaxxing is free and open source; Menivor is the paid\n"
    "product that funds it.\n"
)


def _print(data: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return
    print(data if isinstance(data, str) else json.dumps(data, indent=2, sort_keys=True))


def _state_path(args: argparse.Namespace) -> Path | None:
    return Path(args.state_file).expanduser() if getattr(args, "state_file", None) else None


def _db_path(args: argparse.Namespace) -> Path | None:
    return Path(args.db_file).expanduser() if getattr(args, "db_file", None) else None


def _build_profile(args: argparse.Namespace) -> content.ProductProfile:
    """Build a :class:`launchmaxxing.content.ProductProfile` from ``--profile-file`` (a local JSON
    file) and/or explicit flags, flags taking precedence. Shared by ``content`` and
    ``outreach draft``, the two commands that generate text from a product profile."""
    data: dict[str, Any] = {}
    profile_file = getattr(args, "profile_file", None)
    if profile_file:
        raw = json.loads(Path(profile_file).expanduser().read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("--profile-file must contain a JSON object")
        data.update(raw)
    data.setdefault("name", args.product)
    for field_name in ("tagline", "problem", "audience", "differentiator", "url", "pricing", "subreddit"):
        value = getattr(args, field_name, None)
        if value:
            data[field_name] = value
    missing = [f for f in ("tagline", "problem", "audience", "differentiator") if not data.get(f)]
    if missing:
        raise ValueError(f"missing required profile field(s): {', '.join(missing)} (pass "
                         "--tagline/--problem/--audience/--differentiator, or --profile-file)")
    return content.ProductProfile(
        name=data["name"], tagline=data["tagline"], problem=data["problem"], audience=data["audience"],
        differentiator=data["differentiator"], url=data.get("url", ""), pricing=data.get("pricing", ""),
        subreddit=data.get("subreddit", ""),
    )


def _add_profile_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--tagline", default=None)
    p.add_argument("--problem", default=None)
    p.add_argument("--audience", default=None)
    p.add_argument("--differentiator", default=None)
    p.add_argument("--url", default=None)
    p.add_argument("--pricing", default=None)
    p.add_argument("--subreddit", default=None)
    p.add_argument("--profile-file", default=None,
                   help="JSON file with name/tagline/problem/audience/differentiator/url/pricing/subreddit, "
                        "instead of (or combined with, flags win) passing each flag.")


# --------------------------------------------------------------------------- #
# directories
# --------------------------------------------------------------------------- #
def _cmd_directories(args: argparse.Namespace) -> int:
    platforms = catalog.platforms_for_category(args.category)
    if args.json:
        _print({"category": args.category or "", "platforms": list(platforms)}, as_json=True)
        return 0
    print(f"{len(platforms)} launch director{'y' if len(platforms) == 1 else 'ies'}"
          f"{f' in category {args.category!r}' if args.category else ''}:\n")
    for p in platforms:
        print(f"- {p['name']} -- {p['url']}\n    {p['note']}")
    return 0


# --------------------------------------------------------------------------- #
# submit / platform-status -- directory submission status, with history
# --------------------------------------------------------------------------- #
def _record_submission(args: argparse.Namespace) -> dict[str, Any]:
    path = _state_path(args)
    app_state = state.load(path)
    row = state.set_platform_status(app_state, product_name=args.product, platform_id=args.platform_id,
                                    status=args.status, note=args.note or "")
    state.save(app_state, path)
    conn = db.connect(_db_path(args))
    try:
        db.log_submission_event(conn, product_name=args.product, platform_id=args.platform_id,
                                status=args.status, note=args.note or "")
    finally:
        conn.close()
    return row


def _cmd_platform_status(args: argparse.Namespace) -> int:
    try:
        row = _record_submission(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _print({"product_name": args.product, "platform_id": args.platform_id, **row}, as_json=args.json)
    return 0


def _cmd_submit(args: argparse.Namespace) -> int:
    if args.history:
        conn = db.connect(_db_path(args))
        try:
            events = db.list_submission_events(conn, args.product, platform_id=args.platform_id)
        finally:
            conn.close()
        if args.json:
            _print({"events": events}, as_json=True)
            return 0
        scope = f" / {args.platform_id}" if args.platform_id else ""
        print(f"{len(events)} submission event(s) for {args.product}{scope}:\n")
        for e in events:
            note = f" ({e['note']})" if e["note"] else ""
            print(f"- {e['created_at']}: {e['platform_id']} -> {e['status']}{note}")
        return 0
    if not args.platform_id or not args.status:
        print("error: platform_id and status are required unless --history is set", file=sys.stderr)
        return 1
    return _cmd_platform_status(args)


# --------------------------------------------------------------------------- #
# checklist
# --------------------------------------------------------------------------- #
def _cmd_checklist(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    result = checklist.build(app_state, args.product)
    if args.json:
        _print(result, as_json=True)
        return 0
    print(f"Launch checklist for {result['product_name']} -- {result['done']}/{result['total']} steps done\n")
    for s in result["steps"]:
        mark = "x" if s["status"] == "done" else " "
        print(f"[{mark}] {s['title']} ({s['key']})\n    {s['detail']}")
    return 0


def _cmd_checklist_step(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    try:
        row = state.set_step_status(app_state, product_name=args.product, step_key=args.step_key,
                                    status=args.status, note=args.note or "")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    state.save(app_state, path)
    _print({"product_name": args.product, "step_key": args.step_key, **row}, as_json=args.json)
    return 0


# --------------------------------------------------------------------------- #
# backlinks
# --------------------------------------------------------------------------- #
def _cmd_backlinks(args: argparse.Namespace) -> int:
    transport = RequestsTransport() if args.allow_live else None
    try:
        result = backlinks.fetch(args.domain, transport=transport, allow_live=args.allow_live)
    except backlinks.BacklinkError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    _print(result, as_json=args.json)
    return 0


# --------------------------------------------------------------------------- #
# pain-points
# --------------------------------------------------------------------------- #
def _cmd_pain_points(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    try:
        threads = reddit_search.search(RequestsTransport(), query=args.query, subreddits=args.subreddit,
                                       limit=args.limit)
    except reddit_search.RedditSearchError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    rows = [{"thread_url": t.url, "thread_title": t.title, "snippet": t.snippet, "subreddit": t.subreddit,
             "upvotes": t.upvotes, "age_days": t.age_days,
             "draft_reply": reddit_search.draft_reply(t.title, t.snippet, args.product or "")} for t in threads]
    saved = state.add_pain_point_drafts(app_state, query=args.query, product_name=args.product or "", threads=rows)
    state.save(app_state, path)
    result = {"query": args.query, "count": len(saved), "threads": saved,
              "note": "Drafts only -- review and post these yourself, nothing here posts to Reddit."}
    if args.json:
        _print(result, as_json=True)
        return 0
    print(f"{result['count']} pain-point thread(s) for {args.query!r} (drafts saved locally):\n")
    for t in saved:
        print(f"- r/{t['subreddit']} -- {t['thread_title']} ({t['upvotes']} upvotes, {t['age_days']}d old)")
        print(f"  {t['thread_url']}")
        print(f"  draft reply: {t['draft_reply']}\n")
    print(result["note"])
    return 0


def _cmd_drafts(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    drafts = state.list_pain_point_drafts(app_state, status=args.status, product_name=args.product)
    _print({"drafts": drafts}, as_json=args.json)
    return 0


def _cmd_draft_status(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    try:
        row = state.set_draft_status(app_state, args.draft_id, args.status)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    state.save(app_state, path)
    _print(row, as_json=args.json)
    return 0


# --------------------------------------------------------------------------- #
# content -- local, template-based launch copy
# --------------------------------------------------------------------------- #
def _print_content_piece(body: Any) -> None:
    if isinstance(body, list):
        for i, line in enumerate(body, 1):
            print(f"{i}. {line}")
    elif isinstance(body, dict) and "title" in body and "body" in body:
        print(f"Title: {body['title']}")
        print(body["body"])
    elif isinstance(body, dict) and "tagline" in body:
        tagline, desc = body["tagline"], body["description"]
        print(f"Tagline ({tagline['length']}/{tagline['limit']} chars): {tagline['text']}")
        if tagline["hype_words"]:
            print(f"  (hype words to reconsider: {', '.join(tagline['hype_words'])})")
        print(f"Description ({desc['length']}/{desc['limit']} chars): {desc['text']}")
    elif isinstance(body, dict) and "text" in body:
        print(f"{body['text']} ({body['length']}/{body['limit']} chars)")
    else:
        print(body)


def _cmd_content(args: argparse.Namespace) -> int:
    try:
        profile = _build_profile(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.platform == "all":
        result: Any = content.generate_all(profile)
    elif args.platform == "product_hunt":
        result = {"tagline": content.product_hunt_tagline(profile),
                  "description": content.product_hunt_description(profile)}
    elif args.platform == "show_hn":
        result = content.show_hn_title(profile)
    elif args.platform == "twitter":
        result = content.twitter_launch_thread(profile)
    elif args.platform == "reddit":
        result = content.reddit_post(profile)
    else:
        result = content.linkedin_post(profile)

    if args.save:
        conn = db.connect(_db_path(args))
        try:
            if args.platform == "all":
                for platform_key, body in result.items():
                    db.add_content_draft(conn, product_name=args.product, platform=platform_key,
                                         body=json.dumps(body))
            else:
                db.add_content_draft(conn, product_name=args.product, platform=args.platform,
                                     body=json.dumps(result))
        finally:
            conn.close()

    if args.json:
        _print(result, as_json=True)
        return 0
    if args.platform == "all":
        for platform_key, body in result.items():
            print(f"=== {platform_key} ===")
            _print_content_piece(body)
            print()
    else:
        _print_content_piece(result)
    return 0


# --------------------------------------------------------------------------- #
# outreach -- local contact pipeline + message drafts
# --------------------------------------------------------------------------- #
def _cmd_outreach_add(args: argparse.Namespace) -> int:
    conn = db.connect(_db_path(args))
    try:
        row = db.add_outreach_contact(conn, product_name=args.product, name=args.name, channel=args.channel,
                                      handle=args.handle, status=args.status, note=args.note)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    _print(row, as_json=args.json)
    return 0


def _cmd_outreach_list(args: argparse.Namespace) -> int:
    conn = db.connect(_db_path(args))
    try:
        rows = db.list_outreach_contacts(conn, product_name=args.product, status=args.status)
    finally:
        conn.close()
    if args.json:
        _print({"contacts": rows}, as_json=True)
        return 0
    print(f"{len(rows)} outreach contact(s) for {args.product}:\n")
    for r in rows:
        line = f"- [{r['status']}] {r['name']} ({r['channel']})"
        if r["handle"]:
            line += f" {r['handle']}"
        print(line)
        if r["note"]:
            print(f"    {r['note']}")
    return 0


def _cmd_outreach_status(args: argparse.Namespace) -> int:
    conn = db.connect(_db_path(args))
    try:
        row = db.update_outreach_status(conn, args.contact_id, args.status, args.note)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    _print(row, as_json=args.json)
    return 0


def _cmd_outreach_draft(args: argparse.Namespace) -> int:
    try:
        profile = _build_profile(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    message = outreach.draft_message(args.channel, profile, contact_name=args.contact_name)
    if args.json:
        _print({"channel": args.channel, "message": message}, as_json=True)
        return 0
    print(message)
    return 0


# --------------------------------------------------------------------------- #
# utm -- local link builder + history
# --------------------------------------------------------------------------- #
def _cmd_utm_build(args: argparse.Namespace) -> int:
    defaults = utm.defaults_for_platform(args.platform_id)
    source = args.source or defaults["source"]
    medium = args.medium or defaults["medium"]
    campaign = args.campaign or re.sub(r"[^a-z0-9]+", "-", args.product.strip().lower()).strip("-") or "launch"
    try:
        full_url = utm.build_url(args.base_url, source=source, medium=medium, campaign=campaign,
                                 content=args.content)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    conn = db.connect(_db_path(args))
    try:
        row = db.add_utm_link(conn, product_name=args.product, base_url=args.base_url, source=source,
                              medium=medium, campaign=campaign, full_url=full_url, platform_id=args.platform_id,
                              content=args.content)
    finally:
        conn.close()
    _print(row, as_json=args.json)
    return 0


def _cmd_utm_list(args: argparse.Namespace) -> int:
    conn = db.connect(_db_path(args))
    try:
        rows = db.list_utm_links(conn, product_name=args.product)
    finally:
        conn.close()
    if args.json:
        _print({"links": rows}, as_json=True)
        return 0
    print(f"{len(rows)} UTM link(s) for {args.product}:\n")
    for r in rows:
        print(f"- {r['full_url']}")
    return 0


# --------------------------------------------------------------------------- #
# track -- cross-cutting status dashboard
# --------------------------------------------------------------------------- #
def _cmd_track(args: argparse.Namespace) -> int:
    app_state = state.load(_state_path(args))
    conn = db.connect(_db_path(args))
    try:
        result = track.build(app_state, conn, args.product, stale_days=args.stale_days)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    if args.json:
        _print(result, as_json=True)
        return 0
    age = f" ({result['age_days']}d tracked)" if result["age_days"] is not None else " (not started yet)"
    print(f"Launch status for {result['product_name']}{age}\n")
    d = result["directories"]
    print(f"Directories: {d['submitted_or_live']}/{d['total']} submitted/live, {d['not_started']} not started.")
    if d["stale"]:
        print(f"  overdue ({result['stale_days']}+ days untouched):")
        for p in d["stale"]:
            print(f"    - {p['name']} -- {p['url']}")
    c = result["checklist"]
    print(f"\nChecklist: {c['done']}/{c['total']} steps done.")
    o = result["outreach"]
    status_summary = ", ".join(f"{v} {k}" for k, v in sorted(o["by_status"].items()))
    print(f"\nOutreach: {o['total']} contact(s) tracked" + (f" ({status_summary})" if status_summary else "") + ".")
    if o["stale_followups"]:
        print("  awaiting follow-up:")
        for contact in o["stale_followups"]:
            print(f"    - {contact['name']} ({contact['channel']})")
    print(f"\nContent drafts: {result['content_drafts']}. UTM links tracked: {result['utm_links']}.")
    return 0


# --------------------------------------------------------------------------- #
# report -- shareable one-page Markdown summary
# --------------------------------------------------------------------------- #
def _cmd_report(args: argparse.Namespace) -> int:
    app_state = state.load(_state_path(args))
    conn = db.connect(_db_path(args))
    try:
        dashboard = track.build(app_state, conn, args.product, stale_days=args.stale_days)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    if args.json:
        _print(dashboard, as_json=True)
        return 0
    markdown = report.render_markdown(dashboard)
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.write_text(markdown, encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        print(markdown)
    return 0


# --------------------------------------------------------------------------- #
# init -- the one-shot "clone and get value" command
# --------------------------------------------------------------------------- #
def _cmd_init(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    platforms = catalog.platforms_for_category(args.category)
    result = checklist.build(app_state, args.product)
    if args.json:
        _print({"product_name": args.product, "platforms": list(platforms), "checklist": result}, as_json=True)
        return 0
    print(f"Launch plan for {args.product}\n{'=' * (len(args.product) + 12)}\n")
    print(f"Step 1: submit to these {len(platforms)} directories\n")
    for p in platforms:
        print(f"  - {p['name']} -- {p['url']}")
    print(f"\nFull 10-step playbook ({result['done']}/{result['total']} done):\n")
    for s in result["steps"]:
        mark = "x" if s["status"] == "done" else " "
        print(f"  [{mark}] {s['title']} -- {s['detail']}")
    print("\nMark progress and keep working the launch with:")
    print(f'  launchmaxxing submit "{args.product}" product_hunt submitted')
    print(f'  launchmaxxing checklist-step "{args.product}" cold_outreach done')
    print(f'  launchmaxxing content "{args.product}" product_hunt --tagline "..." --problem "..." '
          '--audience "..." --differentiator "..."')
    print(f'  launchmaxxing outreach add "{args.product}" "Some Creator" creator')
    print(f'  launchmaxxing track "{args.product}"')
    print(FOOTER)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="launchmaxxing", description=__doc__)
    parser.add_argument("--version", action="version", version=f"launchmaxxing {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--state-file", default=None, help="Path to the local JSON state file "
                       "(default: ~/.launchmaxxing/state.json, or $LAUNCHMAXXING_STATE).")
        p.add_argument("--db-file", default=None, help="Path to the local SQLite database "
                       "(default: ~/.launchmaxxing/launchmaxxing.db, or $LAUNCHMAXXING_DB).")
        p.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of text.")

    p_dirs = sub.add_parser("directories", help="List launch directories (Product Hunt, PeerPush, ...).")
    p_dirs.add_argument("--category", default=None, choices=(*catalog.all_categories(), None), metavar="CATEGORY")
    _add_common(p_dirs)
    p_dirs.set_defaults(func=_cmd_directories)

    p_plat = sub.add_parser("platform-status", help="Deprecated alias for 'submit'; kept for compatibility.")
    p_plat.add_argument("product")
    p_plat.add_argument("platform_id", choices=sorted(catalog.PLATFORM_BY_ID))
    p_plat.add_argument("status", choices=state.PLATFORM_STATUSES)
    p_plat.add_argument("--note", default="")
    _add_common(p_plat)
    p_plat.set_defaults(func=_cmd_platform_status)

    p_submit = sub.add_parser("submit", help="Record a directory submission (full history kept) or show history.")
    p_submit.add_argument("product")
    p_submit.add_argument("platform_id", nargs="?", default=None, choices=sorted(catalog.PLATFORM_BY_ID))
    p_submit.add_argument("status", nargs="?", default=None, choices=state.PLATFORM_STATUSES)
    p_submit.add_argument("--note", default="")
    p_submit.add_argument("--history", action="store_true",
                          help="Show this product's (optionally one platform's) submission history.")
    _add_common(p_submit)
    p_submit.set_defaults(func=_cmd_submit)

    p_check = sub.add_parser("checklist", help="Show the 10-step first-100-users checklist for one product.")
    p_check.add_argument("product")
    _add_common(p_check)
    p_check.set_defaults(func=_cmd_checklist)

    p_step = sub.add_parser("checklist-step", help="Mark one playbook step done/pending.")
    p_step.add_argument("product")
    p_step.add_argument("step_key", choices=sorted(catalog.STEP_BY_KEY))
    p_step.add_argument("status", choices=state.STEP_STATUSES)
    p_step.add_argument("--note", default="")
    _add_common(p_step)
    p_step.set_defaults(func=_cmd_checklist_step)

    p_back = sub.add_parser("backlinks", help="Competitor backlink lookup (free directory fallback by default).")
    p_back.add_argument("domain")
    p_back.add_argument("--allow-live", action="store_true",
                        help="Spend a real API call (needs CRAWLGRAPH_API_KEY or DATAFORSEO_LOGIN/PASSWORD).")
    _add_common(p_back)
    p_back.set_defaults(func=_cmd_backlinks)

    p_pain = sub.add_parser("pain-points", help="Read-only Reddit search for pain-point threads + draft replies.")
    p_pain.add_argument("query")
    p_pain.add_argument("--subreddit", action="append", default=[], dest="subreddit",
                        help="Restrict to this subreddit; repeatable.")
    p_pain.add_argument("--product", default="", help="Your product name, used in the drafted reply.")
    p_pain.add_argument("--limit", type=int, default=10)
    _add_common(p_pain)
    p_pain.set_defaults(func=_cmd_pain_points)

    p_drafts = sub.add_parser("drafts", help="List saved pain-point reply drafts.")
    p_drafts.add_argument("--status", default=None, choices=state.DRAFT_STATUSES)
    p_drafts.add_argument("--product", default=None)
    _add_common(p_drafts)
    p_drafts.set_defaults(func=_cmd_drafts)

    p_draft_status = sub.add_parser("draft-status", help="Approve or dismiss a drafted reply. Never 'posted'.")
    p_draft_status.add_argument("draft_id")
    p_draft_status.add_argument("status", choices=state.DRAFT_STATUSES)
    _add_common(p_draft_status)
    p_draft_status.set_defaults(func=_cmd_draft_status)

    p_content = sub.add_parser("content", help="Generate local, template-based launch copy for one platform.")
    p_content.add_argument("product")
    p_content.add_argument("platform", choices=(*db.CONTENT_PLATFORMS, "all"))
    _add_profile_flags(p_content)
    p_content.add_argument("--save", action="store_true", help="Save the generated draft(s) to the local database.")
    _add_common(p_content)
    p_content.set_defaults(func=_cmd_content)

    p_outreach = sub.add_parser("outreach", help="Local outreach contact pipeline + cold-message drafts.")
    outreach_sub = p_outreach.add_subparsers(dest="outreach_command", required=True)

    p_o_add = outreach_sub.add_parser("add", help="Track a new outreach contact.")
    p_o_add.add_argument("product")
    p_o_add.add_argument("name")
    p_o_add.add_argument("channel", choices=db.OUTREACH_CHANNELS)
    p_o_add.add_argument("--handle", default="")
    p_o_add.add_argument("--status", default="not_contacted", choices=db.OUTREACH_STATUSES)
    p_o_add.add_argument("--note", default="")
    _add_common(p_o_add)
    p_o_add.set_defaults(func=_cmd_outreach_add)

    p_o_list = outreach_sub.add_parser("list", help="List tracked outreach contacts.")
    p_o_list.add_argument("product")
    p_o_list.add_argument("--status", default=None, choices=db.OUTREACH_STATUSES)
    _add_common(p_o_list)
    p_o_list.set_defaults(func=_cmd_outreach_list)

    p_o_status = outreach_sub.add_parser("status", help="Update one contact's status.")
    p_o_status.add_argument("contact_id")
    p_o_status.add_argument("status", choices=db.OUTREACH_STATUSES)
    p_o_status.add_argument("--note", default=None)
    _add_common(p_o_status)
    p_o_status.set_defaults(func=_cmd_outreach_status)

    p_o_draft = outreach_sub.add_parser("draft", help="Draft a cold-outreach message for one channel.")
    p_o_draft.add_argument("product")
    p_o_draft.add_argument("channel", choices=db.OUTREACH_CHANNELS)
    p_o_draft.add_argument("--contact-name", default="")
    _add_profile_flags(p_o_draft)
    _add_common(p_o_draft)
    p_o_draft.set_defaults(func=_cmd_outreach_draft)

    p_utm = sub.add_parser("utm", help="Local UTM link builder + history (no analytics server involved).")
    utm_sub = p_utm.add_subparsers(dest="utm_command", required=True)

    p_u_build = utm_sub.add_parser("build", help="Build + save a UTM-tagged link.")
    p_u_build.add_argument("product")
    p_u_build.add_argument("base_url")
    p_u_build.add_argument("--platform-id", default="", dest="platform_id",
                           choices=(*sorted(catalog.PLATFORM_BY_ID), ""))
    p_u_build.add_argument("--source", default=None)
    p_u_build.add_argument("--medium", default=None)
    p_u_build.add_argument("--campaign", default=None)
    p_u_build.add_argument("--content", default="")
    _add_common(p_u_build)
    p_u_build.set_defaults(func=_cmd_utm_build)

    p_u_list = utm_sub.add_parser("list", help="List previously built UTM links for one product.")
    p_u_list.add_argument("product")
    _add_common(p_u_list)
    p_u_list.set_defaults(func=_cmd_utm_list)

    p_track = sub.add_parser("track", help="Cross-cutting status dashboard: directories, checklist, outreach, "
                                           "content, stale reminders.")
    p_track.add_argument("product")
    p_track.add_argument("--stale-days", type=int, default=track.DEFAULT_STALE_DAYS)
    _add_common(p_track)
    p_track.set_defaults(func=_cmd_track)

    p_report = sub.add_parser("report", help="Render a shareable one-page Markdown launch report.")
    p_report.add_argument("product")
    p_report.add_argument("--stale-days", type=int, default=track.DEFAULT_STALE_DAYS)
    p_report.add_argument("--out", default=None, help="Write the report to this file instead of stdout.")
    _add_common(p_report)
    p_report.set_defaults(func=_cmd_report)

    p_init = sub.add_parser("init", help="One-shot personalized launch plan: directories + checklist.")
    p_init.add_argument("product")
    p_init.add_argument("--category", default=None, choices=(*catalog.all_categories(), None), metavar="CATEGORY")
    _add_common(p_init)
    p_init.set_defaults(func=_cmd_init)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
