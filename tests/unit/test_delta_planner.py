from __future__ import annotations

from webrenewal.delta import DeltaPlanner
from webrenewal.postedit.models import SiteBlock, SitePage, SiteState


def _sample_state() -> SiteState:
    state = SiteState()
    state.pages = [
        SitePage(path="/", url="/", title="Home", blocks=[SiteBlock(id="hero", text="Welcome")]),
        SitePage(path="/services", url="/services", title="Services", blocks=[SiteBlock(id="svc", text="Massage")]),
    ]
    return state


def test_delta_planner_css_scope_only() -> None:
    state = _sample_state()
    planner = DeltaPlanner(state, ["css"], "modern blue palette rounded buttons")
    change_set = planner.plan()
    assert change_set.targets == ["css"]
    assert any(op.type == "css.tokens.update" for op in change_set.operations)
    assert all(not op.type.startswith("content") for op in change_set.operations)


def test_delta_planner_idempotent_hash() -> None:
    state = _sample_state()
    planner = DeltaPlanner(state, ["content"], "extend copy")
    first = planner.plan()
    second = planner.plan()
    assert first.hash() == second.hash()


def test_delta_planner_respects_nav_scope() -> None:
    state = _sample_state()
    planner = DeltaPlanner(state, ["nav"], "navigation top right hover dropdown")
    change_set = planner.plan()
    assert change_set.targets == ["nav"]
    assert change_set.operations[0].payload["location"] == "top-right"
