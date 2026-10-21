"""Deterministic, local, template-based launch-copy generator.

Every real "first 100 users" guide says the same thing: Product Hunt wants a
<=60-character benefit-first tagline, Show HN wants a plain, hype-free
"Show HN: Name - what it is" title under 80 characters (its moderators
silently rewrite anything that reads like marketing), and a Reddit pain-point
reply needs to lead with the problem, not the pitch. Getting each platform's
voice and limits right by hand, every time, is exactly the kind of tedious
checklist work this tool exists to remove.

This module generates that copy from a small, locally-supplied
:class:`ProductProfile` -- no LLM call, no API key, no network request. It is
pure text templating: same input always produces the same output, works
fully offline, and never spends anyone's AI credits. (If someone wants an
LLM to riff on these drafts further, that is a choice they make themselves,
outside this tool -- these are the hype-free, platform-correct first drafts
to start from.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

PRODUCT_HUNT_TAGLINE_MAX = 60
PRODUCT_HUNT_DESCRIPTION_MAX = 260
SHOW_HN_TITLE_MAX = 80
#: X/Twitter's real per-post character limit. Every tweet in the generated launch thread is
#: truncated to this so the thread this tool generates can actually be posted as-is, instead of
#: silently overflowing for any profile with a longer-than-average problem/audience/differentiator.
TWITTER_TWEET_MAX = 280

#: Words real Show HN / Product Hunt guides call out as the tone that gets a post buried or
#: silently rewritten by moderators. Stripped from generated titles; flagged (not auto-fixed, so
#: the human stays in control) in the tagline if present.
HYPE_WORDS = (
    "revolutionary", "game-changing", "game changer", "best-in-class", "ultimate", "insane",
    "incredible", "amazing", "groundbreaking", "disruptive", "world-class", "cutting-edge",
    "next-generation", "unparalleled", "unbelievable",
)


@dataclass(frozen=True)
class ProductProfile:
    """The minimum a human has to supply, once, to generate copy for every platform. Nothing here
    is fetched or guessed -- you know your own product and audience better than a template does."""
    name: str
    tagline: str
    problem: str
    audience: str
    differentiator: str
    url: str = ""
    pricing: str = ""
    subreddit: str = ""
    hype_flags: tuple[str, ...] = field(default_factory=tuple, compare=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name is required")
        if not self.tagline.strip():
            raise ValueError("tagline is required")
        if not self.problem.strip():
            raise ValueError("problem is required")
        if not self.audience.strip():
            raise ValueError("audience is required")
        if not self.differentiator.strip():
            raise ValueError("differentiator is required")


def _collapse(text: str) -> str:
    return " ".join(text.split()).strip()


def _truncate(text: str, limit: int) -> str:
    """Truncate ``clean`` to ``limit`` chars (including the trailing "…"), preferring to cut on a
    word boundary so generated copy never chops a word in half (e.g. "server" -> "se…") -- this
    text is meant to be pasted directly onto a launch directory, not post-edited. Falls back to a
    hard character cut when there is no space to break on (e.g. a single long URL/slug) or when
    breaking on the last space would throw away most of the available budget."""
    clean = _collapse(text)
    if len(clean) <= limit:
        return clean
    budget = max(0, limit - 1)
    window = clean[:budget]
    last_space = window.rfind(" ")
    # Only prefer the word boundary if it does not waste more than ~20% of the budget;
    # otherwise a hard cut uses the available space better.
    if last_space > 0 and last_space >= budget * 0.8:
        window = window[:last_space]
    return window.rstrip() + "…"


def _strip_hype(text: str) -> str:
    """Remove banned hype words along with a bordering comma/space so the surrounding sentence
    stays grammatical (e.g. "a Revolutionary, game-changing tool" -> "a tool"), not just blanked
    out in place and left with stray punctuation."""
    out = text
    for word in HYPE_WORDS:
        out = re.sub(rf"\s*,?\s*{re.escape(word)}\s*,?\s*", " ", out, flags=re.IGNORECASE)
    return _collapse(out)


def flag_hype_words(text: str) -> tuple[str, ...]:
    """Which banned hype words (if any) appear in ``text``, for a human to reconsider -- used on
    the tagline/description, which are never auto-rewritten, only flagged."""
    lowered = text.lower()
    return tuple(word for word in HYPE_WORDS if word in lowered)


def product_hunt_tagline(profile: ProductProfile) -> dict[str, object]:
    """<=60 chars, benefit-first. Truncated if needed; hype words are flagged, never silently
    removed, since the tagline is the one line a human should polish by hand."""
    tagline = _truncate(profile.tagline, PRODUCT_HUNT_TAGLINE_MAX)
    return {"text": tagline, "length": len(tagline), "limit": PRODUCT_HUNT_TAGLINE_MAX,
            "hype_words": flag_hype_words(tagline)}


def product_hunt_description(profile: ProductProfile) -> dict[str, object]:
    """Problem -> solution -> differentiator -> audience, in <=260 chars (Product Hunt's own
    guidance disagrees with itself between 260 and 500; 260 is valid under either reading)."""
    body = (f"{profile.problem} {profile.name} fixes that: {profile.differentiator}. "
            f"Built for {profile.audience}.")
    text = _truncate(body, PRODUCT_HUNT_DESCRIPTION_MAX)
    return {"text": text, "length": len(text), "limit": PRODUCT_HUNT_DESCRIPTION_MAX}


def show_hn_title(profile: ProductProfile) -> dict[str, object]:
    """"Show HN: Name - plain noun-phrase description", hype words stripped (HN moderators rewrite
    these anyway), hard-truncated at HN's real 80-character site-wide title limit."""
    clean_differentiator = _strip_hype(profile.differentiator)
    prefix = f"Show HN: {profile.name.strip()} – "
    remaining = max(10, SHOW_HN_TITLE_MAX - len(prefix))
    body = _truncate(clean_differentiator, remaining)
    title = f"{prefix}{body}"
    if len(title) > SHOW_HN_TITLE_MAX:
        title = title[: SHOW_HN_TITLE_MAX - 1].rstrip() + "…"
    return {"text": title, "length": len(title), "limit": SHOW_HN_TITLE_MAX}


def twitter_launch_thread(profile: ProductProfile) -> list[str]:
    """A 6-tweet launch thread: hook, problem, solution, differentiator, how-to-try, call-to-action.
    Real threads outperform single launch tweets because each tweet can be quote-tweeted on its
    own; this gives a human six real drafts to edit, not one generic blob."""
    link = f" {profile.url}" if profile.url else ""
    tweets = [
        f"Shipping {profile.name} today.{link}",
        f"The problem: {_collapse(profile.problem)}",
        f"{profile.audience} deal with this constantly, usually by cobbling together workarounds.",
        f"What {profile.name} does: {_collapse(profile.differentiator)}",
        (f"It's built for {_collapse(profile.audience)} specifically -- not a generic tool "
         f"we bolted a landing page onto."),
        (f"If you're one of the {_collapse(profile.audience)}, give it a look"
         f"{' at ' + profile.url if profile.url else ''}. Feedback (especially the "
         f"critical kind) is genuinely welcome."),
    ]
    # X/Twitter hard-caps every post at TWITTER_TWEET_MAX chars; a long audience/problem/
    # differentiator in the profile must not produce a tweet that would fail to post as-is.
    return [_truncate(tweet, TWITTER_TWEET_MAX) if len(tweet) > TWITTER_TWEET_MAX else tweet
            for tweet in tweets]


def reddit_post(profile: ProductProfile) -> dict[str, str]:
    """Problem-first Reddit post: r/SideProject and niche subs reward build-story posts, not bare
    links -- this leads with the problem and mentions the product once, near the end."""
    title = _truncate(f"Built a tool after getting tired of {_collapse(profile.problem).lower()}",
                       limit=300)
    body = (
        f"For a while I kept running into this: {_collapse(profile.problem)}\n\n"
        f"I'm part of {_collapse(profile.audience)}, so I ended up building {profile.name} to fix "
        f"it for myself first. {_collapse(profile.differentiator)}\n\n"
        + (f"It's up at {profile.url} if you want to poke at it" if profile.url else "Happy to "
           "share more about how it works")
        + " -- genuinely interested in whether this is a problem other people here have too, or "
          "if I'm the only one who found it this annoying."
    )
    return {"title": title, "body": body, "subreddit": profile.subreddit}


def linkedin_post(profile: ProductProfile) -> str:
    """Build-in-public style post: motivation, what shipped, who it is for, soft CTA -- no hard
    sell, matching what actually performs on LinkedIn for small-team/founder audiences."""
    link = f"\n\n{profile.url}" if profile.url else ""
    return (
        f"Shipped {profile.name}.\n\n"
        f"The problem: {_collapse(profile.problem)}\n\n"
        f"{_collapse(profile.differentiator)}\n\n"
        f"Built for {_collapse(profile.audience)}. If that's you, I'd genuinely like your "
        f"feedback -- the good and the bad.{link}"
    )


def generate_all(profile: ProductProfile) -> dict[str, object]:
    """Every platform's copy in one call -- what ``launchmaxxing content --platform all`` and the
    one-page launch report both use."""
    return {
        "product_hunt": {"tagline": product_hunt_tagline(profile), "description": product_hunt_description(profile)},
        "show_hn": show_hn_title(profile),
        "twitter": twitter_launch_thread(profile),
        "reddit": reddit_post(profile),
        "linkedin": linkedin_post(profile),
    }


__all__ = [
    "HYPE_WORDS", "PRODUCT_HUNT_DESCRIPTION_MAX", "PRODUCT_HUNT_TAGLINE_MAX", "SHOW_HN_TITLE_MAX",
    "TWITTER_TWEET_MAX", "ProductProfile", "flag_hype_words", "generate_all", "linkedin_post",
    "product_hunt_description", "product_hunt_tagline", "reddit_post", "show_hn_title",
    "twitter_launch_thread",
]
