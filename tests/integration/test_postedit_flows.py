from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from webrenewal.models import RenewalConfig
from webrenewal.pipeline import run_pipeline
from webrenewal.postedit.models import SiteBlock, SitePage, SiteState
from webrenewal.state import StateStore


def _seed_state(store: StateStore) -> SiteState:
    state = SiteState()
    state.pages = [
        SitePage(path="/", url="/", title="Home", blocks=[SiteBlock(id="hero", text="Welcome to PhysioHeld")]),
        SitePage(path="/services", url="/services", title="Services", blocks=[SiteBlock(id="svc", text="We help you recover")]),
    ]
    state.nav["items"] = [
        {"label": "Home", "href": "index.html"},
        {"label": "Services", "href": "services.html"},
    ]
    store.save_site_state(state)
    return state


@pytest.fixture
def state_store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.db")


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_css_scope_changes_only_css(sandbox_dir: Path, state_store: StateStore) -> None:
    _seed_state(state_store)
    config = RenewalConfig(
        domain="https://www.physioheld.ch",
        css_framework="bootstrap",
        llm_provider="openai",
        user_prompt="Make it modern; blue/white palette; rounded buttons with shadow",
        apply_scope=["css"],
        no_recrawl=True,
    )
    result = run_pipeline(config, state_store=state_store)

    updated_state = state_store.load_site_state()
    assert "blue" in json_fragment(updated_state.css_bundle["tokens"])

    build_dir = Path(result["build"]["output_dir"])
    assert build_dir.exists()
    pages = sorted(build_dir.glob("*.html"))
    hashes = {_hash_file(page) for page in pages}

    # Running again with the same scope should not create additional edit entries
    run_pipeline(config, state_store=state_store)
    assert len(state_store.list_edits()) == 1
    remaining_hashes = {_hash_file(page) for page in build_dir.glob("*.html")}
    assert hashes == remaining_hashes


def test_content_scope_updates_blocks(sandbox_dir: Path, state_store: StateStore) -> None:
    _seed_state(state_store)
    config = RenewalConfig(
        domain="https://www.physioheld.ch",
        css_framework="bootstrap",
        llm_provider="openai",
        user_prompt="Make all service descriptions 30% longer and add a call-to-action at the end",
        apply_scope=["content"],
        no_recrawl=True,
    )
    result = run_pipeline(config, state_store=state_store)

    updated_state = state_store.load_site_state()
    assert "call_to_action" in updated_state.pages[1].blocks[0].meta
    build_dir = Path(result["build"]["output_dir"])
    html_files = list(build_dir.glob("*.html"))
    assert any("call-to-action" in path.read_text(encoding="utf-8") for path in html_files)


def test_navigation_scope_moves_navigation(sandbox_dir: Path, state_store: StateStore) -> None:
    _seed_state(state_store)
    config = RenewalConfig(
        domain="https://www.physioheld.ch",
        css_framework="bootstrap",
        llm_provider="openai",
        user_prompt="navigation top-right with hover dropdowns closed by default",
        apply_scope=["nav"],
        no_recrawl=True,
    )
    run_pipeline(config, state_store=state_store)

    updated_state = state_store.load_site_state()
    assert updated_state.nav["layout"]["location"] == "top-right"
    assert "nav-top-right" in updated_state.nav["html"]


def json_fragment(value) -> str:
    import json

    return json.dumps(value, sort_keys=True)
