"""Prompt construction helpers for the rewrite agent."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from ...models import ContentExtract, RenewalPlan, RenewalAction
from ...utils import domain_to_display_name


def build_action_summaries(actions: Iterable[RenewalAction]) -> List[dict[str, Any]]:
    return [
        {
            "id": action.identifier,
            "description": action.description,
            "impact": action.impact,
            "effort_hours": action.effort_hours,
        }
        for action in actions
    ]


def build_guidelines(domain: str, plan: RenewalPlan) -> str:
    site_label = domain_to_display_name(domain)
    goals = ", ".join(plan.goals) if plan.goals else "general improvements"
    return (
        "You are an expert marketing copywriter refreshing the website for "
        f"{site_label} ({domain}). Blend the renewal goals and action plan into "
        "persuasive, accessible copy while keeping the original language. Highlight "
        "user benefits, improve clarity, and retain any medical or legal disclaimers. "
        f"Align the tone with the goals: {goals}. Keep HTML safe (no Markdown)."
    )


def build_section_payload(
    domain: str,
    content: ContentExtract,
    section_index: int,
    plan: RenewalPlan,
    action_summaries: List[dict[str, Any]],
) -> dict[str, Any]:
    section = content.sections[section_index]
    return {
        "domain": domain,
        "site_name": domain_to_display_name(domain),
        "language": content.language or "auto",
        "goals": plan.goals,
        "actions": action_summaries,
        "section": {
            "title": section.title,
            "text": section.text,
            "readability_score": section.readability_score,
            "index": section_index + 1,
            "total": len(content.sections),
        },
    }


def build_user_instruction(
    payload: dict[str, Any],
    section_index: int,
    total_sections: int,
    include_meta: bool,
) -> str:
    meta_clause = (
        "Include 'meta_title' and 'meta_description' fields only if this is the first section. "
        if include_meta
        else "Set 'meta_title' and 'meta_description' to null for this section. "
    )
    return (
        "Return JSON with keys 'meta_title', 'meta_description' and 'blocks'. Provide exactly one "
        "entry in 'blocks' with 'title' and 'body'. "
        f"This is section {section_index + 1} of {total_sections}. "
        + meta_clause
        + "Here is the source data: "
        + json.dumps(payload, ensure_ascii=False)
    )


def build_request(
    model: str,
    temperature: float,
    guidelines: str,
    instruction: str,
) -> Dict[str, Any]:
    return {
        "model": model,
        "temperature": temperature,
        "input": [
            {"role": "system", "content": guidelines},
            {"role": "user", "content": instruction},
        ],
    }


__all__ = [
    "build_action_summaries",
    "build_guidelines",
    "build_request",
    "build_section_payload",
    "build_user_instruction",
]
