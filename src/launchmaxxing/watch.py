"""Background-poll watcher: re-runs the detection logic launchmaxxing already ships
(:func:`launchmaxxing.linkcheck.check_all`, :mod:`launchmaxxing.track`'s stale-directory and
stale-outreach reminders) on an interval and fires a native OS notification the moment something
*newly* changes, instead of requiring a human to remember to run ``directories --check-links`` or
``track`` by hand. Turns already-built detection logic into an always-on signal.

Notifications are native macOS notifications via ``osascript -e 'display notification'`` -- no
account, no push-notification service, no server. On any other platform, ``watch`` still runs and
still logs every detected change to stdout, it just can't pop a native OS notification; it never
crashes for lacking one.
"""

from __future__ import annotations

import platform
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from launchmaxxing import linkcheck, track
from launchmaxxing.transport import RequestsTransport

#: How often ``watch`` polls by default -- 15 minutes. Frequent enough to catch a directory
#: going dead or a contact going stale within the same working session, infrequent enough not to
#: hammer every catalog submit URL (or whichever --category subset) on a tight loop.
DEFAULT_INTERVAL_S = 900
NOTIFY_SUPPORTED = platform.system() == "Darwin"


def _osa_quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def notify(title: str, message: str, *, runner: Callable[..., Any] | None = None) -> bool:
    """Fire one native macOS notification. Returns ``True`` if a notification was actually sent,
    ``False`` if notifications aren't supported on this platform (anything but macOS) -- callers
    should still log the same message to stdout either way, so ``watch`` stays useful everywhere
    even where a native popup isn't available."""
    if not NOTIFY_SUPPORTED:
        return False
    script = f"display notification {_osa_quote(message)} with title {_osa_quote(title)}"
    run = runner or subprocess.run
    run(["osascript", "-e", script], check=False, capture_output=True)
    return True


def check_once(app_state: dict[str, Any], conn: Any, product_name: str, *, category: str | None = None,
                stale_days: int = track.DEFAULT_STALE_DAYS, transport: Any = None) -> dict[str, Any]:
    """One poll cycle, as a pure function of the current state/db: link-check the catalog (or one
    ``category``) and re-run ``track``'s stale-directory/stale-outreach detection, returning the
    *current* sets keyed by id. No notification side effects here -- :func:`diff_and_notify`
    decides what counts as newly-appeared by comparing two of these snapshots, which keeps this
    function independently testable and reusable by anything that wants a one-shot check."""
    live_transport = transport or RequestsTransport()
    link_results = linkcheck.check_all(live_transport, category=category)
    broken_links = {r.platform_id: r for r in linkcheck.broken(link_results)}
    dashboard = track.build(app_state, conn, product_name, stale_days=stale_days)
    stale_outreach = {c["id"]: c for c in dashboard["outreach"]["stale_followups"]}
    stale_directories = {p["id"]: p for p in dashboard["directories"]["stale"]}
    return {
        "broken_links": broken_links, "stale_outreach": stale_outreach,
        "stale_directories": stale_directories, "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def diff_and_notify(previous: dict[str, Any] | None, current: dict[str, Any], *, product_name: str,
                    notifier: Callable[[str, str], bool] = notify,
                    log: Callable[[str], None] = print) -> list[str]:
    """Compare ``current`` against ``previous`` (``None`` on the very first poll -- nothing counts
    as "new" yet, so the first cycle never fires a notification for something that was already
    broken/stale before ``watch`` even started) and notify once per newly-appeared broken link,
    newly-stale directory, or newly-stale outreach contact. Returns every message sent, mainly so
    tests/the CLI can assert on exactly what fired without re-parsing stdout."""
    sent: list[str] = []
    if previous is None:
        return sent
    for platform_id in set(current["broken_links"]) - set(previous["broken_links"]):
        r = current["broken_links"][platform_id]
        message = f"{product_name}: {r.name}'s submit link went dead ({r.note})."
        notifier("launchmaxxing -- directory link down", message)
        log(message)
        sent.append(message)
    for platform_id in set(current["stale_directories"]) - set(previous["stale_directories"]):
        p = current["stale_directories"][platform_id]
        message = f"{product_name}: {p['name']} is now overdue (still not submitted)."
        notifier("launchmaxxing -- directory overdue", message)
        log(message)
        sent.append(message)
    for contact_id in set(current["stale_outreach"]) - set(previous["stale_outreach"]):
        c = current["stale_outreach"][contact_id]
        message = f"{product_name}: {c['name']} ({c['channel']}) is now overdue for a follow-up."
        notifier("launchmaxxing -- outreach follow-up due", message)
        log(message)
        sent.append(message)
    return sent


def run_loop(app_state_loader: Callable[[], dict[str, Any]], conn_factory: Callable[[], Any], product_name: str,
            *, interval_s: int = DEFAULT_INTERVAL_S, category: str | None = None,
            stale_days: int = track.DEFAULT_STALE_DAYS, max_cycles: int | None = None,
            sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = print) -> int:
    """Poll forever (or exactly ``max_cycles`` times, for a bounded one-shot run) every
    ``interval_s`` seconds, notifying on anything newly detected. ``app_state_loader``/
    ``conn_factory`` are zero-argument callables re-invoked every cycle (not a snapshot captured
    once) so a directory/outreach change made by a separate ``launchmaxxing submit``/``outreach``
    invocation while this loop is running is picked up on the very next poll. Returns the number
    of cycles actually run."""
    if not NOTIFY_SUPPORTED:
        log("Native notifications need macOS (osascript) -- running anyway, logging to stdout instead.")
    previous: dict[str, Any] | None = None
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        app_state = app_state_loader()
        conn = conn_factory()
        try:
            current = check_once(app_state, conn, product_name, category=category, stale_days=stale_days)
        finally:
            conn.close()
        diff_and_notify(previous, current, product_name=product_name, log=log)
        previous = current
        cycles += 1
        if max_cycles is None or cycles < max_cycles:
            sleep(interval_s)
    return cycles


__all__ = [
    "DEFAULT_INTERVAL_S", "NOTIFY_SUPPORTED", "check_once", "diff_and_notify", "notify", "run_loop",
]
