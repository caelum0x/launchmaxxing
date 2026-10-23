from __future__ import annotations

import csv
from pathlib import Path

import pytest

from launchmaxxing import utm


def test_defaults_for_known_platform() -> None:
    defaults = utm.defaults_for_platform("product_hunt")
    assert defaults == {"source": "producthunt", "medium": "launch_directory"}


def test_defaults_for_unknown_platform_falls_back() -> None:
    defaults = utm.defaults_for_platform("totally-unknown")
    assert defaults["source"] == "totally-unknown"
    assert defaults["medium"] == "referral"


def test_defaults_resolve_for_every_catalog_platform_id() -> None:
    """Every catalog platform gets a usable (non-empty source/medium) UTM default -- either from
    the curated :data:`utm.PLATFORM_UTM_DEFAULTS` table (only practical to hand-curate for a
    subset of the catalog) or :func:`utm.defaults_for_platform`'s id-derived fallback for
    everything else, so growing the catalog never leaves a platform with no usable default."""
    from launchmaxxing import catalog

    for platform in catalog.PLATFORMS:
        defaults = utm.defaults_for_platform(platform["id"])
        assert defaults["source"]
        assert defaults["medium"]


def test_build_url_adds_utm_params() -> None:
    url = utm.build_url("https://acme.example", source="producthunt", medium="launch_directory",
                        campaign="acme-launch")
    assert "utm_source=producthunt" in url
    assert "utm_medium=launch_directory" in url
    assert "utm_campaign=acme-launch" in url


def test_build_url_adds_scheme_when_missing() -> None:
    url = utm.build_url("acme.example", source="s", medium="m", campaign="c")
    assert url.startswith("https://acme.example")


def test_build_url_preserves_existing_non_utm_params() -> None:
    url = utm.build_url("https://acme.example/page?ref=abc", source="s", medium="m", campaign="c")
    assert "ref=abc" in url


def test_build_url_overwrites_existing_utm_params_idempotently() -> None:
    first = utm.build_url("https://acme.example", source="old", medium="old", campaign="old")
    second = utm.build_url(first, source="new", medium="new", campaign="new")
    assert "utm_source=new" in second
    assert "utm_source=old" not in second
    assert second.count("utm_source") == 1


def test_build_url_includes_optional_content_param() -> None:
    url = utm.build_url("https://acme.example", source="s", medium="m", campaign="c", content="thread-1")
    assert "utm_content=thread-1" in url


def test_build_url_rejects_empty_base_url() -> None:
    with pytest.raises(ValueError):
        utm.build_url("", source="s", medium="m", campaign="c")


def _link_row(**overrides: str) -> dict[str, str]:
    row = {"id": "l1", "product_name": "Acme", "platform_id": "product_hunt", "base_url": "https://acme.example",
           "source": "producthunt", "medium": "launch_directory", "campaign": "acme-launch", "content": "",
           "full_url": "https://acme.example?utm_source=producthunt&utm_medium=launch_directory"
                       "&utm_campaign=acme-launch",
           "created_at": "2026-10-01T00:00:00+00:00"}
    row.update(overrides)
    return row


def test_write_links_csv_writes_header_and_rows(tmp_path: Path) -> None:
    out_path = tmp_path / "links.csv"
    rows = [_link_row(), _link_row(id="l2", platform_id="betalist", source="betalist")]

    result = utm.write_links_csv(rows, out_path)

    assert result == out_path
    assert out_path.is_file()
    with out_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        data_rows = list(reader)
    assert header == list(utm.CSV_FIELDS)
    assert len(data_rows) == 2
    expected_full_url = ("https://acme.example?utm_source=producthunt&utm_medium=launch_directory"
                         "&utm_campaign=acme-launch")
    assert data_rows[0] == ["l1", "Acme", "product_hunt", "https://acme.example", "producthunt",
                            "launch_directory", "acme-launch", "", expected_full_url,
                            "2026-10-01T00:00:00+00:00"]
    assert data_rows[1][0:3] == ["l2", "Acme", "betalist"]


def test_write_links_csv_handles_empty_rows(tmp_path: Path) -> None:
    out_path = tmp_path / "empty.csv"

    utm.write_links_csv([], out_path)

    with out_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows == [list(utm.CSV_FIELDS)]


def test_write_links_csv_accepts_str_path(tmp_path: Path) -> None:
    out_path = tmp_path / "links.csv"

    result = utm.write_links_csv([_link_row()], str(out_path))

    assert result == out_path
    assert out_path.is_file()
