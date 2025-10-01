from webrenewal.agents.head import HeadAgent
from webrenewal.postedit.models import ChangeOperation, SiteState


def test_head_agent_apply_post_edit_updates_state() -> None:
    state = SiteState()
    state.head["title"] = "Physio Held"
    state.head["brand"] = "Physio Held"

    agent = HeadAgent()
    ops = [
        ChangeOperation(
            type="head.patch",
            payload={
                "title_policy": "brand_first",
                "favicon": "/static/favicon.ico",
                "meta": {"theme-color": "#0050b3"},
                "links": [{"rel": "preconnect", "href": "https://fonts.googleapis.com"}],
            },
        )
    ]

    summary = agent.apply_post_edit(state, ops)

    assert summary["patched"] == 1
    assert summary["title_updates"] == 1
    assert any(link.get("rel") == "icon" for link in state.head.get("links", []))
    assert any(link.get("rel") == "preconnect" for link in state.head.get("links", []))
    assert state.head.get("meta", {}).get("theme-color") == "#0050b3"
