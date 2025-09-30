# Agent A12 – Theming

---

## 1. Übersicht / Rolle im System

Der **Theming Agent (A12)** ist verantwortlich für die **Gestaltung und visuelle Identität** der generierten Website.
Während A11 Inhalte produziert, definiert A12 die **Designsprache** (Farben, Typografie, Abstände, Komponenten-Stil).

Ziele:

* ein konsistentes, modernes und barrierefreies Designsystem bereitstellen,
* alternative Layout-/Designvarianten auf Knopfdruck erzeugen („Blau/Weiß Bootstrap Theme“, „Minimalistisch in Schwarz/Weiß“),
* responsives Verhalten (Mobile, Tablet, Desktop) berücksichtigen,
* Ergebnisse in einem **maschinell nutzbaren Token-Format** liefern (ThemeTokens.json).

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **RenewalPlan.json (A10)** → z. B. „Upgrade Bootstrap 3 → 5“
* **ContentNew.json (A11)** → Seiteninhalte, Sections
* **Optionale User-Vorgaben** → „Farbschema Blau/Weiß“, „Serif Fonts“

Beispiel:

```json
{
  "plan": {"actions": [{"id": "upgrade-bootstrap", "impact": "hoch"}]},
  "content_new": {"pages": [{"url": "/", "title": "Start"}]},
  "theme_prefs": {"colors": "blue-white", "typography": "sans-serif"}
}
```

### Ausgabe

* **ThemeTokens.json**

```json
{
  "brand": {"primary": "#0d6efd", "secondary": "#6610f2", "neutral": "#f8f9fa"},
  "typography": {"base": "system-ui", "scale": 1.25, "headings": "bold"},
  "spacing": {"sm": "0.5rem", "md": "1rem", "lg": "2rem"},
  "radius": {"sm": "0.25rem", "xl": "1rem"},
  "components": {
    "button": {"variant": "solid", "shape": "rounded", "hover": "darken"},
    "navbar": {"variant": "sticky", "bg": "primary"}
  }
}
```

---

## 3. Interne Abhängigkeiten

### Technologien

* **LLMs (mehrere)**:

  * für kreative Theming-Vorschläge (Palette, Layout-Vorschläge),
  * für JSON-konforme Tokens.
* **Design-Tokens-Schema**: W3C Style Dictionary oder Tailwind/Jinja2-kompatibel.
* **Validator**: prüft Farbkontraste (WCAG 2.1 AA/AAA).
* **CSS-Generator**: optional, um Tokens direkt in CSS zu konvertieren.

### Algorithmen

* **Palette-Generator**: Harmonische Farbsets (HSL-Berechnung, Kontrastprüfung).
* **Responsive Breakpoints**: Standardwerte (576px, 768px, 992px, 1200px).
* **Accessibility Checks**: Farbkontraste, Fontgrößen.
* **Theme-Mapping**: Tokens → Bootstrap, Tailwind oder Custom CSS.

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Speichern von ThemeTokens.json.
* **Memory MCP**: Speicherung und Vergleich von alten/neuen Designvarianten.
* **Builder (A13)**: nutzt ThemeTokens.json, um HTML/CSS zu generieren.
* **Validator-Agent**: prüft WCAG-Konformität und Lesbarkeit.

---

## 5. Ablauf / Workflow intern

1. **Input laden**

   * RenewalPlan, ContentNew, ThemePreferences

2. **Designsystem-Erstellung**

   * LLM generiert 2–3 Varianten von ThemeTokens.json
   * Farbkontraste berechnen (Kontrast ≥ 4.5:1 für Text)

3. **Responsive Definition**

   * Breakpoints & Layout-Grids festlegen

4. **Validation**

   * JSON-Schema prüfen
   * Accessibility-Check (WCAG-Validator)

5. **Output**

   * ThemeTokens.json speichern
   * optional: CSS-Datei generieren für Preview

---

## 6. Quality Gates & Non-Functional Requirements

* **Kontrast**: alle Farbpaare WCAG 2.1 AA konform
* **Responsiveness**: Layouts müssen auf 3 Breakpoints funktionieren
* **Erweiterbarkeit**: Tokens in jedes Framework (Bootstrap, Tailwind, Jinja2) einsetzbar
* **Konsistenz**: Buttons, Links, Headings einheitlich
* **Performance**: Theming-Agent < 2s für Token-Generierung

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: eigenständiger Service, LLM-basiert
* **Scaling**: parallele Generierung von Designvarianten
* **Persistence**: Memory MCP → Historie von Themes (z. B. Blau/Weiß vs. Dunkel/Minimal)
* **Observability**:

  * Logs: Anzahl generierter Variationen
  * Metrics: WCAG-Compliance-Rate
  * Alerts: Falls ThemeTokens unvollständig sind

---

## 8. Erweiterungspotenzial & offene Fragen

* **Dark Mode**: Soll A12 automatisch Light/Dark Themes erzeugen?
* **Brand Guidelines Import**: Soll A12 Marken-Styleguides importieren (z. B. CI-PDF)?
* **Visual Mockups**: Soll A12 zusätzlich Screenshots mit generiertem Theme liefern?
* **Cross-Framework Mapping**: Tailwind + Bootstrap parallel unterstützen?

---

📄 **Fazit**:
A12 ist der **Design-Orchestrator**. Er transformiert abstrakte Branding-Vorgaben + RenewalPlan in **standardisierte Design Tokens**.
Damit kann A13 (Builder) Websites konsistent und modern rendern – egal ob als Minimal-Update oder Full Redesign.
