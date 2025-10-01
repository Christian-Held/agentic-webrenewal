"""Command line entrypoint for running the WebRenewal pipeline."""

from __future__ import annotations

import argparse
import logging
from typing import Dict, Tuple

from dotenv import load_dotenv

from webrenewal.pipeline import PipelineOptions, run_pipeline


def _parse_goal_override(value: str) -> Tuple[str, float]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            f"Invalid goal override '{value}'. Expected format name=value."
        )
    name, raw = value.split("=", 1)
    name = name.strip().lower()
    try:
        parsed = float(raw)
    except ValueError as exc:  # pragma: no cover - defensive
        raise argparse.ArgumentTypeError(
            f"Invalid goal value for '{name}': {raw}"
        ) from exc
    return name, parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Agentic WebRenewal pipeline")
    parser.add_argument("domain", help="Domain or URL to process.")
    parser.add_argument("--log-level", default="INFO", help="Python logging level (default: INFO)")
    parser.add_argument("--llm-model", help="Override the model used by the rewrite agent.")
    parser.add_argument(
        "--llm-base-url",
        help="Custom base URL for the OpenAI-compatible API (e.g. Ollama).",
    )
    parser.add_argument(
        "--llm-api-key",
        help="API key for the LLM provider. Overrides OPENAI_API_KEY when provided.",
    )
    parser.add_argument(
        "--llm-temperature",
        type=float,
        help="Sampling temperature for rewrite requests.",
    )
    parser.add_argument(
        "--llm-parallel",
        type=int,
        help="Maximum number of concurrent rewrite requests.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Limit the crawler to a specific number of pages (default: 10).",
    )
    parser.add_argument(
        "--goal",
        dest="goal_overrides",
        action="append",
        type=_parse_goal_override,
        default=[],
        metavar="NAME=VALUE",
        help=(
            "Override renewal goal thresholds (e.g. --goal accessibility=97 --goal seo=92)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    goal_overrides: Dict[str, float] = {name: value for name, value in args.goal_overrides}

    options = PipelineOptions()
    if args.llm_model:
        options.llm.model = args.llm_model
    if args.llm_base_url:
        options.llm.base_url = args.llm_base_url
    if args.llm_api_key:
        options.llm.api_key = args.llm_api_key
    if args.llm_temperature is not None:
        options.llm.temperature = args.llm_temperature
    if args.llm_parallel is not None:
        options.llm.max_parallel_requests = max(1, args.llm_parallel)
    if args.max_pages is not None:
        options.max_pages = max(1, args.max_pages)

    targets = options.plan_targets
    if "accessibility" in goal_overrides:
        targets.accessibility = goal_overrides["accessibility"]
    if "seo" in goal_overrides:
        targets.seo = goal_overrides["seo"]
    if "security" in goal_overrides:
        targets.security = goal_overrides["security"]

    run_pipeline(args.domain, log_level=log_level, options=options)


if __name__ == "__main__":
    main()
