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
    compare,
    content,
    dashboard,
    db,
    dogfood,
    linkcheck,
    outreach,
    painpoints,
    portfolio,
    reddit_search,
    report,
    state,
    track,
    utm,
    watch,
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
    """Build a :class:`launchmaxxing.content.ProductProfile`, lowest to highest precedence: this
    product's saved default profile (from ``launchmaxxing init --interactive``), then
    ``--profile-file`` (a local JSON file), then explicit flags. Shared by ``content`` and
    ``outreach draft``, the two commands that generate text from a product profile -- once a
    default profile is saved, neither command needs any profile flag supplied again."""
    data: dict[str, Any] = {}
    saved_profile = state.get_default_profile(state.load(_state_path(args)), args.product)
    if saved_profile:
        data.update(saved_profile)
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
    if getattr(args, "check_links", False):
        return _cmd_directories_check_links(args)
    platforms = catalog.platforms_for_category(args.category)
    if args.account_free:
        platforms = catalog.platforms_account_free(platforms)
    if getattr(args, "export", None):
        out_path = Path(args.out).expanduser() if args.out else Path(f"launchmaxxing-directories.{args.export}")
        writer = {"csv": catalog.export_csv, "json": catalog.export_json, "opml": catalog.export_opml}[args.export]
        written = writer(platforms, out_path)
        print(f"Wrote {len(platforms)} director{'y' if len(platforms) == 1 else 'ies'} to {written}")
        return 0
    if args.json:
        _print({"category": args.category or "", "platforms": list(platforms)}, as_json=True)
        return 0
    print(f"{len(platforms)} launch director{'y' if len(platforms) == 1 else 'ies'}"
          f"{f' in category {args.category!r}' if args.category else ''}"
          f"{' (account-free only)' if args.account_free else ''}:\n")
    for p in platforms:
        print(f"- {p['name']} -- {p['url']}\n    {p['note']}")
    return 0


def _cmd_directories_check_links(args: argparse.Namespace) -> int:
    """Live reachability check for every catalog submit URL (or one category's) -- see
    :mod:`launchmaxxing.linkcheck`. Automates the manual "try to submit, hit a 404" discovery
    that produced 3 past changelog fixes to this exact catalog."""
    results = linkcheck.check_all(RequestsTransport(), category=args.category)
    broken = linkcheck.broken(results)
    rows = [{"id": r.platform_id, "name": r.name, "url": r.url, "ok": r.ok,
             "status_code": r.status_code, "final_url": r.final_url, "note": r.note} for r in results]
    if args.json:
        _print({"category": args.category or "", "checked": len(results), "broken": len(broken),
                "results": rows}, as_json=True)
        return 1 if broken else 0
    print(f"Checked {len(results)} director{'y' if len(results) == 1 else 'ies'}"
          f"{f' in category {args.category!r}' if args.category else ''}: "
          f"{len(results) - len(broken)} reachable, {len(broken)} broken.\n")
    for r in results:
        marker = "OK  " if r.ok else "FAIL"
        print(f"[{marker}] {r.name} -- {r.url}\n       {r.note}")
    if broken:
        print(f"\n{len(broken)} director{'y' if len(broken) == 1 else 'ies'} need a catalog fix "
              "in src/launchmaxxing/catalog.py (dead URL, or account_free no longer true).")
    return 1 if broken else 0


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
    conn = db.connect(_db_path(args))
    try:
        result = checklist.build(app_state, args.product, conn=conn)
    finally:
        conn.close()
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
    if getattr(args, "competitors", None):
        return _cmd_backlinks_many(args)
    if not args.domain:
        print("error: either a single domain, or --competitors FILE, is required", file=sys.stderr)
        return 1
    transport = RequestsTransport() if args.allow_live else None
    try:
        result = backlinks.fetch(args.domain, transport=transport, allow_live=args.allow_live,
                                 category=args.category, account_free_only=args.account_free)
    except backlinks.BacklinkError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        return 1
    _print(result, as_json=args.json)
    return 0


def _cmd_backlinks_many(args: argparse.Namespace) -> int:
    """``backlinks --competitors file.txt``: run the lookup across every domain in the file in
    one pass and union/dedupe the directories they're findable through into one "submit here
    too" list (see :func:`launchmaxxing.backlinks.fetch_many`)."""
    try:
        domains = backlinks.read_domains_file(args.competitors)
    except OSError as exc:
        print(f"error: could not read --competitors file: {exc}", file=sys.stderr)
        return 1
    if not domains:
        print(f"error: {args.competitors!r} has no domains (blank lines and '#' comments are skipped)",
              file=sys.stderr)
        return 1
    transport = RequestsTransport() if args.allow_live else None
    result = backlinks.fetch_many(domains, transport=transport, allow_live=args.allow_live,
                                  category=args.category, account_free_only=args.account_free)
    if args.export:
        out_path = Path(args.out).expanduser() if args.out else Path("launchmaxxing-submit-here-too.csv")
        written = backlinks.export_csv(result["submit_here_too"], out_path)
        print(f"Wrote {result['count']} \"submit here too\" director{'y' if result['count'] == 1 else 'ies'} "
              f"(across {len(domains)} competitor domain(s)) to {written}")
        return 0
    if args.json:
        _print(result, as_json=True)
        return 0
    print(f"{result['count']} \"submit here too\" director{'y' if result['count'] == 1 else 'ies'} across "
          f"{len(domains)} competitor domain(s) ({', '.join(domains)}):\n")
    for entry in result["submit_here_too"]:
        print(f"- {entry['name']} -- {entry['url']} (via {entry['found_via']}, {entry['source']})")
    return 0


# --------------------------------------------------------------------------- #
# pain-points
# --------------------------------------------------------------------------- #
def _cmd_pain_points(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    sources = tuple(args.source) if args.source else painpoints.SOURCES
    merged = painpoints.search_all(RequestsTransport(), query=args.query, subreddits=args.subreddit,
                                   limit=args.limit, sources=sources)
    rows = [{"source": t.source, "thread_url": t.url, "thread_title": t.title, "snippet": t.snippet,
             "community": t.community, "upvotes": t.upvotes, "age_days": t.age_days,
             "draft_reply": reddit_search.draft_reply(t.title, t.snippet, args.product or "")}
            for t in merged["threads"]]
    saved = state.add_pain_point_drafts(app_state, query=args.query, product_name=args.product or "", threads=rows)
    state.save(app_state, path)
    result = {"query": args.query, "count": len(saved), "threads": saved, "source_status": merged["status"],
              "note": "Drafts only -- review and post these yourself, nothing here posts anywhere."}
    if args.json:
        _print(result, as_json=True)
        return 0
    print(f"{result['count']} pain-point thread(s) for {args.query!r} across "
          f"{', '.join(painpoints.SOURCE_LABELS[s] for s in sources)} (drafts saved locally):\n")
    for t in saved:
        label = f"r/{t['community']}" if t.get("source", "reddit") == "reddit" else t["community"]
        print(f"- [{label}] {t['thread_title']} ({t['upvotes']} upvotes, {t['age_days']}d old)")
        print(f"  {t['thread_url']}")
        print(f"  draft reply: {t['draft_reply']}\n")
    for source, info in merged["status"].items():
        if not info["ok"]:
            print(f"({painpoints.SOURCE_LABELS[source]}: {info['reason']})")
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
    elif isinstance(body, dict) and "subject" in body and "body" in body:
        subject = body["subject"]
        print(f"Subject ({subject['length']}/{subject['limit']} chars): {subject['text']}")
        if subject["hype_words"]:
            print(f"  (hype words to reconsider: {', '.join(subject['hype_words'])})")
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
    single_platform_generators: dict[str, Any] = {
        "product_hunt": lambda: {"tagline": content.product_hunt_tagline(profile),
                                 "description": content.product_hunt_description(profile)},
        "show_hn": lambda: content.show_hn_title(profile),
        "ask_hn": lambda: content.ask_hn_title(profile),
        "twitter": lambda: content.twitter_launch_thread(profile),
        "reddit": lambda: content.reddit_post(profile),
        "linkedin": lambda: content.linkedin_post(profile),
        "indie_hackers": lambda: content.indie_hackers_post(profile),
        "cold_pitch_email": lambda: content.cold_pitch_email(profile, contact_name=args.contact_name or ""),
        "community_intro": lambda: content.community_intro_post(profile),
        "newsletter_sponsor_pitch": lambda: content.newsletter_sponsor_pitch(profile),
    }
    if args.platform == "all":
        result: Any = content.generate_all(profile)
    else:
        result = single_platform_generators[args.platform]()

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
                                      handle=args.handle, status=args.status, note=args.note,
                                      email=getattr(args, "email", "") or "")
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
    if args.csv:
        csv_path = outreach.write_contacts_csv(rows, Path(args.csv).expanduser())
        print(f"Wrote {len(rows)} outreach contact(s) to {csv_path}")
        return 0
    print(f"{len(rows)} outreach contact(s) for {args.product}:\n")
    for r in rows:
        line = f"- {r['id']} [{r['status']}] {r['name']} ({r['channel']})"
        if r["handle"]:
            line += f" {r['handle']}"
        if r["send_status"]:
            line += f" -- send: {r['send_status']}"
        print(line)
        if r["note"]:
            print(f"    {r['note']}")
    print("\nUse the id on the left with 'outreach status <id> ...' or 'outreach send <id>'.")
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


def _cmd_outreach_send(args: argparse.Namespace) -> int:
    """``outreach send <contact_id>``: drafts the channel-appropriate cold-outreach message for
    this contact (reusing :func:`launchmaxxing.outreach.draft_message`, the exact same text
    ``outreach draft`` would print) and actually sends it as an email via the user's own SMTP
    credentials (:func:`launchmaxxing.outreach.send_email`), then records a ``sent_at`` timestamp
    and delivery status on the contact row -- moving outreach from draft-only to drafted-and-
    actually-sent-and-tracked. If the contact's own pipeline status is still ``not_contacted``, a
    successful send auto-advances it to ``contacted`` (the signal
    :mod:`launchmaxxing.checklist`'s ``cold_outreach`` auto-derivation looks for)."""
    conn = db.connect(_db_path(args))
    try:
        contact = db.get_outreach_contact(conn, args.contact_id)
        if contact is None:
            print(f"error: contact not found: {args.contact_id!r}", file=sys.stderr)
            return 1
        to_email = (args.to or contact["email"] or (contact["handle"] if "@" in contact["handle"] else "")).strip()
        if not to_email:
            print(f"error: no email address on file for {contact['name']!r} -- pass --to "
                  "you@example.com, or set one next time with 'outreach add --email'.", file=sys.stderr)
            return 1
        args.product = contact["product_name"]
        try:
            profile = _build_profile(args)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        body = outreach.draft_message(contact["channel"], profile, contact_name=contact["name"])
        subject = (args.subject or f"Quick note from {profile.name}").strip()
        if len(subject) > content.COLD_EMAIL_SUBJECT_MAX:
            subject = subject[: content.COLD_EMAIL_SUBJECT_MAX - 1].rstrip() + "…"
        try:
            outreach.send_email(to_email=to_email, subject=subject, body=body)
        except outreach.OutreachSendError as exc:
            db.mark_outreach_sent(conn, args.contact_id, status="failed", error=exc.message)
            print(f"error: {exc.message}", file=sys.stderr)
            return 1
        updated = db.mark_outreach_sent(conn, args.contact_id, status="sent")
        if contact["status"] == "not_contacted":
            updated = db.update_outreach_status(conn, args.contact_id, "contacted",
                                                note="auto: marked contacted after a successful outreach send.")
    finally:
        conn.close()
    if args.json:
        _print({"contact": updated, "to": to_email, "subject": subject, "body": body}, as_json=True)
        return 0
    print(f"Sent to {to_email} ({contact['name']}, {contact['channel']}) at {updated['sent_at']}.")
    print(f"Subject: {subject}\n{body}")
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
    if args.csv:
        csv_path = utm.write_links_csv(rows, Path(args.csv).expanduser())
        print(f"Wrote {len(rows)} UTM link(s) to {csv_path}")
        return 0
    print(f"{len(rows)} UTM link(s) for {args.product}:\n")
    for r in rows:
        print(f"- {r['full_url']}")
    return 0


# --------------------------------------------------------------------------- #
# watch -- always-on background poll + native OS notification
# --------------------------------------------------------------------------- #
def _cmd_watch(args: argparse.Namespace) -> int:
    state_path, db_path = _state_path(args), _db_path(args)
    note = "" if watch.NOTIFY_SUPPORTED else " (no native notifications on this OS -- logging to stdout only)"
    print(f"Watching {args.product!r} every {args.interval}s{note}. Ctrl-C to stop.")
    try:
        watch.run_loop(
            lambda: state.load(state_path), lambda: db.connect(db_path), args.product,
            interval_s=args.interval, category=args.category, stale_days=args.stale_days,
            max_cycles=args.cycles,
        )
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


# --------------------------------------------------------------------------- #
# dogfood -- launchmaxxing submitting itself to its own newer catalog entries
# --------------------------------------------------------------------------- #
def _cmd_dogfood(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    conn = db.connect(_db_path(args))
    try:
        pending = dogfood.pending_targets(app_state)
        if not pending:
            print("Nothing pending -- every dogfood target directory is already submitted/live.")
            return 0
        results = dogfood.run(app_state, conn, evidence_dir=args.evidence_dir,
                              mark_submitted=args.mark_submitted)
    finally:
        if args.mark_submitted:
            state.save(app_state, path)
        conn.close()
    if args.json:
        _print({"results": results}, as_json=True)
        return 0
    print(f"Generated dogfood copy for {len(results)} pending director{'y' if len(results) == 1 else 'ies'}:\n")
    for r in results:
        acct = "no account needed" if r["account_free"] else "free account required"
        mark = "marked submitted" if r["marked_submitted"] else "NOT marked submitted yet"
        print(f"- {r['name']} ({acct}) -- {r['url']}")
        print(f"    copy: {r['evidence_path']} ({mark})")
    if not args.mark_submitted:
        print("\nAfter you actually paste the copy above and click submit on each site, either "
              "re-run this with --mark-submitted, or run the usual tracker command per directory:")
        for r in results:
            print(f'  launchmaxxing submit "launchmaxxing" {r["platform_id"]} submitted '
                  f'--note "see {Path(r["evidence_path"]).name}"')
    return 0


# --------------------------------------------------------------------------- #
# compare -- the factual competitor comparison table from STRATEGY-2026-10-23.md
# --------------------------------------------------------------------------- #
def _cmd_compare(args: argparse.Namespace) -> int:
    if args.json:
        _print({"competitors": list(compare.COMPETITORS)}, as_json=True)
        return 0
    if args.markdown or args.out:
        markdown = compare.render_markdown()
        if args.out:
            out_path = compare.write_markdown(Path(args.out).expanduser())
            print(f"Wrote {out_path}")
        else:
            print(markdown)
        return 0
    print(compare.render_text())
    return 0


# --------------------------------------------------------------------------- #
# portfolio -- cross-product rollup for a founder/studio running several launches
# --------------------------------------------------------------------------- #
def _cmd_portfolio(args: argparse.Namespace) -> int:
    app_state = state.load(_state_path(args))
    conn = db.connect(_db_path(args))
    try:
        result = portfolio.build(app_state, conn, stale_days=args.stale_days)
    finally:
        conn.close()
    if args.json:
        _print(result, as_json=True)
        return 0
    if result["count"] == 0:
        print("No products tracked yet -- run 'launchmaxxing init \"My Product\"' to start one.")
        return 0
    print(f"{result['count']} product(s) tracked:\n")
    header = f"{'Product':<24} {'Directories':>13} {'Checklist':>11} {'Outreach':>10} {'Last active':>14}"
    print(header)
    print("-" * len(header))
    for row in result["products"]:
        dirs = f"{row['directories_submitted']}/{row['directories_total']} ({row['directories_pct']}%)"
        chk = f"{row['checklist_done']}/{row['checklist_total']} ({row['checklist_pct']}%)"
        outreach_cell = f"{row['outreach_replied']}/{row['outreach_total']} replied"
        if row["last_active"]:
            last = f"{row['days_since_active']}d ago" if row["days_since_active"] is not None else "unknown"
        else:
            last = "never"
        stale_flag = " *" if row["stale"] else ""
        print(f"{row['product_name']:<24} {dirs:>13} {chk:>11} {outreach_cell:>10} {last:>14}{stale_flag}")
    if any(row["stale"] for row in result["products"]):
        print(f"\n* not touched in {result['stale_days']}+ days.")
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
    """Render the shareable one-page launch summary. Three interchangeable output modes share the
    exact same underlying :func:`launchmaxxing.track.build` payload, so they can never disagree:
    plain Markdown (default, for pasting into a doc/Slack), ``--json`` (the full dashboard payload,
    for piping into another script/tool), and ``--html`` (the same visual dashboard
    :mod:`launchmaxxing.dashboard`/``launchmaxxing dashboard`` render, for a one-off shareable
    file without needing a separate command)."""
    app_state = state.load(_state_path(args))
    conn = db.connect(_db_path(args))
    try:
        if args.html:
            output = dashboard.build(app_state, conn, args.product, stale_days=args.stale_days)
        else:
            dashboard_data = track.build(app_state, conn, args.product, stale_days=args.stale_days)
            output = json.dumps(dashboard_data, indent=2, sort_keys=True) if args.json \
                else report.render_markdown(dashboard_data)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    if args.out:
        out_path = Path(args.out).expanduser()
        out_path.write_text(output, encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        print(output)
    return 0


# --------------------------------------------------------------------------- #
# dashboard / serve -- the shareable static HTML visual artifact
# --------------------------------------------------------------------------- #
def _default_dashboard_path(product: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", product.strip().lower()).strip("-") or "product"
    return Path.home() / ".launchmaxxing" / "dashboards" / f"{slug}.html"


def _cmd_dashboard(args: argparse.Namespace) -> int:
    app_state = state.load(_state_path(args))
    conn = db.connect(_db_path(args))
    try:
        html_doc = dashboard.build(app_state, conn, args.product, stale_days=args.stale_days)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    out_path = Path(args.out).expanduser() if args.out else _default_dashboard_path(args.product)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Open it with: open {out_path}" if sys.platform == "darwin" else f"Open it at: {out_path}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Serve the always-fresh HTML dashboard on ``127.0.0.1`` only (never binds 0.0.0.0): a plain
    stdlib ``http.server`` handler that re-runs :func:`launchmaxxing.dashboard.build` on every GET
    request, so the page a human has open always reflects the latest local state/database without
    needing a page refresh workflow, a build step, or any third-party server/account."""
    import http.server

    state_path, db_path, product, stale_days = (
        _state_path(args), _db_path(args), args.product, args.stale_days,
    )

    class _Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *log_args: Any) -> None:
            pass  # keep stdout clean; this is a local dev-only viewer, not a service with logs.

        def do_GET(self) -> None:
            app_state = state.load(state_path)
            conn = db.connect(db_path)
            try:
                html_doc = dashboard.build(app_state, conn, product, stale_days=stale_days)
            except ValueError as exc:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(str(exc).encode("utf-8"))
                return
            finally:
                conn.close()
            body = html_doc.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    server = http.server.HTTPServer(("127.0.0.1", args.port), _Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Serving a live dashboard for {product!r} at {url} (localhost only, no account, "
          "Ctrl-C to stop).")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


# --------------------------------------------------------------------------- #
# init --interactive -- the step-by-step onboarding wizard
# --------------------------------------------------------------------------- #
def _ask(prompt: str, *, required: bool = False, default: str = "") -> str:
    while True:
        try:
            raw = input(f"{prompt}: ").strip()
        except EOFError:
            if required:
                raise ValueError(f"{prompt!r} is required but stdin closed before it was answered "
                                 "-- run 'init --interactive' from a real terminal, or use the "
                                 "non-interactive flags instead.") from None
            return default
        if raw:
            return raw
        if not required:
            return default
        print("  (required -- try again)")


def _cmd_init_interactive(args: argparse.Namespace) -> int:
    """``launchmaxxing init --interactive``: prompts step-by-step for exactly the fields
    :class:`launchmaxxing.content.ProductProfile` needs, saves the answers as this product's
    default profile (:func:`launchmaxxing.state.set_default_profile`), then falls through to the
    normal ``init`` plan output. Every later ``content``/``outreach draft`` call for the same
    product picks the saved profile back up automatically -- closes the "re-supply every flag
    every time" friction point from the journey map without changing what those commands do for
    someone who still prefers passing flags explicitly."""
    print(f"Interactive setup for {args.product!r} -- press Enter to skip an optional field.\n")
    try:
        tagline = _ask("Tagline (<=60 chars, benefit-first, e.g. 'Calorie tracking with no account')",
                       required=True)
        problem = _ask("Problem this solves (what pain does it fix?)", required=True)
        audience = _ask("Audience (who is this for, specifically?)", required=True)
        differentiator = _ask("What makes it different from existing options?", required=True)
        url = _ask("Product URL (optional)")
        pricing = _ask("Pricing (optional, e.g. 'Free' or '$9/mo')")
        subreddit = _ask("Relevant subreddit for Reddit posts (optional, no 'r/' prefix)")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    profile = {"name": args.product, "tagline": tagline, "problem": problem, "audience": audience,
               "differentiator": differentiator, "url": url, "pricing": pricing, "subreddit": subreddit}
    path = _state_path(args)
    app_state = state.load(path)
    state.set_default_profile(app_state, args.product, profile)
    state.save(app_state, path)
    print(f"\nSaved a default profile for {args.product!r} -- 'content' and 'outreach draft' for "
          "this product no longer need --tagline/--problem/--audience/--differentiator.\n")
    args.interactive = False
    return _cmd_init(args)


# --------------------------------------------------------------------------- #
# init -- the one-shot "clone and get value" command
# --------------------------------------------------------------------------- #
def _cmd_init(args: argparse.Namespace) -> int:
    if getattr(args, "interactive", False):
        return _cmd_init_interactive(args)
    path = _state_path(args)
    app_state = state.load(path)
    platforms = catalog.platforms_for_category(args.category)
    conn = db.connect(_db_path(args))
    try:
        result = checklist.build(app_state, args.product, conn=conn)
    finally:
        conn.close()
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
    p_dirs.add_argument("--account-free", action="store_true", dest="account_free",
                        help="Only list directories that can be submitted without creating an account.")
    p_dirs.add_argument("--check-links", action="store_true", dest="check_links",
                        help="Live HTTP check of every submit URL (or one --category's); flags dead "
                             "links and redirects to a login page. Exits non-zero if any are broken.")
    p_dirs.add_argument("--export", default=None, choices=("csv", "json", "opml"),
                        help="Export the (optionally filtered) catalog to this format instead of "
                             "printing it.")
    p_dirs.add_argument("--out", default=None, help="Path to write --export's output to "
                        "(default: ./launchmaxxing-directories.<format>).")
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

    p_back = sub.add_parser("backlinks", help="Competitor backlink lookup (free directory fallback by default); "
                                              "--competitors FILE for multi-competitor mode.")
    p_back.add_argument("domain", nargs="?", default=None)
    p_back.add_argument("--competitors", default=None, help="Path to a text file with one "
                        "competitor domain per line (# comments/blank lines ignored); runs the "
                        "lookup across all of them and unions/dedupes a 'submit here too' list, "
                        "instead of a single --domain lookup.")
    p_back.add_argument("--allow-live", action="store_true",
                        help="Spend a real API call (needs CRAWLGRAPH_API_KEY or DATAFORSEO_LOGIN/PASSWORD).")
    p_back.add_argument("--category", default=None, choices=(*catalog.all_categories(), None), metavar="CATEGORY",
                        help="Narrow the free fallback's directory list to one category, e.g. 'ai'.")
    p_back.add_argument("--account-free", action="store_true", dest="account_free",
                        help="Narrow the free fallback's directory list to account-free directories only.")
    p_back.add_argument("--export", default=None, choices=("csv",), help="With --competitors, "
                        "export the combined 'submit here too' list to a CSV file instead of printing it.")
    p_back.add_argument("--out", default=None, help="Path for --export's output "
                        "(default: ./launchmaxxing-submit-here-too.csv).")
    _add_common(p_back)
    p_back.set_defaults(func=_cmd_backlinks)

    p_pain = sub.add_parser("pain-points", help="Read-only pain-point search (Reddit, Hacker News, "
                                                "Indie Hackers) + draft replies.")
    p_pain.add_argument("query")
    p_pain.add_argument("--subreddit", action="append", default=[], dest="subreddit",
                        help="Restrict Reddit results to this subreddit; repeatable.")
    p_pain.add_argument("--source", action="append", default=[], dest="source",
                        choices=painpoints.SOURCES,
                        help="Restrict to this source; repeatable. Default: all sources "
                             f"({', '.join(painpoints.SOURCES)}).")
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
    p_content.add_argument("--contact-name", default="", help="Used only by cold_pitch_email, for "
                           "a personalized greeting.")
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
    p_o_add.add_argument("--email", default="", help="Email address to use for 'outreach send'; "
                         "if omitted, 'outreach send' falls back to --handle when it looks like "
                         "an email address.")
    p_o_add.add_argument("--status", default="not_contacted", choices=db.OUTREACH_STATUSES)
    p_o_add.add_argument("--note", default="")
    _add_common(p_o_add)
    p_o_add.set_defaults(func=_cmd_outreach_add)

    p_o_list = outreach_sub.add_parser("list", help="List tracked outreach contacts.")
    p_o_list.add_argument("product")
    p_o_list.add_argument("--status", default=None, choices=db.OUTREACH_STATUSES)
    p_o_list.add_argument("--csv", default=None, help="Write contacts to this CSV file instead of stdout, for "
                          "import into Gmail mail-merge or a spreadsheet.")
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

    p_o_send = outreach_sub.add_parser("send", help="Actually send a drafted cold-outreach "
                                                    "message via your own SMTP credentials, and "
                                                    "record delivery status.")
    p_o_send.add_argument("contact_id")
    p_o_send.add_argument("--to", default=None, help="Recipient email address; defaults to the "
                          "contact's --email (or --handle, if it looks like an email).")
    p_o_send.add_argument("--subject", default=None, help="Email subject line; defaults to "
                          "'Quick note from <product name>'.")
    _add_profile_flags(p_o_send)
    _add_common(p_o_send)
    p_o_send.set_defaults(func=_cmd_outreach_send)

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
    p_u_list.add_argument("--csv", default=None, help="Write links to this CSV file instead of stdout, for "
                          "import into a spreadsheet.")
    _add_common(p_u_list)
    p_u_list.set_defaults(func=_cmd_utm_list)

    p_watch = sub.add_parser("watch", help="Always-on background poll: notifies (native macOS "
                                          "notification, or stdout elsewhere) when a directory "
                                          "link dies or an outreach contact goes stale.")
    p_watch.add_argument("product")
    p_watch.add_argument("--interval", type=int, default=watch.DEFAULT_INTERVAL_S,
                         help=f"Seconds between polls (default: {watch.DEFAULT_INTERVAL_S}).")
    p_watch.add_argument("--category", default=None, choices=(*catalog.all_categories(), None), metavar="CATEGORY",
                         help="Only link-check this category's directories, instead of the full catalog.")
    p_watch.add_argument("--stale-days", type=int, default=track.DEFAULT_STALE_DAYS)
    p_watch.add_argument("--cycles", type=int, default=None, help="Stop after this many poll "
                         "cycles instead of running forever (mainly for scripting/testing).")
    _add_common(p_watch)
    p_watch.set_defaults(func=_cmd_watch)

    p_dogfood = sub.add_parser("dogfood", help="Generate ready-to-paste copy for launchmaxxing's "
                                               "own un-self-submitted catalog directories.")
    p_dogfood.add_argument("--evidence-dir", default="launch-evidence",
                           help="Directory to write the generated Markdown copy files into "
                                "(default: ./launch-evidence, this project's existing evidence folder).")
    p_dogfood.add_argument("--mark-submitted", action="store_true", dest="mark_submitted",
                           help="Only pass this after you have actually pasted the copy and "
                                "clicked submit on each site -- records 'submitted' via the same "
                                "tracker 'launchmaxxing submit' uses. Never set automatically.")
    _add_common(p_dogfood)
    p_dogfood.set_defaults(func=_cmd_dogfood)

    p_compare = sub.add_parser("compare", help="Factual competitor comparison table "
                                              "(launchmaxxing vs. SubmitMap/OpenLaunch/SubmitFleet/paid services).")
    p_compare.add_argument("--markdown", action="store_true", help="Print a ready-to-paste "
                           "README Markdown table instead of the plain-text summary.")
    p_compare.add_argument("--out", default=None, help="Write the Markdown table to this file "
                           "instead of stdout (implies --markdown).")
    _add_common(p_compare)
    p_compare.set_defaults(func=_cmd_compare)

    p_portfolio = sub.add_parser("portfolio", help="Cross-product rollup table for every product "
                                                   "tracked locally -- for running several launches at once.")
    p_portfolio.add_argument("--stale-days", type=int, default=track.DEFAULT_STALE_DAYS)
    _add_common(p_portfolio)
    p_portfolio.set_defaults(func=_cmd_portfolio)

    p_track = sub.add_parser("track", help="Cross-cutting status dashboard: directories, checklist, outreach, "
                                           "content, stale reminders.")
    p_track.add_argument("product")
    p_track.add_argument("--stale-days", type=int, default=track.DEFAULT_STALE_DAYS)
    _add_common(p_track)
    p_track.set_defaults(func=_cmd_track)

    p_report = sub.add_parser("report", help="Render a shareable launch report -- Markdown "
                                             "(default), --json, or --html.")
    p_report.add_argument("product")
    p_report.add_argument("--stale-days", type=int, default=track.DEFAULT_STALE_DAYS)
    p_report.add_argument("--html", action="store_true", help="Render the full visual HTML "
                          "dashboard (same template as 'launchmaxxing dashboard') instead of "
                          "Markdown.")
    p_report.add_argument("--out", default=None, help="Write the report to this file instead of stdout.")
    _add_common(p_report)
    p_report.set_defaults(func=_cmd_report)

    p_dash = sub.add_parser("dashboard", help="Render a self-contained static HTML dashboard "
                                              "(progress rings + submission timeline).")
    p_dash.add_argument("product")
    p_dash.add_argument("--stale-days", type=int, default=track.DEFAULT_STALE_DAYS)
    p_dash.add_argument("--out", default=None, help="Write the HTML to this path instead of "
                        "~/.launchmaxxing/dashboards/<product-slug>.html")
    _add_common(p_dash)
    p_dash.set_defaults(func=_cmd_dashboard)

    p_serve = sub.add_parser("serve", help="Serve a live-refreshing HTML dashboard on "
                                           "localhost only (no account, no external server).")
    p_serve.add_argument("product")
    p_serve.add_argument("--stale-days", type=int, default=track.DEFAULT_STALE_DAYS)
    p_serve.add_argument("--port", type=int, default=8808)
    _add_common(p_serve)
    p_serve.set_defaults(func=_cmd_serve)

    p_init = sub.add_parser("init", help="One-shot personalized launch plan: directories + checklist.")
    p_init.add_argument("product")
    p_init.add_argument("--category", default=None, choices=(*catalog.all_categories(), None), metavar="CATEGORY")
    p_init.add_argument("--interactive", action="store_true", help="Prompt step-by-step for the "
                        "product profile (tagline/problem/audience/differentiator/url/pricing/"
                        "subreddit) and save it as this product's default, instead of just "
                        "printing the directory + checklist plan.")
    _add_common(p_init)
    p_init.set_defaults(func=_cmd_init)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
