"""Models used by the post-edit pipeline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence


def _ensure_dict(value: Dict[str, Any] | None) -> Dict[str, Any]:
    return dict(value or {})


def _ensure_list(value: Sequence[Any] | None) -> List[Any]:
    return list(value or [])


@dataclass(slots=True)
class SiteBlock:
    """Represents a logical block of content within a page."""

    id: str
    text: str
    type: str = "text"
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "type": self.type,
            "meta": dict(self.meta or {}),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SiteBlock":
        return cls(
            id=str(data.get("id", "")),
            text=str(data.get("text", "")),
            type=str(data.get("type", "text")),
            meta=dict(data.get("meta", {})),
        )


@dataclass(slots=True)
class SitePage:
    """Represents a page in the SiteState."""

    path: str
    url: str
    title: str
    blocks: List[SiteBlock] = field(default_factory=list)
    sections: List[Dict[str, Any]] = field(default_factory=list)
    assets: Dict[str, Any] = field(default_factory=dict)
    seo: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)
    content_hash: str | None = None
    rendered: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "url": self.url,
            "title": self.title,
            "blocks": [block.to_dict() for block in self.blocks],
            "sections": _ensure_list(self.sections),
            "assets": _ensure_dict(self.assets),
            "seo": _ensure_dict(self.seo),
            "meta": _ensure_dict(self.meta),
            "content_hash": self.content_hash,
            "rendered": self.rendered,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SitePage":
        blocks = [SiteBlock.from_dict(item) for item in data.get("blocks", [])]
        return cls(
            path=str(data.get("path", "")),
            url=str(data.get("url", "")),
            title=str(data.get("title", "")),
            blocks=blocks,
            sections=_ensure_list(data.get("sections")),
            assets=_ensure_dict(data.get("assets")),
            seo=_ensure_dict(data.get("seo")),
            meta=_ensure_dict(data.get("meta")),
            content_hash=data.get("content_hash"),
            rendered=data.get("rendered"),
        )


@dataclass(slots=True)
class SiteState:
    """Canonical representation of the crawled and edited website."""

    nav: Dict[str, Any] = field(
        default_factory=lambda: {"items": [], "layout": {}, "html": ""}
    )
    head: Dict[str, Any] = field(
        default_factory=lambda: {"title": "", "meta": {}, "links": []}
    )
    pages: List[SitePage] = field(default_factory=list)
    theme: Dict[str, Any] = field(
        default_factory=lambda: {
            "tokens": {
                "palette": {"primary": "#0d6efd", "background": "#ffffff"},
                "shape": {"radius": "0.5rem"},
                "shadow": {"medium": "0 4px 12px rgba(0,0,0,0.1)"},
            },
            "palette": {},
            "radii": {},
            "shadow": {},
            "spacing": {},
            "typography": {},
        }
    )
    css_bundle: Dict[str, Any] = field(
        default_factory=lambda: {
            "raw": "",
            "tokens": {},
            "framework": "bootstrap",
        }
    )
    assets: Dict[str, Any] = field(
        default_factory=lambda: {"images": [], "logo": {}}
    )
    seo: Dict[str, Any] = field(
        default_factory=lambda: {"meta": {}, "ld_json": {}}
    )
    build: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nav": _ensure_dict(self.nav),
            "head": _ensure_dict(self.head),
            "pages": [page.to_dict() for page in self.pages],
            "theme": _ensure_dict(self.theme),
            "css_bundle": _ensure_dict(self.css_bundle),
            "assets": _ensure_dict(self.assets),
            "seo": _ensure_dict(self.seo),
            "build": _ensure_dict(self.build),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "SiteState":
        if not data:
            return cls()
        pages = [SitePage.from_dict(item) for item in data.get("pages", [])]
        state = cls(
            nav=_ensure_dict(data.get("nav")),
            head=_ensure_dict(data.get("head")),
            pages=pages,
            theme=_ensure_dict(data.get("theme")),
            css_bundle=_ensure_dict(data.get("css_bundle")),
            assets=_ensure_dict(data.get("assets")),
            seo=_ensure_dict(data.get("seo")),
            build=_ensure_dict(data.get("build")),
        )
        state.ensure_defaults()
        return state

    def ensure_defaults(self) -> None:
        """Ensure required keys exist for downstream components."""

        self.nav.setdefault("items", [])
        self.nav.setdefault("layout", {})
        self.nav.setdefault("html", "")
        self.head.setdefault("title", "")
        self.head.setdefault("meta", {})
        self.head.setdefault("links", [])
        self.theme.setdefault("tokens", {})
        self.theme.setdefault("palette", {})
        self.theme.setdefault("radii", {})
        self.theme.setdefault("shadow", {})
        self.theme.setdefault("spacing", {})
        self.theme.setdefault("typography", {})
        self.css_bundle.setdefault("raw", "")
        self.css_bundle.setdefault("tokens", {})
        self.css_bundle.setdefault("framework", "bootstrap")
        self.assets.setdefault("images", [])
        self.assets.setdefault("logo", {})
        self.seo.setdefault("meta", {})
        self.seo.setdefault("ld_json", {})
        self.build.setdefault("history", [])

    def find_page(self, path_or_url: str) -> SitePage | None:
        """Return the first page matching ``path_or_url``."""

        for page in self.pages:
            if page.path == path_or_url or page.url == path_or_url:
                return page
        return None

    def ensure_page(self, path: str, *, url: str | None = None, title: str | None = None) -> SitePage:
        page = self.find_page(path)
        if page is None:
            page = SitePage(path=path, url=url or path, title=title or path)
            self.pages.append(page)
        return page


@dataclass(slots=True)
class ChangeOperation:
    """Single operation emitted by the planner."""

    type: str
    payload: Dict[str, Any]
    page: str | None = None
    block_id: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        data = {"type": self.type, "payload": safe_payload(self.payload)}
        if self.page is not None:
            data["page"] = self.page
        if self.block_id is not None:
            data["blockId"] = self.block_id
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeOperation":
        return cls(
            type=str(data.get("type")),
            payload=dict(data.get("payload", {})),
            page=data.get("page"),
            block_id=data.get("blockId"),
        )


@dataclass(slots=True)
class ChangeSet:
    """Collection of operations derived from the planner."""

    targets: List[str]
    operations: List[ChangeOperation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "targets": list(self.targets),
            "operations": [op.to_dict() for op in self.operations],
        }

    def hash(self) -> str:
        canonical = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def is_empty(self) -> bool:
        return not self.operations


def safe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a JSON-safe payload recursively."""

    def _convert(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): _convert(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [_convert(item) for item in value]
        return value

    return _convert(payload)


def merge_operations(operations: Iterable[ChangeOperation]) -> List[ChangeOperation]:
    """Return operations sorted deterministically for idempotency."""

    sorted_ops = sorted(
        operations,
        key=lambda op: (
            op.type,
            op.page or "",
            op.block_id or "",
            json.dumps(safe_payload(op.payload), sort_keys=True),
        ),
    )
    return list(sorted_ops)


__all__ = [
    "ChangeOperation",
    "ChangeSet",
    "SiteBlock",
    "SitePage",
    "SiteState",
    "merge_operations",
    "safe_payload",
]

