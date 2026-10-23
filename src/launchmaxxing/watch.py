"""Background-poll watcher: re-runs the detection logic launchmaxxing already ships
(:func:`launchmaxxing.linkcheck.check_all`, :mod:`launchmaxxing.track`'s stale-directory and
stale-outreach reminders) on an interval and fires a native OS notification the moment something
*newly* changes, instead of requiring a human to remember to run ``directories --check-links`` or
``track`` by hand. Turns already-built detection logic into an always-on signal.

Notifications are native, with no account, no push-notification service and no server, on every
platform launchmaxxing supports:

- **macOS**: ``osascript -e 'display notification'`` (Notification Center).
- **Linux**: ``notify-send`` (the ``libnotify`` CLI most desktop distros -- GNOME, KDE, XFCE --
  already ship; a headless/server Linux box without it just doesn't have a notification daemon
  to notify, same as macOS without Notification Center).
- **Windows**: a one-shot PowerShell ``System.Windows.Forms.NotifyIcon`` balloon tip -- uses only
  the .NET Forms assembly every Windows 10/11 install already has, no extra module to install.

If none of the above is available (an unrecognized platform, or the expected native tool is
missing), ``watch`` still runs and still logs every detected change to stdout; it never crashes
for lacking a way to pop a native popup."""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from launchmaxxing import linkcheck, outreach, track
from launchmaxxing.transport import RequestsTransport

#: How often ``watch`` polls by default -- 15 minutes. Frequent enough to catch a directory
#: going dead or a contact going stale within the same working session, infrequent enough not to
#: hammer every catalog submit URL (or whichever --category subset) on a tight loop.
DEFAULT_INTERVAL_S = 900

_PLATFORM = platform.system()
#: Whether :func:`notify` can actually pop a native OS notification on this machine. On Linux this
#: also depends on ``notify-send`` being installed (most desktops have it; a bare server distro
#: usually doesn't), so this is computed once at import time rather than being a static per-OS
#: constant -- a Linux box genuinely without a notification daemon should see this as ``False``,
#: not silently try and fail every poll cycle.
NOTIFY_SUPPORTED = (
    _PLATFORM in ("Darwin", "Windows")
    or (_PLATFORM == "Linux" and shutil.which("notify-send") is not None)
)


def _osa_quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _powershell_quote(text: str) -> str:
    """Quote ``text`` as a single-quoted PowerShell string literal -- the only special case is a
    literal single quote, which PowerShell escapes by doubling it (unlike backslash-escaping in
    shells like bash or AppleScript)."""
    return "'" + text.replace("'", "''") + "'"


def _notify_macos(title: str, message: str, run: Callable[..., Any]) -> None:
    script = f"display notification {_osa_quote(message)} with title {_osa_quote(title)}"
    run(["osascript", "-e", script], check=False, capture_output=True)


def _notify_linux(title: str, message: str, run: Callable[..., Any]) -> None:
    run(["notify-send", "--app-name=launchmaxxing", title, message], check=False, capture_output=True)


def _notify_windows(title: str, message: str, run: Callable[..., Any]) -> None:
    """Pop a Windows balloon-tip notification via a throwaway PowerShell process -- no extra
    module (no BurntToast, no pywin32) required, just the ``System.Windows.Forms`` assembly every
    Windows 10/11 install already ships. The notify icon is kept alive with ``Start-Sleep`` for
    long enough for the balloon to actually render before the process (and the icon with it)
    exits; disposing it immediately would often race the balloon off-screen before a user ever
    saw it."""
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Information; "
        "$n.Visible = $true; "
        f"$n.ShowBalloonTip(8000, {_powershell_quote(title)}, {_powershell_quote(message)}, "
        "[System.Windows.Forms.ToolTipIcon]::Info); "
        "Start-Sleep -Seconds 8; "
        "$n.Dispose();"
    )
    run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], check=False, capture_output=True)


#: Dispatch table from :func:`platform.system`'s return value to the notifier that knows how to
#: talk to that OS's native notification mechanism.
_NOTIFIERS: dict[str, Callable[[str, str, Callable[..., Any]], None]] = {
    "Darwin": _notify_macos, "Linux": _notify_linux, "Windows": _notify_windows,
}


def notify(title: str, message: str, *, runner: Callable[..., Any] | None = None) -> bool:
    """Fire one native OS notification (macOS Notification Center, Linux ``notify-send``, or a
    Windows balloon tip -- see :data:`NOTIFY_SUPPORTED`). Returns ``True`` if a notification was
    actually attempted, ``False`` if this platform has no supported native mechanism available --
    callers should still log the same message to stdout either way, so ``watch`` stays useful
    everywhere even where a native popup isn't available."""
    if not NOTIFY_SUPPORTED:
        return False
    notifier = _NOTIFIERS.get(_PLATFORM)
    if notifier is None:
        return False
    run = runner or subprocess.run
    notifier(title, message, run)
    return True


def make_email_notifier(to_email: str, *, env: dict[str, str] | None = None) -> Callable[[str, str], bool]:
    """Build a notifier callable (same ``(title, message) -> bool`` shape :func:`notify` has, so
    it drops straight into :func:`diff_and_notify`/:func:`run_loop`'s ``notifier`` parameter)
    that emails ``to_email`` via the user's own SMTP credentials instead of popping a native OS
    notification -- the only delivery channel that actually reaches someone running ``watch`` on
    a headless server or a Linux box with no notification daemon (where :data:`NOTIFY_SUPPORTED`
    is ``False``), or who simply wants an email trail of every alert alongside/instead of a
    desktop popup. Never raises: a failed send (SMTP not configured, network down, bad
    credentials) is logged by the caller via the ``False`` return, not a crashed poll loop."""
    def _send(title: str, message: str) -> bool:
        try:
            outreach.send_email(to_email=to_email, subject=title, body=message, env=env)
            return True
        except outreach.OutreachSendError:
            return False
    return _send


def compose_notifiers(*notifiers: Callable[[str, str], bool]) -> Callable[[str, str], bool]:
    """Combine several notifier callables (e.g. the native :func:`notify` plus an
    :func:`make_email_notifier` email notifier) into the single callable
    :func:`diff_and_notify`/:func:`run_loop` expect, so ``watch`` can fire every configured
    channel for the same event without either of them knowing the other exists. Calls *every*
    notifier (never short-circuits on the first success), returning ``True`` if any one of them
    actually fired."""
    def _combined(title: str, message: str) -> bool:
        # Deliberately a list comprehension, not a generator -- any() short-circuits on the
        # first True, which would skip every later notifier (e.g. never actually send the email
        # once the native popup fires) if this were lazy.
        results = [n(title, message) for n in notifiers]
        return any(results)
    return _combined


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
            notifier: Callable[[str, str], bool] = notify,
            sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = print) -> int:
    """Poll forever (or exactly ``max_cycles`` times, for a bounded one-shot run) every
    ``interval_s`` seconds, notifying on anything newly detected. ``app_state_loader``/
    ``conn_factory`` are zero-argument callables re-invoked every cycle (not a snapshot captured
    once) so a directory/outreach change made by a separate ``launchmaxxing submit``/``outreach``
    invocation while this loop is running is picked up on the very next poll. ``notifier``
    defaults to the native-OS :func:`notify`; pass a :func:`make_email_notifier` (optionally
    wrapped in :func:`compose_notifiers` alongside :func:`notify`) to also/instead email every
    alert -- the practical channel on a headless box with no native notification mechanism.
    Returns the number of cycles actually run."""
    if not NOTIFY_SUPPORTED and notifier is notify:
        reason = (
            "install notify-send (most desktop Linux distros ship it via libnotify; a headless "
            "server usually doesn't have a notification daemon to notify)"
            if _PLATFORM == "Linux" else
            f"no supported native-notification mechanism is known for {_PLATFORM!r}"
        )
        log(f"No native notifications available on this machine ({reason}) -- running anyway, "
            "logging to stdout instead (pass an email notifier to still get alerted off-screen).")
    previous: dict[str, Any] | None = None
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        app_state = app_state_loader()
        conn = conn_factory()
        try:
            current = check_once(app_state, conn, product_name, category=category, stale_days=stale_days)
        finally:
            conn.close()
        diff_and_notify(previous, current, product_name=product_name, notifier=notifier, log=log)
        previous = current
        cycles += 1
        if max_cycles is None or cycles < max_cycles:
            sleep(interval_s)
    return cycles


__all__ = [
    "DEFAULT_INTERVAL_S", "NOTIFY_SUPPORTED", "check_once", "compose_notifiers", "diff_and_notify",
    "make_email_notifier", "notify", "run_loop",
]
