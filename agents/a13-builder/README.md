# Agent A13 – Builder

---

## 1. Übersicht / Rolle im System

Der **Builder Agent (A13)** ist die **Umsetzungs-Engine**, die aus den von anderen Agenten gelieferten Bausteinen (Navigation, Inhalte, Theming) eine vollständige **statische Website** erzeugt.
Während A11 Inhalte und A12 Themes bereitstellen, führt A13 alles zusammen und produziert die **neue Site-Version** inkl. Assets.

Ziele:

* Modularen, reproduzierbaren Build-Prozess implementieren.
* HTML, CSS, Media und Metadaten in ein **distributables Artefakt** (BuildArtifact) überführen.
* Unterschiede zwischen „alter“ und „neuer“ Site klar nachvollziehbar machen (für A14 Comparator).
* Unterstützung für alternative Layouts / Frameworks (Bootstrap, Tailwind, Custom).

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **NavModel.json (A9)** → Strukturierte Navigation
* **ContentBundle.json (A11)** → AI-generierte Texte & Section HTML
* **ThemeTokens.json (A12)** → Farb- und Typografie-Tokens
* **MediaReport.json (A8)** → Optimierte Bilder, Pfade
* **RenewalPlan.json (A10)** → Build-relevante Maßnahmen (z. B. „Minify CSS“)

Beispiel:

```json
{
  "nav": {"root":{"id":"root","label":"Start","url":"/"}},
  "content": {"pages":[{"url":"/","title":"Startseite","sections":[{"id":"hero","html":"<section>...</section>"}]}]},
  "theme": {"brand":{"primary":"#0d6efd","secondary":"#6610f2"}},
  "plan": {"actions":[{"id":"minify-css","impact":"mittel"}]}
}
```

### Ausgabe

* **BuildArtifact.json**

```json
{
  "dist": "sandbox/newsite/",
  "files": ["index.html", "leistungen/index.html", "kontakt/index.html", "assets/main.css", "assets/theme.css"],
  "meta": {"build_time": "2025-09-26T10:22:00Z", "size_kb": 3820}
}
```

---

## 3. Interne Abhängigkeiten

### Technologien

* **Templating**: Jinja2 (Python) → HTML-Render mit Tokens
* **Static Assets**: Optimierung mit css-html-js-minify oder eigener Pipeline
* **Token Injection**: ThemeTokens → CSS Variablen, SCSS oder Tailwind Config
* **Linking**: NavModel → Breadcrumbs, Header/Footer Navigation

### Algorithmen

* **Static Site Generation**: Jede Page als HTML-Datei erzeugen.
* **Asset Pipeline**: CSS minify, inline critical CSS.
* **Image Handling**: WebP/AVIF Konvertierung (basierend auf MediaReport).
* **Meta Injection**: SEO-Daten (Title, Description, Schema.org) ins `<head>`.

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Speichern von Build-Artefakten (HTML, CSS, Assets).
* **Memory MCP**: Ablage von Build-Metadaten für spätere Vergleiche.
* **Comparator (A14)**: braucht Artefakte, um Vorher/Nachher zu vergleichen.
* **Offer (A15)**: nutzt Kennzahlen (Größe, Optimierungsgrad).

---

## 5. Ablauf / Workflow intern

1. **Input aggregieren**

   * NavModel, ContentBundle, ThemeTokens, Plan einlesen.

2. **Template-Setup**

   * Grundlayout definieren (`base.html`, `header.html`, `footer.html`).
   * Navigation + ThemeTokens einbinden.

3. **Seiten-Rendering**

   * Pro Content-Seite HTML generieren.
   * Breadcrumbs automatisch aus NavModel erzeugen.

4. **Assets erzeugen**

   * ThemeTokens → CSS-Variablen oder Bootstrap/Tailwind Theme.
   * CSS + JS minifizieren, ggf. Split für Critical CSS.

5. **Bilder integrieren**

   * Optimierte Bilder (von A8) einbinden.
   * Responsive `srcset` + Lazy Loading.

6. **Output erzeugen**

   * Dateien in `sandbox/newsite/` ablegen.
   * BuildArtifact.json mit Metadaten schreiben.

---

## 6. Quality Gates & Non-Functional Requirements

* **Build-Zeit**: < 5 Sekunden für 200 Seiten.
* **Kompatibilität**: Ausspielbar auf jedem CDN (Cloudflare, Netlify, Vercel).
* **Responsiveness**: Standard-Breakpoints abgedeckt.
* **SEO-Ready**: Title/Description vorhanden, semantische Tags `<main>`, `<nav>`.
* **Performance**: PageWeight ≤ 500KB für Landing-Page.
* **Determinismus**: Gleiche Inputs → identisches Build-Artefakt.

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Als eigenständiger Service, on-demand Build.
* **Scaling**: Kann parallel für mehrere Domains laufen.
* **Persistence**: Alle Builds + Artefakte versioniert im Filesystem MCP.
* **Observability**:

  * Logs: Build-Dauer, Artefaktgröße
  * Metrics: CSS/JS Reduction %, Image Savings %
  * Alerts: Build-Fehler, defekte Links

---

## 8. Erweiterungspotenzial & offene Fragen

* **Multi-Framework Support**: Bootstrap & Tailwind parallel, Auswahl durch Nutzer.
* **Component Library**: eigene modulare Komponenten (Buttons, Forms, Cards).
* **Headless CMS Integration**: statt statischer JSON-Inputs, direkt API (z. B. Strapi).
* **Preview Links**: Automatisch als Docker-Container oder auf Subdomain deployen.
* **Theming Variations**: Builder könnte mehrere Layouts generieren (klassisch, minimalistisch, modern).

---

📄 **Fazit**:
Der Builder Agent A13 ist der **Produktionsmotor**. Er wandelt Analysen, Inhalte und Designvorgaben in ein **reales, testbares Build-Artefakt** um.
Damit wird die Pipeline greifbar: von Analyse & Planung (A0–A12) hin zur sichtbaren Website, die Kunden vergleichen und bewerten können.

## Testing

* `pytest tests/unit/agents/test_builder_agent.py -q`
* Tests prüfen Dateiausgabe, Slug-Kollisionen und Framework-Validierung mit den Dummy-Blöcken aus `tests/conftest.py`.
* Der Integrationstest erzeugt zusätzlich einen echten `sandbox/newsite/`-Build.

