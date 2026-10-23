"""Cold-outreach message templates for playbook steps 2 and 4 (``cold_outreach``,
``ugc_creators``) and the ``icp_communities`` step -- the actual words to send, not just a
reminder that outreach is step 2. Pairs with :mod:`launchmaxxing.db`'s ``outreach_contacts`` table,
which is the local, no-CRM-signup pipeline tracker for who you have contacted and whether they
replied.

Nothing here sends anything: :mod:`launchmaxxing.cli`'s ``outreach`` command only ever drafts a
message and/or records a contact's status in the local database. Every actual email/DM/reply is
sent by a human, same philosophy as :mod:`launchmaxxing.reddit_search`.
"""

from __future__ import annotations

import csv
import os
import smtplib
from collections.abc import Sequence
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from launchmaxxing.content import ProductProfile
from launchmaxxing.db import OUTREACH_CHANNELS

#: Column order for CSV export, matching the ``outreach_contacts`` row shape returned by
#: :func:`launchmaxxing.db.list_outreach_contacts`.
CSV_FIELDS = ("id", "product_name", "name", "channel", "handle", "status", "note", "created_at", "updated_at")

#: Environment variables ``outreach send`` reads SMTP credentials from -- the user's own mail
#: provider (Gmail/Fastmail/their own domain, most support an app-specific password), never a
#: third-party email-sending account/API and never a cost beyond what the user's mail provider
#: already charges them (commonly $0 for an existing personal/work inbox).
SMTP_HOST_ENV = "LAUNCHMAXXING_SMTP_HOST"
SMTP_PORT_ENV = "LAUNCHMAXXING_SMTP_PORT"
SMTP_USER_ENV = "LAUNCHMAXXING_SMTP_USER"
SMTP_PASSWORD_ENV = "LAUNCHMAXXING_SMTP_PASSWORD"
SMTP_FROM_ENV = "LAUNCHMAXXING_SMTP_FROM"
#: Set to "1"/"true"/"yes" to connect via implicit TLS (``SMTP_SSL``, typically port 465) instead
#: of the default plaintext-then-``STARTTLS`` upgrade (typically port 587).
SMTP_USE_SSL_ENV = "LAUNCHMAXXING_SMTP_USE_SSL"
DEFAULT_SMTP_PORT = 587
SMTP_TIMEOUT_S = 20.0

SMTP_SETUP_STEP = (
    f"Sending a cold-outreach email needs your own SMTP credentials -- zero third-party account, "
    f"zero extra cost beyond whatever email provider you already use. Set {SMTP_HOST_ENV}, "
    f"{SMTP_USER_ENV} and {SMTP_PASSWORD_ENV} (optionally {SMTP_PORT_ENV}, default "
    f"{DEFAULT_SMTP_PORT}, and {SMTP_FROM_ENV}, default = the SMTP user). Gmail, Fastmail, and "
    "most other providers support an app-specific password for exactly this."
)


class OutreachSendError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def smtp_configured(env: dict[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return all(str(source.get(key) or "").strip() for key in (SMTP_HOST_ENV, SMTP_USER_ENV, SMTP_PASSWORD_ENV))


def send_email(*, to_email: str, subject: str, body: str, env: dict[str, str] | None = None,
               smtp_client: Any = None) -> None:
    """Send one plain-text email via the user's own SMTP credentials (read from ``env``, or the
    real process environment when ``env`` is ``None``). Raises :class:`OutreachSendError` if SMTP
    isn't configured or the send itself fails -- never silently swallows a failed send, so a
    caller always knows whether to record ``sent`` or ``failed``.

    ``smtp_client`` is an injectable ``(host, port) -> smtplib.SMTP``-shaped factory, the same
    dependency-injection pattern :mod:`launchmaxxing.transport` uses for HTTP -- tests pass a fake
    here instead of opening a real SMTP connection; it defaults to real ``smtplib.SMTP``/
    ``SMTP_SSL``."""
    to_clean = to_email.strip()
    if not to_clean or "@" not in to_clean:
        raise OutreachSendError(f"to_email must look like an email address, got {to_email!r}")
    source = os.environ if env is None else env
    if not smtp_configured(source):
        raise OutreachSendError(SMTP_SETUP_STEP)
    host = str(source[SMTP_HOST_ENV]).strip()
    try:
        port = int(str(source.get(SMTP_PORT_ENV) or DEFAULT_SMTP_PORT))
    except ValueError as exc:
        raise OutreachSendError(f"{SMTP_PORT_ENV} must be an integer port number") from exc
    user = str(source[SMTP_USER_ENV]).strip()
    password = str(source[SMTP_PASSWORD_ENV])
    from_addr = str(source.get(SMTP_FROM_ENV) or user).strip()
    use_ssl = str(source.get(SMTP_USE_SSL_ENV) or "").strip().lower() in ("1", "true", "yes")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_addr
    message["To"] = to_clean
    message.set_content(body)

    try:
        if smtp_client is not None:
            client = smtp_client(host, port)
        elif use_ssl:
            client = smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT_S)
        else:
            client = smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_S)
        with client as server:
            if not use_ssl:
                server.starttls()
            server.login(user, password)
            server.send_message(message)
    except OutreachSendError:
        raise
    except Exception as exc:
        raise OutreachSendError(f"SMTP send failed ({type(exc).__name__}): {exc}") from exc


def draft_message(channel: str, profile: ProductProfile, *, contact_name: str = "") -> str:
    """A one-sentence-personalized-enough starting draft per outreach channel. ``contact_name`` is
    optional context (what they make/cover), not required -- founders rarely have it for a cold
    list, and the template still reads naturally without it."""
    if channel not in OUTREACH_CHANNELS:
        raise ValueError(f"channel must be one of {', '.join(OUTREACH_CHANNELS)}")
    who = contact_name.strip()
    greeting = f"Hey {who}," if who else "Hey,"
    if channel == "creator":
        return (
            f"{greeting} I built {profile.name} for {profile.audience} -- {profile.differentiator}. "
            f"Would you be up for a short video covering it? Happy to pay a flat fee plus a bonus "
            f"if it performs; no script required, your honest take is worth more than a read-aloud ad."
        )
    if channel == "press":
        return (
            f"{greeting} quick pitch: {profile.name} solves {profile.problem.rstrip('.')} for "
            f"{profile.audience}. {profile.differentiator}. Happy to send an embargoed early look, "
            f"screenshots, or get on a 10-minute call if it's relevant to anything you're covering."
        )
    if channel == "community":
        return (
            f"{greeting} long-time lurker here. I kept hitting this: {profile.problem.rstrip('.')} "
            f"-- ended up building {profile.name} to fix it ({profile.differentiator}). Figured "
            f"folks here might have hit the same wall; happy to answer questions, not here to just "
            f"drop a link."
        )
    return (  # channel == "user"
        f"{greeting} noticed you ran into {profile.problem.rstrip('.')} -- I built {profile.name} "
        f"for exactly that ({profile.differentiator}). No pressure at all, but if it's useful, "
        f"I'd love your honest feedback, good or bad."
    )


def write_contacts_csv(rows: Sequence[dict[str, Any]], path: Path | str) -> Path:
    """Write tracked outreach ``rows`` (as returned by :func:`launchmaxxing.db.list_outreach_contacts`)
    to a CSV file at ``path`` with a header row, so a founder can import contacts into Gmail
    mail-merge or a spreadsheet. Returns the resolved :class:`~pathlib.Path` written to."""
    out_path = Path(path)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_FIELDS})
    return out_path


__all__ = [
    "CSV_FIELDS", "DEFAULT_SMTP_PORT", "SMTP_FROM_ENV", "SMTP_HOST_ENV", "SMTP_PASSWORD_ENV",
    "SMTP_PORT_ENV", "SMTP_SETUP_STEP", "SMTP_USER_ENV", "SMTP_USE_SSL_ENV", "OutreachSendError",
    "draft_message", "send_email", "smtp_configured", "write_contacts_csv",
]
