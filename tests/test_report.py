from __future__ import annotations

from launchmaxxing import report


def _dashboard(**overrides: object) -> dict:
    base = {
        "product_name": "Acme",
        "created_at": "2026-10-01T00:00:00+00:00",
        "age_days": 17,
        "directories": {"total": 24, "submitted_or_live": 3, "not_started": 21,
                        "stale": [{"id": "betalist", "name": "BetaList", "url": "https://betalist.com/submit"}]},
        "checklist": {"done": 2, "total": 10},
        "outreach": {"total": 2, "by_status": {"contacted": 1, "replied": 1},
                    "stale_followups": [{"id": "abc", "name": "Jane", "channel": "creator"}]},
        "content_drafts": 3,
        "utm_links": 1,
        "stale_days": 5,
    }
    base.update(overrides)
    return base


def test_render_markdown_includes_product_name_and_sections() -> None:
    markdown = report.render_markdown(_dashboard())
    assert "# Launch report: Acme" in markdown
    assert "## Directories" in markdown
    assert "## Checklist" in markdown
    assert "## Outreach" in markdown
    assert "## Content drafted" in markdown
    assert "## UTM links generated" in markdown


def test_render_markdown_lists_stale_directories() -> None:
    markdown = report.render_markdown(_dashboard())
    assert "BetaList" in markdown
    assert "overdue" in markdown.lower()


def test_render_markdown_lists_stale_outreach_followups() -> None:
    markdown = report.render_markdown(_dashboard())
    assert "Jane" in markdown
    assert "awaiting follow-up" in markdown.lower()


def test_render_markdown_handles_no_outreach_contacts() -> None:
    dashboard = _dashboard(outreach={"total": 0, "by_status": {}, "stale_followups": []})
    markdown = report.render_markdown(dashboard)
    assert "No contacts tracked yet" in markdown


def test_render_markdown_omits_age_line_when_none() -> None:
    dashboard = _dashboard(age_days=None)
    markdown = report.render_markdown(dashboard)
    assert "Launch tracking started" not in markdown


def test_render_markdown_mentions_local_only_in_footer() -> None:
    markdown = report.render_markdown(_dashboard())
    assert "no data leaves your machine" in markdown.lower()
