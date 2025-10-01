"""Tests for :mod:`webrenewal.config`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pytest

from webrenewal.config import PipelineConfig, load_pipeline_config


def test_pipeline_config_loads_file_and_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Given a JSON config When PipelineConfig.load is invoked Then file and env overrides are merged."""

    config_payload: Dict[str, str] = {"design_directives": "Blau und modern"}
    config_path = tmp_path / "pipeline.json"
    config_path.write_text(json.dumps(config_payload), encoding="utf-8")
    monkeypatch.setenv("WEBRENEWAL_DESIGN_DIRECTIVES", "Serif friendly")

    config = PipelineConfig.load(config_path)

    assert config.design_directives == "Serif friendly"


def test_load_pipeline_config_defaults_when_missing(tmp_path: Path) -> None:
    """Given no config file When load_pipeline_config is executed Then defaults with None directives are returned."""

    missing_path = tmp_path / "missing.json"

    config = load_pipeline_config(missing_path)

    assert isinstance(config, PipelineConfig)
    assert config.design_directives is None
