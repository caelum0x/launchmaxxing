"""The ``launchroster`` command-line tool.

Everything here is read-only against third parties except the local state
file: nothing submits to a launch directory, posts to Reddit, or spends
backlink API credits unless you explicitly pass ``--allow-live`` with a key
configured. Run ``launchroster init "My Product"`` for a one-shot personalized
launch plan, or any subcommand with ``-h`` for details.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from launchroster import __version__, backlinks, catalog, checklist, reddit_search, state
from launchroster.transport import RequestsTransport

FOOTER = (
    "\n---\nBuilt by the team behind Menivor (https://menivor.com) -- AI video creation for\n"
    "founders launching products. launchroster is free and open source; Menivor is the paid\n"
    "product that funds it.\n"
)


def _print(data: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return
    print(data if isinstance(data, str) else json.dumps(data, indent=2, sort_keys=True))


def _state_path(args: argparse.Namespace) -> Path | None:
    return Path(args.state_file).expanduser() if getattr(args, "state_file", None) else None


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
# platform-status
# --------------------------------------------------------------------------- #
def _cmd_platform_status(args: argparse.Namespace) -> int:
    path = _state_path(args)
    app_state = state.load(path)
    try:
        row = state.set_platform_status(app_state, product_name=args.product, platform_id=args.platform_id,
                                        status=args.status, note=args.note or "")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    state.save(app_state, path)
    _print({"product_name": args.product, "platform_id": args.platform_id, **row}, as_json=args.json)
    return 0


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
    print("\nMark progress any time with:")
    print(f'  launchroster platform-status "{args.product}" product_hunt submitted')
    print(f'  launchroster checklist-step "{args.product}" cold_outreach done')
    print(FOOTER)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="launchroster", description=__doc__)
    parser.add_argument("--version", action="version", version=f"launchroster {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--state-file", default=None, help="Path to the local JSON state file "
                       "(default: ~/.launchroster/state.json, or $LAUNCHROSTER_STATE).")
        p.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of text.")

    p_dirs = sub.add_parser("directories", help="List launch directories (Product Hunt, BetaList, ...).")
    p_dirs.add_argument("--category", default=None, choices=(*catalog.all_categories(), None), metavar="CATEGORY")
    _add_common(p_dirs)
    p_dirs.set_defaults(func=_cmd_directories)

    p_plat = sub.add_parser("platform-status", help="Record what you actually submitted on one directory.")
    p_plat.add_argument("product")
    p_plat.add_argument("platform_id", choices=sorted(catalog.PLATFORM_BY_ID))
    p_plat.add_argument("status", choices=state.PLATFORM_STATUSES)
    p_plat.add_argument("--note", default="")
    _add_common(p_plat)
    p_plat.set_defaults(func=_cmd_platform_status)

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
