"""Command line entrypoint for running the WebRenewal pipeline."""

from __future__ import annotations

import argparse
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
    config = RenewalConfig(
        domain=args.domain,
        renewal_mode=args.renewal_mode,
        css_framework=args.css_framework,
        theme_style=args.theme_style,
        llm_provider=args.llm,
        llm_model=args.llm_model,
        log_level=args.log_level,
    )
    run_pipeline(config)


if __name__ == "__main__":
    main()
