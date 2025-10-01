from __future__ import annotations

from webrenewal.agents.navigation_builder import NavigationBuilderAgent
from webrenewal.models import NavModel, NavigationItem, ThemeTokens


def _nav_model() -> NavModel:
    return NavModel(
        items=[
            NavigationItem(label="Home", href="/"),
            NavigationItem(
                label="Services",
                href="/services",
                children=[NavigationItem(label="Therapy", href="/services/therapy")],
            ),
        ]
    )


def test_navigation_builder_renders_bootstrap_horizontal(sample_theme_tokens: ThemeTokens) -> None:
    agent = NavigationBuilderAgent(
        css_framework="bootstrap",
        navigation_config={
            "location": "top-right",
            "style": "horizontal",
            "dropdown": "hover",
        },
    )

    bundle = agent.run((_nav_model(), sample_theme_tokens, {"brand_label": "Example"}))

    assert bundle.location == "top-right"
    assert bundle.style == "horizontal"
    assert "navbar" in bundle.html
    assert "Skip to main content" in bundle.html
    assert bundle.css
    assert "wr-nav-container" in bundle.css


def test_navigation_builder_dropdown_default_open(sample_theme_tokens: ThemeTokens) -> None:
    agent = NavigationBuilderAgent(css_framework="bootstrap", navigation_config={"dropdown_default": "open"})

    bundle = agent.run((_nav_model(), sample_theme_tokens, {}))

    assert "collapse navbar-collapse show" in bundle.html


def test_navigation_builder_tailwind_outputs_toggle(sample_theme_tokens: ThemeTokens) -> None:
    agent = NavigationBuilderAgent(
        css_framework="tailwind",
        navigation_config={"location": "top-center", "dropdown": "click"},
    )

    bundle = agent.run((_nav_model(), sample_theme_tokens, {"brand_label": "Tailwind"}))

    assert "tw-nav-toggle" in bundle.html
    assert bundle.location == "top-center"
    assert "hidden" in bundle.html  # mobile menu hidden by default
    assert "toggle" in bundle.js.lower()


def test_navigation_builder_supports_overrides(sample_theme_tokens: ThemeTokens) -> None:
    agent = NavigationBuilderAgent(
        css_framework="vanilla",
        navigation_config={"style": "vertical", "location": "side-left"},
    )

    bundle = agent.run((_nav_model(), sample_theme_tokens, {"style": "mega-menu"}))

    # override ensures final style is mega-menu even on vanilla renderer
    assert bundle.style == "mega-menu"
    assert "wr-vanilla-nav" in bundle.html
