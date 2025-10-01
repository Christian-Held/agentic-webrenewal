from __future__ import annotations

from pathlib import Path

import pytest

from webrenewal.models import RenewalConfig
from webrenewal.pipeline import PostEditPipeline
from webrenewal.postedit.models import SiteBlock, SitePage, SiteState
from webrenewal.state import StateStore


def _seed_state(store: StateStore) -> None:
    state = SiteState()
    home = SitePage(path="/", url="/", title="Home", blocks=[SiteBlock(id="hero", text="Hello world")])
    services = SitePage(
        path="/services",
        url="/services",
        title="Services",
        blocks=[SiteBlock(id="services", text="We offer physiotherapy.")],
    )
    state.pages = [home, services]
    state.nav["items"] = [
        {"label": "Home", "href": "index.html"},
        {"label": "Services", "href": "services.html"},
    ]
    store.save_site_state(state)


@pytest.fixture
def state_store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.db")


def test_postedit_pipeline_updates_css_only(monkeypatch: pytest.MonkeyPatch, sandbox_dir: Path, state_store: StateStore) -> None:
    _seed_state(state_store)
    config = RenewalConfig(
        domain="https://example.com",
        css_framework="bootstrap",
        theme_style="",
        llm_provider="openai",
        llm_model=None,
        log_level="INFO",
        user_prompt="modern blue white rounded buttons shadow",
        apply_scope=["css"],
        no_recrawl=True,
    )
    pipeline = PostEditPipeline(config, state_store=state_store)
    result = pipeline.execute()

    updated_state = state_store.load_site_state()
    assert "style intent" in updated_state.css_bundle.get("raw", "")
    # Content should remain unchanged for CSS-only run
    assert updated_state.pages[0].blocks[0].text == "Hello world"
    assert Path(result["build"]["output_dir"]).exists()


def test_postedit_pipeline_is_idempotent(monkeypatch: pytest.MonkeyPatch, sandbox_dir: Path, state_store: StateStore) -> None:
    _seed_state(state_store)
    config = RenewalConfig(
        domain="https://example.com",
        css_framework="bootstrap",
        theme_style="",
        llm_provider="openai",
        llm_model=None,
        log_level="INFO",
        user_prompt="increase content length",
        apply_scope=["content"],
        no_recrawl=True,
    )

    pipeline = PostEditPipeline(config, state_store=state_store)
    first = pipeline.execute()
    second = pipeline.execute()

    assert first["change_set"] == second["change_set"]
    assert second["preview"]["id"] == state_store.latest_preview()["id"]
