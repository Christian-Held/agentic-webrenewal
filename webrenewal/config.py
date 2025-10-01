"""Configuration helpers for the WebRenewal pipeline."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

_LOGGER = logging.getLogger(__name__)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "configs" / "pipeline.json"


@dataclass(slots=True)
class PipelineConfig:
    """User-provided configuration for the renewal pipeline."""

    design_directives: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> "PipelineConfig":
        """Load configuration from disk and environment overrides."""

        config_path = path or _DEFAULT_CONFIG_PATH
        data: Dict[str, Any] = {}

        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                _LOGGER.warning(
                    "Unable to decode pipeline config at %s: %s", config_path, exc
                )

        env_directives = os.environ.get("WEBRENEWAL_DESIGN_DIRECTIVES")
        if env_directives is not None:
            data["design_directives"] = env_directives

        filtered: Dict[str, Any] = {
            "design_directives": data.get("design_directives"),
        }

        return cls(**filtered)


def load_pipeline_config(path: Path | None = None) -> PipelineConfig:
    """Helper to load the pipeline configuration."""

    return PipelineConfig.load(path)


__all__ = ["PipelineConfig", "load_pipeline_config"]
