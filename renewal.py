"""Command line entrypoint for running the WebRenewal pipeline."""

from __future__ import annotations

import argparse
import logging

from webrenewal.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Agentic WebRenewal pipeline")
    parser.add_argument("domain", help="Domain or URL to process, e.g. https://www.physioheld.ch")
    parser.add_argument("--log-level", default="INFO", help="Python logging level (default: INFO)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    run_pipeline(args.domain, log_level=log_level)


if __name__ == "__main__":
    main()
