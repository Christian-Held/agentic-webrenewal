"""Command line entrypoint for running the WebRenewal pipeline."""

from __future__ import annotations

import argparse
import logging
import os

from dotenv import load_dotenv
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
        "--css-framework",
        default="vanilla",
        choices=["bootstrap", "tailwind", "vanilla"],
        help="Select the CSS framework used for generated templates.",
    )
    parser.add_argument(
        "--llm",
        default=os.getenv("LLM_PROVIDER", "openai"),
        choices=["openai", "ollama", "anthropic"],
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
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    run_pipeline(
        args.domain,
        log_level=log_level,
        css_framework=args.css_framework,
        llm_provider=args.llm,
        llm_model=args.llm_model,
    )


if __name__ == "__main__":
    main()
