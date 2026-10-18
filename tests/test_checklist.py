from __future__ import annotations

from launchmaxxing import checklist, state


def test_build_requires_product_name() -> None:
    import pytest

    with pytest.raises(ValueError):
        checklist.build({"products": {}, "pain_point_drafts": []}, "  ")


def test_build_all_pending_for_new_product() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    result = checklist.build(app_state, "Acme")
    assert result["done"] == 0
    assert result["total"] == 10
    assert all(s["status"] == "pending" for s in result["steps"])
    assert result["platforms_submitted"] == []


def test_build_derives_launch_everywhere_from_platforms() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="submitted")
    result = checklist.build(app_state, "Acme")
    launch_step = next(s for s in result["steps"] if s["key"] == "launch_everywhere")
    assert launch_step["status"] == "done"
    assert result["done"] == 1
    assert result["platforms_submitted"] == ["product_hunt"]


def test_build_explicit_step_status_overrides_derived() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_platform_status(app_state, product_name="Acme", platform_id="product_hunt", status="submitted")
    state.set_step_status(app_state, product_name="Acme", step_key="launch_everywhere", status="pending",
                           note="not really launched yet")
    result = checklist.build(app_state, "Acme")
    launch_step = next(s for s in result["steps"] if s["key"] == "launch_everywhere")
    assert launch_step["status"] == "pending"
    assert launch_step["note"] == "not really launched yet"


def test_build_marks_non_launch_step_done() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_step_status(app_state, product_name="Acme", step_key="cold_outreach", status="done")
    result = checklist.build(app_state, "Acme")
    assert result["done"] == 1
    step = next(s for s in result["steps"] if s["key"] == "cold_outreach")
    assert step["status"] == "done"


def test_build_is_scoped_per_product() -> None:
    app_state = {"products": {}, "pain_point_drafts": []}
    state.set_step_status(app_state, product_name="Acme", step_key="cold_outreach", status="done")
    other = checklist.build(app_state, "Other")
    assert other["done"] == 0
