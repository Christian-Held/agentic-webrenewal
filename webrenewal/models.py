"""Data models used across the Agentic WebRenewal pipeline."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class RenewalConfig(BaseModel):
    """Central configuration shared by CLI and future API entrypoints."""

    domain: str = Field(..., description="Domain or URL to process")
    renewal_mode: str = Field(
        default="full",
        description="Strategy for renewing the target site",
    )
    css_framework: str = Field(
        default="vanilla",
        description="Preferred CSS framework or library name",
    )
    theme_style: str = Field(
        default="",
        description="Comma-separated styling directives passed to theming",
    )
    llm_provider: str = Field(
        default="openai",
        description="LLM provider identifier",
    )
    llm_model: str | None = Field(
        default=None,
        description="Specific model name for the chosen provider",
    )
    log_level: str = Field(
        default="INFO",
        description="Desired logging verbosity",
    )
    navigation_style: str = Field(
        default="horizontal",
        description="Preferred navigation layout style",
    )
    navigation_location: str = Field(
        default="top-left",
        description="Where the navigation should be positioned on the page",
    )
    navigation_dropdown: str = Field(
        default="hover",
        description="Interaction mode for dropdown menus",
    )
    navigation_dropdown_default: str = Field(
        default="closed",
        description="Initial dropdown expanded state",
    )
    navigation_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Advanced navigation configuration overrides",
    )
    navigation_logo: str | None = Field(
        default=None,
        description="Optional logo URL to display in the navigation",
    )
    user_prompt: str | None = Field(
        default=None,
        description="Free-text instructions for post-edit runs",
    )
    apply_scope: List[str] = Field(
        default_factory=lambda: ["all"],
        description="Scopes to apply during post-edit runs",
    )
    no_recrawl: bool = Field(
        default=False,
        description="Skip initial crawl when prior artifacts exist",
    )

    @field_validator("domain", mode="before")
    @classmethod
    def _ensure_domain(cls, value: str) -> str:
        if value is None:
            raise ValueError("Domain must be provided")
        text = str(value).strip()
        if not text:
            raise ValueError("Domain must be a non-empty string")
        return text

    @field_validator("renewal_mode", mode="before")
    @classmethod
    def _normalise_mode(cls, value: str | None) -> str:
        candidate = (value or "full").strip().lower()
        allowed = {"full", "text-only", "seo-only", "design-only"}
        if candidate not in allowed:
            raise ValueError(
                f"Unsupported renewal_mode '{value}'. Expected one of: {', '.join(sorted(allowed))}."
            )
        return candidate

    @field_validator("css_framework", mode="before")
    @classmethod
    def _normalise_framework(cls, value: str | None) -> str:
        return (value or "vanilla").strip()

    @field_validator("theme_style", mode="before")
    @classmethod
    def _normalise_theme(cls, value: str | None) -> str:
        return (value or "").strip()

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _normalise_provider(cls, value: str | None) -> str:
        return (value or "openai").strip()

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_log_level(cls, value: str | None) -> str:
        return (value or "INFO").strip().upper()

    @field_validator("navigation_style", mode="before")
    @classmethod
    def _normalise_navigation_style(cls, value: str | None) -> str:
        candidate = (value or "horizontal").strip().lower()
        allowed = {"horizontal", "vertical", "mega-menu"}
        if candidate not in allowed:
            raise ValueError(
                "Unsupported navigation_style '{value}'. Expected one of: horizontal, vertical, mega-menu.".format(
                    value=value
                )
            )
        return candidate

    @field_validator("navigation_location", mode="before")
    @classmethod
    def _normalise_navigation_location(cls, value: str | None) -> str:
        candidate = (value or "top-left").strip().lower()
        allowed = {
            "top-left",
            "top-right",
            "top-center",
            "side-left",
            "side-right",
            "footer",
        }
        if candidate not in allowed:
            raise ValueError(
                "Unsupported navigation_location '{value}'. Expected one of: {choices}.".format(
                    value=value,
                    choices=", ".join(sorted(allowed)),
                )
            )
        return candidate

    @field_validator("navigation_dropdown", mode="before")
    @classmethod
    def _normalise_navigation_dropdown(cls, value: str | None) -> str:
        candidate = (value or "hover").strip().lower()
        allowed = {"none", "hover", "click"}
        if candidate not in allowed:
            raise ValueError(
                "Unsupported navigation_dropdown '{value}'. Expected one of: none, hover, click.".format(
                    value=value
                )
            )
        return candidate

    @field_validator("navigation_dropdown_default", mode="before")
    @classmethod
    def _normalise_navigation_dropdown_default(cls, value: str | None) -> str:
        candidate = (value or "closed").strip().lower()
        allowed = {"open", "closed"}
        if candidate not in allowed:
            raise ValueError(
                "Unsupported navigation_dropdown_default '{value}'. Expected one of: open, closed.".format(
                    value=value
                )
            )
        return candidate

    @field_validator("apply_scope", mode="before")
    @classmethod
    def _normalise_apply_scope(cls, value: Any) -> List[str]:
        allowed = {"all", "css", "seo", "images", "logo", "content", "nav", "head"}
        if value is None:
            return ["all"]
        if isinstance(value, str):
            tokens = [token.strip().lower() for token in value.split(",") if token.strip()]
        elif isinstance(value, (list, tuple, set)):
            tokens = [str(token).strip().lower() for token in value if str(token).strip()]
        else:
            raise ValueError("apply_scope must be a comma separated string or list of scopes")
        if not tokens:
            return ["all"]
        for token in tokens:
            if token not in allowed:
                raise ValueError(
                    f"Unsupported apply_scope entry '{token}'. Expected one of: {', '.join(sorted(allowed))}."
                )
        return tokens

    def navigation_settings(self) -> Dict[str, Any]:
        """Return the resolved navigation settings merged with advanced config."""

        merged: Dict[str, Any] = {
            "style": self.navigation_style,
            "location": self.navigation_location,
            "dropdown": self.navigation_dropdown,
            "dropdown_default": self.navigation_dropdown_default,
        }
        advanced = dict(self.navigation_config or {})
        merged.update(advanced)
        if self.navigation_logo:
            merged.setdefault("logo", self.navigation_logo)
        return merged

    def style_hints(self) -> list[str]:
        """Return individual style hints derived from the theme_style field."""

        return [hint.strip() for hint in self.theme_style.split(",") if hint.strip()]


@dataclass(slots=True)
class Serializable:
    """Base dataclass providing JSON serialisation helpers."""

    def to_dict(self) -> Dict:
        """Convert the dataclass to a serialisable dictionary."""

        def _convert(value):
            if dataclasses.is_dataclass(value):
                return {f.name: _convert(getattr(value, f.name)) for f in dataclasses.fields(value)}
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, list):
                return [_convert(item) for item in value]
            if isinstance(value, dict):
                return {key: _convert(val) for key, val in value.items()}
            return value

        return _convert(self)

    def to_json(self, path: Path) -> None:
        """Write the dataclass as JSON to the provided ``path``."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


@dataclass(slots=True)
class ToolInfo(Serializable):
    name: str
    category: str
    description: str
    usage_snippet: str


@dataclass(slots=True)
class ToolCatalog(Serializable):
    tools: List[ToolInfo] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class ScopePlan(Serializable):
    domain: str
    seed_urls: List[str]
    sitemap_urls: List[str]
    robots_txt: Optional[str] = None


@dataclass(slots=True)
class PageContent(Serializable):
    url: str
    status_code: int
    headers: Dict[str, str]
    html: str
    fetched_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class CrawlResult(Serializable):
    pages: List[PageContent]


@dataclass(slots=True)
class ContentSection(Serializable):
    title: Optional[str]
    text: str
    readability_score: Optional[float] = None


@dataclass(slots=True)
class ContentExtract(Serializable):
    sections: List[ContentSection]
    language: Optional[str]


@dataclass(slots=True)
class TechFingerprint(Serializable):
    frameworks: List[str]
    evidence: Dict[str, List[str]]


@dataclass(slots=True)
class Issue(Serializable):
    description: str
    severity: str
    recommendation: str


@dataclass(slots=True)
class A11yReport(Serializable):
    score: float
    issues: List[Issue]


@dataclass(slots=True)
class SEOReport(Serializable):
    score: float
    issues: List[Issue]


@dataclass(slots=True)
class SecurityReport(Serializable):
    score: float
    issues: List[Issue]


@dataclass(slots=True)
class MediaInfo(Serializable):
    url: str
    alt_text: Optional[str]
    size_bytes: Optional[int]
    format: Optional[str]


@dataclass(slots=True)
class MediaReport(Serializable):
    images: List[MediaInfo]


@dataclass(slots=True)
class NavigationItem(Serializable):
    label: str
    href: str
    children: List["NavigationItem"] = field(default_factory=list)


@dataclass(slots=True)
class NavModel(Serializable):
    items: List[NavigationItem]


@dataclass(slots=True)
class NavigationBundle(Serializable):
    location: str
    style: str
    dropdown: str
    dropdown_default: str
    items: List[NavigationItem]
    logo: Optional[str] = None
    sticky: bool = False
    config: Dict[str, Any] = field(default_factory=dict)
    html: str = ""
    css: str = ""
    js: str = ""


@dataclass(slots=True)
class RenewalAction(Serializable):
    identifier: str
    description: str
    impact: str
    effort_hours: float


@dataclass(slots=True)
class RenewalPlan(Serializable):
    goals: List[str]
    actions: List[RenewalAction]
    estimate_hours: float


@dataclass(slots=True)
class ContentBlock(Serializable):
    title: Optional[str]
    body: str
    type: str = "text"
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ContentBundle(Serializable):
    blocks: List[ContentBlock]
    meta_title: Optional[str]
    meta_description: Optional[str]
    fallback_used: bool = False


@dataclass(slots=True)
class ThemeTokens(Serializable):
    colors: Dict[str, str]
    typography: Dict[str, str]
    spacing: Dict[str, str]
    radius: Dict[str, str]
    breakpoints: Dict[str, str]
    elevation: Dict[str, str]
    slots: Dict[str, Dict[str, str]]

    def css_variables(self) -> Dict[str, str]:
        """Return a flattened mapping of CSS custom properties."""

        variables: Dict[str, str] = {}

        for name, value in self.colors.items():
            variables[f"--color-{name.replace('_', '-')}"] = value

        variables.update(
            {
                "--font-body-family": self.typography.get(
                    "body_family", self.typography.get("font_family", "'Inter', sans-serif")
                ),
                "--font-heading-family": self.typography.get(
                    "heading_family",
                    self.typography.get("body_family", self.typography.get("font_family", "'Inter', sans-serif")),
                ),
                "--font-base-size": self.typography.get("base_size", "16px"),
                "--font-scale": self.typography.get("scale", "1.25"),
                "--font-line-height": self.typography.get("line_height", "1.6"),
                "--font-weight-heading": self.typography.get("heading_weight", "600"),
            }
        )

        for name, value in self.spacing.items():
            variables[f"--space-{name.replace('_', '-')}"] = value

        for name, value in self.radius.items():
            variables[f"--radius-{name.replace('_', '-')}"] = value

        for name, value in self.breakpoints.items():
            variables[f"--breakpoint-{name.replace('_', '-')}"] = value

        for name, value in self.elevation.items():
            variables[f"--shadow-{name.replace('_', '-')}"] = value

        for area, config in self.slots.items():
            for name, value in config.items():
                variables[f"--slot-{area.replace('_', '-')}-{name.replace('_', '-')}"] = value

        return variables


@dataclass(slots=True)
class BuildArtifact(Serializable):
    output_dir: str
    files: List[str]
    navigation_bundle: NavigationBundle | None = None


@dataclass(slots=True)
class DiffResult(Serializable):
    page: str
    diff: str


@dataclass(slots=True)
class PreviewIndex(Serializable):
    diffs: List[DiffResult]
    style_deltas: List[str] = field(default_factory=list)


@dataclass(slots=True)
class OfferDoc(Serializable):
    title: str
    summary: str
    pricing_eur: float


@dataclass(slots=True)
class MemoryRecord(Serializable):
    key: str
    payload: Dict[str, str]
    stored_at: datetime = field(default_factory=datetime.utcnow)
