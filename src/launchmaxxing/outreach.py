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

from launchmaxxing.content import ProductProfile
from launchmaxxing.db import OUTREACH_CHANNELS


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


__all__ = ["draft_message"]
