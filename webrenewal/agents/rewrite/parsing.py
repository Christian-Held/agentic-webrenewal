"""Helpers to coerce OpenAI responses into structured rewrite payloads."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, List, Optional


def extract_response_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return direct

    parts: List[str] = []
    for item in getattr(response, "output", []) or []:
        content_items = getattr(item, "content", []) or []
        parts.extend(filter(None, map(_coerce_content_text, content_items)))

    if parts:
        return "".join(parts)

    structured = _safe_model_dump(response)
    if structured:
        candidate = _locate_rewrite_payload(structured)
        if candidate:
            return candidate

    return ""


def strip_json_fences(payload: str) -> str:
    stripped = payload.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)```", stripped, re.DOTALL)
        if match:
            stripped = match.group(1).strip()
    if stripped and not stripped.startswith("{"):
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            stripped = match.group(0).strip()
    return stripped


def parse_json_payload(raw: str) -> dict[str, Any]:
    cleaned = strip_json_fences(raw)
    if not cleaned:
        raise ValueError("Empty JSON payload returned by LLM")
    return json.loads(cleaned)


def _coerce_content_text(content_item: Any) -> Optional[str]:
    content_type = getattr(content_item, "type", None)
    if content_type in {"output_json", "json"}:
        json_payload = getattr(content_item, "json", None)
        if isinstance(json_payload, dict):
            return json.dumps(json_payload)
        if hasattr(json_payload, "model_dump"):
            try:
                dumped = json_payload.model_dump()
            except Exception:  # pragma: no cover - defensive
                dumped = None
            if isinstance(dumped, dict):
                return json.dumps(dumped)

    if content_type in {"output_text", "text", None}:
        text_obj = getattr(content_item, "text", None)
        normalised = _normalise_text_value(text_obj)
        if normalised:
            return normalised

    return None


def _normalise_text_value(text_obj: Any) -> Optional[str]:
    if text_obj is None:
        return None
    if isinstance(text_obj, str):
        return text_obj
    if hasattr(text_obj, "value"):
        value = getattr(text_obj, "value")
        if isinstance(value, str):
            return value
    if isinstance(text_obj, dict):
        value = text_obj.get("value") or text_obj.get("text")
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            pieces = [segment.get("text") for segment in value if isinstance(segment, dict)]
            return "".join(filter(None, pieces)) if pieces else None
    if isinstance(text_obj, list):
        pieces: List[str] = []
        for item in text_obj:
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                piece = item.get("text") or item.get("value")
                if isinstance(piece, str):
                    pieces.append(piece)
        return "".join(pieces) if pieces else None
    if hasattr(text_obj, "model_dump"):
        try:
            dumped = text_obj.model_dump()
        except Exception:  # pragma: no cover - defensive
            dumped = None
        if dumped is not None:
            return _normalise_text_value(dumped)
    return None


def _safe_model_dump(response: Any) -> Optional[Any]:
    for attr in ("model_dump", "to_dict", "dict"):
        method = getattr(response, attr, None)
        if callable(method):
            try:
                data = method()
            except Exception:  # pragma: no cover - defensive
                continue
            if data:
                return data
    return None


def _locate_rewrite_payload(data: Any, depth: int = 0) -> Optional[str]:
    if depth > 6:
        return None
    if isinstance(data, str):
        stripped = data.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped
        return None
    if isinstance(data, dict):
        if _looks_like_rewrite_payload(data):
            return json.dumps(data)
        for value in data.values():
            candidate = _locate_rewrite_payload(value, depth + 1)
            if candidate:
                return candidate
    if isinstance(data, list):
        for item in data:
            candidate = _locate_rewrite_payload(item, depth + 1)
            if candidate:
                return candidate
    return None


def _looks_like_rewrite_payload(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if "blocks" not in data or not isinstance(data["blocks"], list):
        return False
    return any(key in data for key in ("meta_title", "meta_description"))


__all__ = ["extract_response_text", "parse_json_payload", "strip_json_fences"]
