"""Navigation builder agent responsible for rendering configurable menus."""

from __future__ import annotations

import html
import secrets
from dataclasses import replace
from textwrap import dedent
from typing import Any, Dict, Iterable, List, Sequence

from .base import Agent
from ..models import NavModel, NavigationBundle, NavigationItem, ThemeTokens

_ALLOWED_STYLES = {"horizontal", "vertical", "mega-menu"}
_ALLOWED_LOCATIONS = {
    "top-left",
    "top-right",
    "top-center",
    "side-left",
    "side-right",
    "footer",
}
_ALLOWED_DROPDOWNS = {"none", "hover", "click"}
_ALLOWED_DEFAULTS = {"open", "closed"}


def _normalise_label(label: str) -> str:
    text = " ".join(label.split())
    if not text:
        return "Untitled"
    if len(text) > 48:
        text = text[:47].rstrip() + "…"
    candidate = text.title()
    # Preserve common acronyms
    for token in ("FAQ", "SEO", "LLM", "AI"):
        candidate = candidate.replace(token.title(), token)
    return candidate


def _clone_items(items: Sequence[NavigationItem]) -> List[NavigationItem]:
    cloned: List[NavigationItem] = []
    for item in items:
        refined = replace(item, label=_normalise_label(item.label))
        refined.children = _clone_items(item.children)
        cloned.append(refined)
    return cloned


def _generate_id(prefix: str = "nav") -> str:
    return f"{prefix}-{secrets.token_hex(4)}"


class NavigationBuilderAgent(
    Agent[tuple[NavModel, ThemeTokens | None, Dict[str, Any] | None], NavigationBundle]
):
    """Render a :class:`NavModel` into HTML/CSS snippets for embedding."""

    def __init__(
        self,
        *,
        css_framework: str = "vanilla",
        navigation_config: Dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name="A13.NavigationBuilder")
        self._framework = css_framework.strip().lower()
        self._base_config = navigation_config or {}

    def run(
        self,
        data: tuple[NavModel, ThemeTokens | None, Dict[str, Any] | None],
    ) -> NavigationBundle:
        nav_model, theme, overrides = data
        items = _clone_items(nav_model.items)
        config = self._resolve_config(overrides or {})

        renderer = {
            "bootstrap": self._render_bootstrap,
            "tailwind": self._render_tailwind,
        }.get(self._framework, self._render_vanilla)

        html_snippet, css_snippet, js_snippet = renderer(items, config, theme)

        bundle = NavigationBundle(
            location=config["location"],
            style=config["style"],
            dropdown=config["dropdown"],
            dropdown_default=config["dropdown_default"],
            items=items,
            logo=config.get("logo"),
            sticky=bool(config.get("sticky", False)),
            config={key: value for key, value in config.items() if key not in {"items"}},
            html=html_snippet,
            css=css_snippet,
            js=js_snippet,
        )
        return bundle

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _resolve_config(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {
            "style": "horizontal",
            "location": "top-left",
            "dropdown": "hover",
            "dropdown_default": "closed",
            "brand_label": "Renewed Website",
            "home_href": "index.html",
        }
        resolved.update(self._base_config)
        resolved.update(overrides)

        style = str(resolved.get("style", "horizontal")).strip().lower()
        if style not in _ALLOWED_STYLES:
            raise ValueError(f"Unsupported navigation style '{style}'")
        location = str(resolved.get("location", "top-left")).strip().lower()
        if location not in _ALLOWED_LOCATIONS:
            raise ValueError(f"Unsupported navigation location '{location}'")
        dropdown = str(resolved.get("dropdown", "hover")).strip().lower()
        if dropdown not in _ALLOWED_DROPDOWNS:
            raise ValueError(f"Unsupported dropdown mode '{dropdown}'")
        dropdown_default = (
            str(resolved.get("dropdown_default", "closed")).strip().lower()
        )
        if dropdown_default not in _ALLOWED_DEFAULTS:
            raise ValueError(f"Unsupported dropdown default '{dropdown_default}'")

        resolved["style"] = style
        resolved["location"] = location
        resolved["dropdown"] = dropdown
        resolved["dropdown_default"] = dropdown_default
        resolved.setdefault("menu_id", _generate_id("nav"))
        resolved.setdefault("collapse_id", f"{resolved['menu_id']}-collapse")
        return resolved

    # ------------------------------------------------------------------
    # Bootstrap rendering
    # ------------------------------------------------------------------
    def _render_bootstrap(
        self,
        items: Iterable[NavigationItem],
        config: Dict[str, Any],
        theme: ThemeTokens | None,
    ) -> tuple[str, str, str]:
        menu_id = config["menu_id"]
        collapse_id = config["collapse_id"]
        sticky_class = " sticky-top" if config.get("sticky") else ""
        location = config["location"]
        brand_label = html.escape(str(config.get("brand_label", "Renewed Website")))
        logo = config.get("logo")

        alignment_class = {
            "top-left": "justify-content-lg-start",
            "top-center": "justify-content-lg-center",
            "top-right": "justify-content-lg-end",
        }.get(location, "justify-content-lg-start")
        if location == "footer":
            container_tag = "footer"
        elif location.startswith("side"):
            container_tag = "aside"
        else:
            container_tag = "header"

        dropdown_default = config["dropdown_default"]
        collapse_classes = "collapse navbar-collapse"
        if dropdown_default == "open":
            collapse_classes += " show"

        nav_classes = ["navbar", "navbar-expand-lg", "wr-navigation"]
        if config["style"] == "vertical" or location.startswith("side"):
            nav_classes.extend(["flex-lg-column", "text-lg-start"])

        nav_html = [
            f"<{container_tag} class=\"wr-nav-container{sticky_class}\" data-location=\"{location}\" id=\"{menu_id}-container\">",
            '  <a class="skip-link" href="#main-content">Skip to main content</a>',
            f"  <nav id=\"{menu_id}\" class=\"{' '.join(nav_classes)}\" data-bs-theme=\"dark\" aria-label=\"Primary navigation\">",
            "    <div class=\"container-xl d-flex align-items-center gap-3\">",
        ]

        brand_parts: List[str] = [
            f"<a class=\"navbar-brand d-flex align-items-center gap-2\" href=\"{html.escape(str(config.get('home_href', 'index.html')))}\">"
        ]
        if logo:
            brand_parts.append(
                f"  <img src=\"{html.escape(str(logo))}\" alt=\"{brand_label}\" class=\"nav-logo\" height=\"36\" />"
            )
        brand_parts.append(f"  <span>{brand_label}</span>")
        brand_parts.append("</a>")
        nav_html.extend([f"    {line}" for line in brand_parts])

        nav_html.append(
            f"    <button class=\"navbar-toggler ms-auto\" type=\"button\" data-bs-toggle=\"collapse\" data-bs-target=\"#{collapse_id}\" aria-controls=\"{collapse_id}\" aria-expanded=\"{str(dropdown_default == 'open').lower()}\" aria-label=\"Toggle navigation\">"
        )
        nav_html.append("      <span class=\"navbar-toggler-icon\"></span>")
        nav_html.append("    </button>")
        nav_html.append(
            f"    <div class=\"{collapse_classes} {alignment_class}\" id=\"{collapse_id}\">"
        )

        items_markup = self._render_bootstrap_items(list(items), config)
        if items_markup.strip():
            nav_html.append("      <ul class=\"navbar-nav ms-lg-auto gap-lg-2\">")
            nav_html.append(items_markup)
            nav_html.append("      </ul>")
        else:
            nav_html.append(
                "      <p class=\"navbar-text text-white-50 mb-0 small\">Navigation will appear after crawling.</p>"
            )

        nav_html.extend([
            "    </div>",
            "    </div>",
            "  </nav>",
            f"</{container_tag}>",
        ])

        js_snippet = ""
        if config["dropdown"] == "hover":
            js_template = """
                document.querySelectorAll('#__ID__ .dropdown').forEach(function (drop) {
                  if (!window.matchMedia('(min-width: 992px)').matches) return;
                  drop.addEventListener('mouseenter', function () {
                    const menu = drop.querySelector('.dropdown-menu');
                    if (menu) { drop.classList.add('show'); menu.classList.add('show'); }
                  });
                  drop.addEventListener('mouseleave', function () {
                    const menu = drop.querySelector('.dropdown-menu');
                    if (menu) { drop.classList.remove('show'); menu.classList.remove('show'); }
                  });
                });
            """
            js_snippet = dedent(js_template).replace("__ID__", menu_id).strip()

        css_snippet = dedent(
            """
            .wr-nav-container {
              background: var(--slot-nav-background, var(--color-primary, #0d6efd));
              color: var(--slot-nav-text, #ffffff);
              z-index: 1030;
            }
            .wr-nav-container .navbar-nav .nav-link {
              color: var(--slot-nav-text, #ffffff);
              font-weight: 500;
            }
            .wr-nav-container .navbar-nav .nav-link:hover,
            .wr-nav-container .navbar-nav .nav-link:focus {
              color: var(--slot-nav-hover, var(--color-accent, #ffc107));
            }
            .wr-nav-container .nav-logo {
              max-height: 42px;
              width: auto;
            }
            .wr-nav-container .mega-menu {
              min-width: min(720px, 95vw);
            }
            @media (max-width: 991.98px) {
              .wr-nav-container .navbar-nav .dropdown-menu {
                position: static;
                float: none;
              }
            }
            """
        ).strip()

        return "\n".join(nav_html), css_snippet, js_snippet

    def _render_bootstrap_items(self, items: List[NavigationItem], config: Dict[str, Any]) -> str:
        dropdown_mode = config["dropdown"]
        style = config["style"]
        menu_id = config["menu_id"]

        lines: List[str] = []
        for index, item in enumerate(items, start=1):
            has_children = bool(item.children)
            item_id = f"{menu_id}-item-{index}"
            label = html.escape(item.label)
            href = html.escape(item.href)

            if has_children and dropdown_mode != "none":
                dropdown_class = "dropdown"
                menu_class = "dropdown-menu"
                if style == "mega-menu":
                    menu_class += " mega-menu p-4"
                lines.append(
                    f"        <li class=\"nav-item {dropdown_class}\" id=\"{item_id}\">"
                )
                lines.append(
                    f"          <a class=\"nav-link dropdown-toggle\" href=\"{href}\" role=\"button\" data-bs-toggle=\"dropdown\" aria-expanded=\"false\">{label}</a>"
                )
                lines.append(f"          <ul class=\"{menu_class}\">")
                if style == "mega-menu":
                    lines.append("            <div class=\"row g-4\">")
                    for column in item.children:
                        lines.append("              <div class=\"col-12 col-md-6 col-lg-4\">")
                        lines.append(
                            f"                <a class=\"dropdown-item fw-semibold\" href=\"{html.escape(column.href)}\">{html.escape(column.label)}</a>"
                        )
                        if column.children:
                            for sub in column.children:
                                lines.append(
                                    f"                <a class=\"dropdown-item\" href=\"{html.escape(sub.href)}\">{html.escape(sub.label)}</a>"
                                )
                        lines.append("              </div>")
                    lines.append("            </div>")
                else:
                    lines.append(self._render_bootstrap_dropdown_children(item.children, menu_id, 1))
                lines.append("          </ul>")
                lines.append("        </li>")
            elif has_children:
                lines.append("        <li class=\"nav-item\">")
                lines.append(f"          <a class=\"nav-link\" href=\"{href}\">{label}</a>")
                lines.append("          <ul class=\"nav flex-column nested\">")
                lines.append(self._render_bootstrap_dropdown_children(item.children, menu_id, 1))
                lines.append("          </ul>")
                lines.append("        </li>")
            else:
                lines.append("        <li class=\"nav-item\">")
                lines.append(f"          <a class=\"nav-link\" href=\"{href}\">{label}</a>")
                lines.append("        </li>")
        return "\n".join(lines)

    def _render_bootstrap_dropdown_children(
        self, items: Sequence[NavigationItem], menu_id: str, depth: int
    ) -> str:
        lines: List[str] = []
        for index, item in enumerate(items, start=1):
            label = html.escape(item.label)
            href = html.escape(item.href)
            has_children = bool(item.children)
            item_id = f"{menu_id}-sub-{depth}-{index}"
            if has_children:
                lines.append(
                    f"            <li class=\"dropdown-submenu\" id=\"{item_id}\">"
                )
                lines.append(
                    f"              <a class=\"dropdown-item dropdown-toggle\" href=\"{href}\" role=\"button\">{label}</a>"
                )
                lines.append("              <ul class=\"dropdown-menu\">")
                lines.append(
                    self._render_bootstrap_dropdown_children(item.children, menu_id, depth + 1)
                )
                lines.append("              </ul>")
                lines.append("            </li>")
            else:
                lines.append(
                    f"            <li><a class=\"dropdown-item\" href=\"{href}\">{label}</a></li>"
                )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Tailwind rendering
    # ------------------------------------------------------------------
    def _render_tailwind(
        self,
        items: Iterable[NavigationItem],
        config: Dict[str, Any],
        theme: ThemeTokens | None,
    ) -> tuple[str, str, str]:
        nav_id = config["menu_id"]
        sticky_class = " sticky top-0" if config.get("sticky") else ""
        location = config["location"]
        alignment_class = {
            "top-left": "lg:justify-start",
            "top-center": "lg:justify-center",
            "top-right": "lg:justify-end",
        }.get(location, "lg:justify-start")

        base_classes = "wr-tw-nav bg-gradient-to-r from-primary-600 to-primary-500 text-white"
        nav_wrapper = [
            f"<div class=\"{base_classes}{sticky_class}\" data-location=\"{location}\" id=\"{nav_id}\">",
            '  <a class="skip-link" href="#main-content">Skip to main content</a>',
            "  <div class=\"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8\">",
            "    <div class=\"flex h-16 items-center justify-between gap-4\">",
            f"      <a href=\"{html.escape(str(config.get('home_href', 'index.html')))}\" class=\"flex items-center gap-3 text-white font-semibold text-lg\">",
        ]
        if config.get("logo"):
            nav_wrapper.append(
                f"        <img src=\"{html.escape(str(config['logo']))}\" alt=\"{html.escape(str(config.get('brand_label', 'Renewed Website')))}\" class=\"h-10 w-auto\" />"
            )
        nav_wrapper.append(
            f"        <span>{html.escape(str(config.get('brand_label', 'Renewed Website')))}</span>"
        )
        nav_wrapper.append("      </a>")
        nav_wrapper.append(
            "      <button type=\"button\" class=\"tw-nav-toggle inline-flex items-center justify-center rounded-md p-2 text-white focus:outline-none focus:ring-2 focus:ring-white lg:hidden\" aria-controls=\"tw-mobile-menu\" aria-expanded=\"false\">"
        )
        nav_wrapper.append(
            "        <span class=\"sr-only\">Open navigation</span><svg class=\"h-6 w-6\" xmlns=\"http://www.w3.org/2000/svg\" fill=\"none\" viewBox=\"0 0 24 24\" stroke-width=\"1.5\" stroke=\"currentColor\"><path stroke-linecap=\"round\" stroke-linejoin=\"round\" d=\"M3.75 5.25h16.5M3.75 12h16.5m-16.5 6.75H12\" /></svg>"
        )
        nav_wrapper.append("      </button>")
        nav_wrapper.append(
            f"      <div class=\"hidden lg:flex lg:items-center lg:gap-6 {alignment_class}\" id=\"tw-desktop-menu\">"
        )
        nav_wrapper.append(self._render_tailwind_items(list(items), config))
        nav_wrapper.append("      </div>")
        nav_wrapper.append("    </div>")
        nav_wrapper.append(
            "    <div id=\"tw-mobile-menu\" class=\"tw-mobile hidden flex-col gap-2 py-4 lg:hidden\">"
        )
        nav_wrapper.append(self._render_tailwind_mobile(list(items), config))
        nav_wrapper.append("    </div>")
        nav_wrapper.append("  </div>")
        nav_wrapper.append("</div>")

        css_snippet = dedent(
            """
            .wr-tw-nav {
              background: linear-gradient(135deg, var(--color-primary, #0ea5e9), var(--color-accent, #f97316));
              position: relative;
              z-index: 50;
            }
            .wr-tw-nav .tw-nav-toggle[aria-expanded="true"] svg {
              display: none;
            }
            .wr-tw-nav .tw-nav-toggle[aria-expanded="true"]::after {
              content: '\00d7';
              font-size: 1.75rem;
              line-height: 1;
            }
            .wr-tw-nav .tw-mobile a {
              display: block;
              padding: 0.75rem 1rem;
              border-radius: var(--radius-md, 0.5rem);
              background: rgba(255, 255, 255, 0.08);
            }
            .wr-tw-nav .tw-mobile a:hover,
            .wr-tw-nav .tw-mobile a:focus {
              background: rgba(255, 255, 255, 0.16);
            }
            """
        ).strip()

        js_snippet = dedent(
            """
            const toggle = document.querySelector('.tw-nav-toggle');
            const mobileMenu = document.getElementById('tw-mobile-menu');
            if (toggle && mobileMenu) {
              toggle.addEventListener('click', () => {
                const expanded = toggle.getAttribute('aria-expanded') === 'true';
                toggle.setAttribute('aria-expanded', String(!expanded));
                mobileMenu.classList.toggle('hidden');
              });
            }
            """
        ).strip()

        return "\n".join(nav_wrapper), css_snippet, js_snippet

    def _render_tailwind_items(self, items: List[NavigationItem], config: Dict[str, Any]) -> str:
        dropdown_mode = config["dropdown"]
        lines: List[str] = []
        for item in items:
            label = html.escape(item.label)
            href = html.escape(item.href)
            if item.children and dropdown_mode != "none":
                lines.append(
                    f"        <div class=\"group relative\"><a href=\"{href}\" class=\"inline-flex items-center gap-1 font-medium\">{label}<svg class=\"h-4 w-4\" viewBox=\"0 0 20 20\" fill=\"currentColor\"><path fill-rule=\"evenodd\" d=\"M5.23 7.21a.75.75 0 011.06.02L10 11.292l3.71-4.06a.75.75 0 011.08 1.04l-4.25 4.65a.75.75 0 01-1.08 0l-4.25-4.65a.75.75 0 01.02-1.06z\" clip-rule=\"evenodd\"/></svg></a>"
                )
                lines.append(
                    "          <div class=\"absolute left-0 z-40 hidden min-w-[16rem] translate-y-3 rounded-xl bg-white p-4 text-slate-900 shadow-xl group-hover:block\">"
                )
                for child in item.children:
                    lines.append(
                        f"            <a class=\"block rounded-lg px-4 py-2 text-sm font-medium hover:bg-slate-100\" href=\"{html.escape(child.href)}\">{html.escape(child.label)}</a>"
                    )
                lines.append("          </div>")
                lines.append("        </div>")
            else:
                lines.append(
                    f"        <a href=\"{href}\" class=\"font-medium\">{label}</a>"
                )
        return "\n".join(lines)

    def _render_tailwind_mobile(self, items: List[NavigationItem], config: Dict[str, Any]) -> str:
        lines: List[str] = []
        for item in items:
            label = html.escape(item.label)
            href = html.escape(item.href)
            lines.append(f"      <a href=\"{href}\" class=\"text-white\">{label}</a>")
            if item.children:
                for child in item.children:
                    lines.append(
                        f"      <a href=\"{html.escape(child.href)}\" class=\"pl-6 text-sm opacity-90\">{html.escape(child.label)}</a>"
                    )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Vanilla rendering
    # ------------------------------------------------------------------
    def _render_vanilla(
        self,
        items: Iterable[NavigationItem],
        config: Dict[str, Any],
        theme: ThemeTokens | None,
    ) -> tuple[str, str, str]:
        nav_id = config["menu_id"]
        sticky_class = " wr-sticky" if config.get("sticky") else ""
        location = config["location"]
        brand_label = html.escape(str(config.get("brand_label", "Renewed Website")))
        alignment_class = {
            "top-left": "justify-start",
            "top-center": "justify-center",
            "top-right": "justify-end",
        }.get(location, "justify-start")

        if config["style"] == "vertical":
            style_class = " vertical"
        elif config["style"] == "mega-menu":
            style_class = " mega-menu"
        else:
            style_class = ""
        html_lines = [
            f"<nav id=\"{nav_id}\" class=\"wr-vanilla-nav {alignment_class}{sticky_class}{style_class}\" data-location=\"{location}\">",
            '  <a class="skip-link" href="#main-content">Skip to main content</a>',
            "  <div class=\"wr-nav-inner\">",
            f"    <a href=\"{html.escape(str(config.get('home_href', 'index.html')))}\" class=\"wr-brand\">",
        ]
        if config.get("logo"):
            html_lines.append(
                f"      <img src=\"{html.escape(str(config['logo']))}\" alt=\"{brand_label}\" class=\"wr-logo\" />"
            )
        html_lines.append(f"      <span>{brand_label}</span>")
        html_lines.append("    </a>")
        html_lines.append(
            "    <button class=\"wr-toggle\" type=\"button\" aria-expanded=\"false\" aria-controls=\"wr-menu\"><span class=\"sr-only\">Open navigation</span><span></span><span></span><span></span></button>"
        )
        html_lines.append("    <div id=\"wr-menu\" class=\"wr-links\">")
        html_lines.append(self._render_vanilla_list(list(items), config, depth=0))
        html_lines.append("    </div>")
        html_lines.append("  </div>")
        html_lines.append("</nav>")

        css_snippet = dedent(
            """
            .wr-vanilla-nav {
              position: relative;
              background: var(--slot-nav-background, rgba(15, 23, 42, 0.88));
              color: var(--slot-nav-text, #ffffff);
              padding: 0.75rem 1.25rem;
              z-index: 200;
            }
            .wr-vanilla-nav.wr-sticky { position: sticky; top: 0; }
            .wr-vanilla-nav .wr-nav-inner {
              display: flex;
              align-items: center;
              gap: 1.5rem;
              max-width: 1100px;
              margin: 0 auto;
            }
            .wr-vanilla-nav .wr-brand {
              display: inline-flex;
              align-items: center;
              gap: 0.75rem;
              font-weight: 600;
              color: inherit;
              text-decoration: none;
            }
            .wr-vanilla-nav .wr-logo { height: 40px; width: auto; }
            .wr-vanilla-nav .wr-links ul {
              list-style: none;
              margin: 0;
              padding: 0;
              display: flex;
              gap: 1rem;
              flex-wrap: wrap;
            }
            .wr-vanilla-nav .wr-links ul ul {
              flex-direction: column;
              gap: 0.5rem;
              background: rgba(15, 23, 42, 0.95);
              padding: 1rem;
              border-radius: var(--radius-md, 0.75rem);
              position: absolute;
              min-width: 12rem;
              display: none;
            }
            .wr-vanilla-nav .wr-links li:hover > ul,
            .wr-vanilla-nav .wr-links li:focus-within > ul {
              display: block;
            }
            .wr-vanilla-nav .wr-links a {
              color: inherit;
              text-decoration: none;
              font-weight: 500;
            }
            .wr-vanilla-nav .wr-toggle {
              display: inline-flex;
              flex-direction: column;
              gap: 0.35rem;
              background: transparent;
              border: none;
              cursor: pointer;
              margin-left: auto;
            }
            .wr-vanilla-nav .wr-toggle span {
              display: block;
              width: 1.75rem;
              height: 2px;
              background: currentColor;
            }
            .wr-vanilla-nav .wr-links {
              display: none;
            }
            .wr-vanilla-nav.open .wr-links {
              display: block;
            }
            @media (min-width: 768px) {
              .wr-vanilla-nav .wr-toggle { display: none; }
              .wr-vanilla-nav .wr-links { display: block; }
              .wr-vanilla-nav.vertical .wr-links ul { flex-direction: column; }
            }
            """
        ).strip()

        js_snippet = dedent(
            """
            const nav = document.getElementById('%(nav_id)s');
            if (nav) {
              const toggle = nav.querySelector('.wr-toggle');
              if (toggle) {
                toggle.addEventListener('click', () => {
                  const expanded = toggle.getAttribute('aria-expanded') === 'true';
                  toggle.setAttribute('aria-expanded', String(!expanded));
                  nav.classList.toggle('open');
                });
              }
            }
            """ % {"nav_id": nav_id}
        ).strip()

        return "\n".join(html_lines), css_snippet, js_snippet

    def _render_vanilla_list(
        self, items: List[NavigationItem], config: Dict[str, Any], depth: int
    ) -> str:
        if not items:
            return "      <p class=\"wr-empty\">Navigation will appear after crawling.</p>"

        lines: List[str] = ["      <ul>"]
        for item in items:
            label = html.escape(item.label)
            href = html.escape(item.href)
            lines.append("        <li>")
            lines.append(f"          <a href=\"{href}\">{label}</a>")
            if item.children:
                lines.append(self._render_vanilla_list(item.children, config, depth + 1))
            lines.append("        </li>")
        lines.append("      </ul>")
        return "\n".join(lines)


__all__ = ["NavigationBuilderAgent"]
