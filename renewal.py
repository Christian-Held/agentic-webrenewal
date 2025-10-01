"""Command line entrypoint for running the WebRenewal pipeline."""

from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from webrenewal.models import RenewalConfig
from webrenewal.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Agentic WebRenewal pipeline")
    parser.add_argument("domain", help="Domain or URL to process.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Python logging level (default: INFO)",
    )
    parser.add_argument(
        "--renewal-mode",
        default="full",
        choices=["full", "text-only", "seo-only", "design-only"],
        help="Select which parts of the pipeline should run.",
    )
    parser.add_argument(
        "--css-framework",
        default="vanilla",
        help="Name of the CSS framework or design system to target.",
    )
    parser.add_argument(
        "--navigation-style",
        default="horizontal",
        choices=["horizontal", "vertical", "mega-menu"],
        help="Navigation layout style (horizontal, vertical, mega-menu).",
    )
    parser.add_argument(
        "--navigation-location",
        default="top-left",
        choices=[
            "top-left",
            "top-right",
            "top-center",
            "side-left",
            "side-right",
            "footer",
        ],
        help="Placement of the navigation component on the page.",
    )
    parser.add_argument(
        "--navigation-dropdown",
        default="hover",
        choices=["none", "hover", "click"],
        help="Dropdown trigger behaviour (none, hover, click).",
    )
    parser.add_argument(
        "--navigation-dropdown-default",
        default="closed",
        choices=["open", "closed"],
        help="Initial dropdown state when rendering the navigation.",
    )
    parser.add_argument(
        "--navigation-config",
        default="",
        help="Advanced navigation configuration overrides encoded as JSON.",
    )
    parser.add_argument(
        "--navigation-logo",
        default=None,
        help="Optional logo URL to display alongside the brand title.",
    )
    parser.add_argument(
        "--theme-style",
        default="",
        help="Comma separated style hints (colours, shapes, effects).",
    )
    parser.add_argument(
        "--llm",
        default=os.getenv("LLM_PROVIDER", "openai"),
        choices=["openai", "ollama", "anthropic", "gemini", "deepseek", "groq"],
        help="Choose the LLM provider backend (default: env LLM_PROVIDER or openai).",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("LLM_MODEL"),
        help="Override the model identifier for the selected provider.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    advanced_config: dict[str, object] = {}
    if args.navigation_config:
        try:
            advanced_config = json.loads(args.navigation_config)
            if not isinstance(advanced_config, dict):
                raise ValueError("Navigation config JSON must decode to an object")
        except (json.JSONDecodeError, ValueError) as exc:
            raise SystemExit(f"Invalid --navigation-config payload: {exc}") from exc
    config = RenewalConfig(
        domain=args.domain,
        renewal_mode=args.renewal_mode,
        css_framework=args.css_framework,
        theme_style=args.theme_style,
        llm_provider=args.llm,
        llm_model=args.llm_model,
        log_level=args.log_level,
        navigation_style=args.navigation_style,
        navigation_location=args.navigation_location,
        navigation_dropdown=args.navigation_dropdown,
        navigation_dropdown_default=args.navigation_dropdown_default,
        navigation_config=advanced_config,
        navigation_logo=args.navigation_logo,
    )
    run_pipeline(config)


if __name__ == "__main__":
    main()
