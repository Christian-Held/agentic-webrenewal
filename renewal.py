"""Command line entrypoint for running the WebRenewal pipeline."""

from __future__ import annotations

import argparse
import logging

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
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    run_pipeline(
        args.domain,
        log_level=log_level,
        css_framework=args.css_framework,
    )


if __name__ == "__main__":
    main()
