# agentic-webrenewal

##About:

* **multi-LLM orchestration**: pro Task können mehrere LLMs parallel antworten, ein Validator wählt das beste Ergebnis (echtes Agentic AI Pattern).
* **Layout-/Design-Modus**: nicht nur Optimierung, sondern auch komplette Neugestaltung basierend auf simplen Nutzeranweisungen („mach Bootstrap, blau/weiß, Texte bleiben erhalten“).
* **Flexibilität**: von minimaler Verbesserung bis zu vollständigem Redesign.

---

# Agentic WebRenewal

## Vision
Ein KI-gestütztes System, das bestehende Websites analysiert, Schwachstellen findet (SEO, A11y, Security, Performance) und automatisch Vorschläge für eine modernisierte Version erstellt.  
Der Flow: **Discover → Crawl → Analyse → Plan → Rewrite/Redesign → Build → Preview → Offer**

**Besonderheit:**  
- **Multi-LLM Agentic System**: jeder Task kann parallel von mehreren LLMs bearbeitet werden. Ein Validator bewertet die Ergebnisse (Kriterien: Vollständigkeit, Konsistenz, Validität des JSON) und wählt das beste aus.  
- **Flexible Modi**:  
  - *Minimal Improve*: Bestehende Seite bleibt, nur Texte oder Bilder KI-optimiert.  
  - *Full Optimization*: SEO, A11y, Security, Performance werden modernisiert.  
  - *Redesign*: Layout/Theme komplett neu generiert (z. B. „Bootstrap, blau/weiß“), Texte und Bilder können bestehen bleiben oder ebenfalls ersetzt werden.  

---

## Architektur (Python-Only)
- **Orchestrierung**: modulare Pipeline im Paket `webrenewal/` mit eigenem Agent-Interface
- **Analyse**: `beautifulsoup4`, `lxml`, `textstat`, `trafilatura`
- **Build**: `jinja2` (Static Site Generation)
- **Diff/Preview**: `difflib`
- **Persistenz**: JSON-Artefakte & Site-Build im Ordner `sandbox/`
- **Keine Frameworks** wie LangGraph oder LiteLLM

Der PoC ist vollständig in Python implementiert. Jedes Agent-Modul liefert klar typisierte
Dataclasses samt Logging. `renewal.py` dient als CLI, `webrenewal/pipeline.py` orchestriert
den Ablauf von Tool-Discovery bis Memory-Persistenz.

---

## 1) Tools und MCPs (ein Tool pro Kategorie, keine Überschneidung)

| Kategorie    | Wahl                                 | Grund |
|--------------|--------------------------------------|-------|
| Browsing     | `@playwright/mcp`                    | JS-Rendering, Script-Eval, A11y-Audits via Axe-Injection |
| HTTP         | `mcp-server-fetch`                   | HEAD/GET, Header/Body, Streaming |
| Filesystem   | `@modelcontextprotocol/server-filesystem` | Lesen/Schreiben in `sandbox/` |
| Memory       | `mcp-memory-libsql`                  | Kurz- und Langzeit-Speicher, einfache SQL/Vector-Slots |

**Parser/Readability**: `beautifulsoup4`, `lxml`, `trafilatura`  
**Templates**: `jinja2`  
**Diff/Review**: `difflib`  

---

## 2) Agenten

| Agent | Zweck | Tools/MCPs | Input | Output (Schema) |
|-------|-------|------------|-------|-----------------|
| A0 Tool-Discovery | scannt Quellen, wählt passende MCPs | Fetch | {sources[]} | ToolCatalog |
| A1 Scope | Domain normalisieren, robots.txt, Sitemap | Fetch | {url} | ScopePlan |
| A2 Crawler | HTML, Headers, Assets, JS-Render | Playwright, Fetch, FS | ScopePlan | CrawlResult |
| A3 Readability | Texte, Titel, H-Struktur | trafilatura | CrawlResult | ContentExtract |
| A4 Tech-Fingerprint | CMS/Framework/Libs erkennen | Fetch, Parser | CrawlResult | TechFingerprint |
| A5 A11y | axe-Audit | Playwright | CrawlResult | A11yReport |
| A6 SEO | Meta/OG/Links prüfen | Parser | CrawlResult | SEOReport |
| A7 Security | Headers, TLS, Mixed-Content | Fetch | CrawlResult | SecurityReport |
| A8 Media | Bilder analysieren | Parser | CrawlResult | MediaReport |
| A9 Navigation | `nav.json` aus Links, ARIA | Parser | CrawlResult | NavModel |
| A10 Plan | Maßnahmenliste, Aufwand | Multi-LLM | A3–A9 | RenewalPlan |
| A11 Rewrite | neue Texte/SEO | Multi-LLM | A3, A6, A10 | ContentBundle |
| A12 Theming | Farben, Tokens, Spacing | Multi-LLM | Vorgaben, A10 | ThemeTokens |
| A13 Builder | Jinja2-Site generieren | FS, Jinja2 | A9, A11, A12 | BuildArtifact |
| A14 Comparator | Vorher/Nachher Diffs | FS | A2, A13 | PreviewIndex |
| A15 Offer | Angebots-Dokument | Multi-LLM | A5–A7, A10, A14 | OfferDoc |
| A16 Memory | persistiert alles | Memory MCP | alle | Confirmation |

---

## 3) Beispiel-Outputs (Schemas)

**RenewalPlan**
```json
{
  "goals": ["A11y>=95","Perf>=90","SEO>=90"],
  "actions": [
    {"id": "upgrade_bootstrap", "reason": "alte Version 3.3.7", "impact": "hoch"},
    {"id": "img_opt", "reason": "hero.jpg > 1MB", "impact": "hoch"}
  ],
  "estimate_hours": 24
}
````

**ThemeTokens (Redesign-Beispiel)**

```json
{
  "brand": {"primary":"#0d6efd","secondary":"#ffffff"},
  "layout": {"framework":"bootstrap-5","theme":"blue-white"},
  "typography": {"base":"system-ui","scale":1.2}
}
```

---

## 4) End-to-End Flow

1. **A0** lädt MCPs, schreibt `.md`-Usages
2. **A1** definiert Scope (Sitemaps, robots.txt)
3. **A2** crawlt Seiten (statisch + gerendert)
4. **A3–A9** analysieren Inhalte, Technik, A11y, SEO, Security, Media, Navigation
5. **A10** plant Maßnahmen + Aufwand
6. **A11–A12** erzeugen neue Texte oder Themes

   * **Moduswahl:** *Minimal Improve*, *Full Optimization*, *Redesign*
7. **A13** baut neue statische Seite via Jinja2
8. **A14** erzeugt Vorher/Nachher Preview
9. **A15** erstellt Angebotsdokument
10. **A16** persistiert alles

**Quality-Gates**:

* Accessibility ≥95
* Performance ≥90
* SEO ≥90
  → wenn verfehlt: A10→A13 iterieren (max. 3×)

---

## 5) Herausforderungen + Lösungen

* **Bot-Schutz / Anti-Scraping**: realistische User-Agent, timeouts, Fallback Fetch
* **SPA-Inhalte**: Playwright mit `waitForNetworkIdle`
* **axe-Injection blockiert (CSP)**: lokal gebundelte Payload injizieren
* **Framework-Fingerprinting ungenau**: mehrere Evidenzen kombinieren
* **Redesign-Wünsche**: LLMs müssen freie Layout-Beschreibung in ThemeTokens + Jinja-Templates übersetzen
* **Validator-Logik**: Cross-LLM Ergebnisse evaluieren (z. B. JSON-Linting, Scoring via drittes LLM)

---

## 6) MCP Usage-Snippets

siehe Ordner `mcps/` (Filesystem, Browser, Fetch, Memory). Jeder enthält Python-Beispielcode mit `MCPServerStdio`.

---

## Setup & Run (PoC)

```bash
git clone <repo-url> agentic-webrenewal
cd agentic-webrenewal
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### FastAPI widget hosting

The feature frontend exposes static assets via FastAPI so that external sites can
load the embeddable chat widget.

1. Start the service locally:

   ```bash
   uvicorn app.main:app --reload --port 3000
   ```

2. Fetch the compiled bundle:

   ```bash
   curl http://localhost:3000/widget.js
   ```

3. To share the widget externally during development, tunnel the same port with
   Ngrok and request the file from the public URL (replace `<ngrok-url>` with the
   tunnel value):

   ```bash
   ngrok http 3000
   curl https://<ngrok-url>/widget.js
   ```

The static files live in `app/static/`, so additional assets can be added without
modifying the FastAPI application.

### Embedding the chatbot widget

Any external site can load the chat widget by embedding the script and providing
an application-issued `data-embed-token`:

```html
<script src="https://<your-domain>/widget.js" data-embed-token="XYZ"></script>
```

The script injects a floating launcher button that opens a sandboxed iframe
pointing to `/embed/chat?token=<data-embed-token>`. The FastAPI service now
serves that route with a placeholder chat surface that echoes the provided
token so integrators can verify that the full round-trip works end to end.
For a local demo open `examples/embed.html` in your browser after starting the
FastAPI server.

### LLM Konfiguration & CLI

Die Pipeline unterstützt mehrere Provider. Ohne weitere Parameter wird OpenAI mit dem Modell
`gpt-4.1-mini` verwendet (sofern ein API-Key vorhanden ist). Folgende Umgebungsvariablen sind relevant:

| Provider  | Pflichtvariablen | Optionale Variablen |
|-----------|------------------|---------------------|
| OpenAI    | `OPENAI_API_KEY` | `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL` |
| Gemini    | `GEMINI_API_KEY` | `GEMINI_BASE_URL`, `GEMINI_MODEL` |
| DeepSeek  | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` |
| Groq      | `GROQ_API_KEY` | `GROQ_BASE_URL`, `GROQ_MODEL` |
| Ollama    | – (lokaler Dienst) | `OLLAMA_HOST`, `OLLAMA_MODEL` |

Neben Provider und Modell können nun auch **Renewal-Mode**, **CSS-Framework** und eine freie **Theme-Style**-Beschreibung angegeben werden.

| Option | Beschreibung |
|--------|--------------|
| `--renewal-mode {full,text-only,seo-only,design-only}` | Steuert, welche Agenten laufen: `full` aktiviert alle Schritte, `text-only` führt nur das Rewrite (A11) aus, `design-only` überspringt den Rewrite und fokussiert auf Theming/Build, `seo-only` liefert ausschließlich SEO/Metadata-Optimierungen. |
| `--css-framework <name>` | Beliebiger Framework-/Library-Name. Bekannte Werte wie `bootstrap`, `tailwind` oder `vanilla` verwenden hinterlegte Templates, unbekannte Werte werden als Custom-Framework in Theming/Builder weitergereicht. |
| `--theme-style "…"` | Komma-separierte Stilhinweise (Farben, Formen, Effekte, Typografie). Diese Hinweise landen direkt beim Theming- und Builder-Agenten. |
| `--navigation-style {horizontal,vertical,mega-menu}` | Steuerung des Layouts für die generierte Navigation. |
| `--navigation-location {top-left,top-right,top-center,side-left,side-right,footer}` | Position des Navigationscontainers (Header, Sidebar oder Footer). |
| `--navigation-dropdown {none,hover,click}` | Dropdown-Verhalten für mehrstufige Menüs. |
| `--navigation-dropdown-default {open,closed}` | Startzustand des Burger-/Dropdown-Menüs. |
| `--navigation-config '{"location":"top-right","dropdown":"hover","sticky":true}'` | Freiform-JSON, das zusätzliche Navigationseigenschaften (z. B. `sticky`, `brand_label`, `mega_columns`) überschreibt. |
| `--navigation-logo <url>` | Optionales Logo, das in der Navigation eingeblendet wird. |

Beispiele für den CLI-Aufruf (Modell optional, ansonsten greift der Default pro Provider):

```bash
# OpenAI (Default)
python renewal.py https://www.physioheld.ch --llm openai --llm-model gpt-4o-mini

# Lokale Ollama-Instanz
python renewal.py https://www.physioheld.ch --llm ollama --llm-model llama3.2

# Anthropic
python renewal.py https://www.physioheld.ch --llm anthropic --llm-model claude-3-7-sonnet-latest

# Google Gemini
python renewal.py https://www.physioheld.ch --llm gemini --llm-model gemini-1.5-pro

# DeepSeek
python renewal.py https://www.physioheld.ch --llm deepseek --llm-model deepseek-chat

# Groq
python renewal.py https://www.physioheld.ch --llm groq --llm-model llama3-70b-8192

# Text-Only Optimierung
python renewal.py https://www.physioheld.ch --renewal-mode text-only --theme-style "klar, sachlich"

# Navigation konfigurieren (Bootstrap, Top-Right)
python renewal.py https://www.physioheld.ch \
  --css-framework bootstrap \
  --navigation-style horizontal \
  --navigation-location top-right \
  --navigation-dropdown hover \
  --navigation-dropdown-default closed

### Navigation Builder & Advanced Konfiguration

Der neue `NavigationBuilderAgent` übernimmt das vom A9-Agent gelieferten `NavModel` und erzeugt ein vollständiges `NavigationBundle` mit HTML-, CSS- und JS-Snippets. Die Ausgabe landet als `navigation_bundle.json` im `sandbox/`-Ordner und wird automatisch vom Builder eingebunden.

* **Framework aware**: Für `bootstrap`, `tailwind` und `vanilla` werden passende Markups generiert (Dropdowns, Mega-Menüs, Hamburger-Menü unter 768 px).
* **Positionierung**: `top-left`, `top-right`, `side-left`, `footer` u. v. m. steuern Sticky/Off-Canvas-Verhalten.
* **Dropdown-Steuerung**: `none`, `hover`, `click` inkl. Default-State (`open`/`closed`).
* **Branding**: Logo via `--navigation-logo` oder `navigation_config.logo` plus automatisch normalisierte Labels.

Die Struktur des Bundles:

```json
{
  "location": "top-right",
  "style": "horizontal",
  "dropdown": "hover",
  "dropdown_default": "closed",
  "items": [
    {"label": "Home", "href": "/", "children": []},
    {"label": "Services", "href": "/services", "children": []}
  ],
  "sticky": true,
  "logo": "https://cdn.example.com/logo.svg"
}
```

Zusätzliche Optionen können über `--navigation-config` gesetzt werden. Beispiel:

```bash
--navigation-config '{"sticky": true, "brand_label": "Physioheld", "mega_columns": 3}'
```

Die Schlüssel `style`, `location`, `dropdown` und `dropdown_default` aus der CLI haben Vorrang, können aber im JSON erneut überschrieben werden.

# Design-Refresh ohne Copy-Änderungen
python renewal.py https://www.physioheld.ch --renewal-mode design-only --css-framework material --theme-style "modern, blue/white, rounded buttons, shadow"

# SEO-Fokus
python renewal.py https://www.physioheld.ch --renewal-mode seo-only --theme-style ""
```

Alle Artefakte landen in `sandbox/`, inklusive Crawl-Daten, Analysen, Plan, Rewrite,
Theming-Tokens, einer vollständigen Kopie der Originalseiten (`sandbox/original/`),
dem mehrseitigen Build (`sandbox/newsite/`), Diff-Preview und Angebot.

## Inkrementeller Post-Edit Workflow

Der neue `PostEditPipeline`-Flow speichert den kompletten `SiteState` in einer SQLite-Datenbank
(`sandbox/state.db`) und berechnet bei jedem Aufruf nur die wirklich nötigen Änderungen.
Post-Edits lassen sich dadurch iterativ anwenden, ohne Crawl und Full-Build erneut durchlaufen
zu müssen.

### Neue CLI-Flags

| Flag | Beschreibung |
|------|--------------|
| `--user-prompt "..."` | Freitext-Instruktionen für Planner & Agents (Design, SEO, Copy, CTA, Navigation …). |
| `--apply-scope css,nav` | Kommagetrennte Scopes (`all`, `css`, `seo`, `images`, `logo`, `content`, `nav`, `head`). |
| `--no-recrawl` | Überspringt A1–A3, wenn bereits Crawl-Artefakte vorliegen. |

Beispiel: nur CSS & Navigation aktualisieren

```bash
python renewal.py https://www.physioheld.ch \
  --no-recrawl \
  --apply-scope css,nav \
  --user-prompt "Modern blue/white palette, rounded buttons, soft shadow, navigation top-right" \
  --css-framework bootstrap
```

### ChangeSet JSON

Der DeltaPlanner liefert deterministische Operationen:

```json
{
  "targets": ["css", "nav"],
  "operations": [
    {"type": "css.tokens.update", "payload": {"path": "theme.tokens", "tokens": {"palette": {"primary": "blue"}}}},
    {"type": "nav.layout.update", "payload": {"location": "top-right", "dropdown": "hover", "default": "closed"}}
  ]
}
```

### SiteState Schema (persistiert in SQLite)

```json
{
  "nav": {"items": [...], "layout": {...}, "html": "..."},
  "head": {"title": "...", "meta": {...}, "links": [...]},
  "pages": [
    {
      "path": "/",
      "blocks": [{"id": "hero", "text": "...", "meta": {...}}],
      "seo": {...},
      "content_hash": "..."
    }
  ],
  "theme": {"tokens": {...}},
  "css_bundle": {"raw": "...", "tokens": {...}, "framework": "bootstrap"},
  "assets": {"images": [...], "logo": {...}},
  "seo": {"meta": {...}, "ld_json": {...}},
  "build": {"latest_dist": "sandbox/newsite-20240618-153000", "history": [...]}
}
```

### Wiederholte Post-Edits

- `--no-recrawl` nutzt die gespeicherte `SiteState` statt neu zu crawlen.
- Jede Operation wird gehasht; identische ChangeSets werden übersprungen und verweisen
  lediglich auf die letzte Preview.
- Der Builder erzeugt nur geänderte Dateien, unveränderte HTMLs werden aus dem letzten Build kopiert.

### Preview & lokale Links

- Jede Ausführung legt einen HTML-Diff unter `sandbox/preview/<id>/index.html` an.
- Der CLI-Output nennt den Pfad (`Preview ready: sandbox/preview/abcd1234/index.html`).
- Bei Bedarf kann derselbe Pfad über einen lokalen Static-Server ausgespielt werden
  (z. B. `http://127.0.0.1:8000/preview/abcd1234/`).

Zusätzlich wird die komplette CLI-Konfiguration als `sandbox/config.json` abgelegt, so dass spätere API-Calls die gleichen Settings übernehmen können.

**Erweiterungstipps:**

* Neue Frameworks lassen sich über `--css-framework` direkt anfragen. Soll ein Preset ergänzt werden, kann in `BuilderAgent` eine passende CDN-Konfiguration hinterlegt werden.
* Stilhinweise funktionieren am besten als kurze Komma-Liste: Farben („modern blue/white“), Formen („rounded buttons“), Effekte („shadow, glassmorphism“) oder Typografie („serif, elegant“).
* Eigene Renewal-Modes lassen sich über zusätzliche Scopes im `RenewalConfig` und passende Planner-Regeln innerhalb der `PostEditPipeline` erweitern.

### MCP Server für LLMs

Das Skript `llm-mcp` startet einen Model Context Protocol Server, der zwei Tools und mehrere
Ressourcen zur Verfügung stellt:

```bash
llm-mcp
```

Tools:

- `llm.complete_text(provider, model, prompt, temperature?)`
- `llm.complete_json(provider, model, prompt, schema?, temperature?)`

Ressourcen:

- `llm://providers` – Übersicht aller Provider und Default-Modelle
- `llm://last/{provider}/{model}` – letzter Completion-Output
- `llm://trace/{id}` – vollständiger Trace inklusive Retries und Token-Nutzung

Die URIs orientieren sich an den MCP-Konventionen: `llm://trace/{id}` liefert den Trace
zum exakten Identifier (z. B. `llm://trace/abc123` → Trace `abc123`). Über
`llm://last/{provider}/{model}` wird der zuletzt gespeicherte Trace für das Paar aus
Provider und Modell geladen (z. B. `llm://last/openai/gpt-4o`).

Die Antworten sind strukturierte Pydantic-Modelle. Fehlgeschlagene JSON-Parsings führen
zu einem zweiten Versuch mit strengeren Instruktionen; bei erneutem Fehlschlag wird der
Trace persistiert und eine aussagekräftige Fehlermeldung ausgelöst.

`llm.complete_json` nutzt – je nach Provider – entweder den nativen JSON-Mode (falls vom
Client unterstützt) oder erzwingt über einen System-Prompt eine strikt valide JSON-Ausgabe.
Bei Parsing- oder Validierungsfehlern wird automatisch mit einer verstärkten Instruktion
erneut versucht, bevor ein Fehler propagiert wird. Sämtliche Aufrufe werden mit Prompt,
Rohantwort und Metadaten im Trace-Log festgehalten.

Alle Artefakte landen in `sandbox/`, inklusive Crawl-Daten, Analysen, Plan, Rewrite,
Theming-Tokens, einer vollständigen Kopie der Originalseiten (`sandbox/original/`),
dem mehrseitigen Build (`sandbox/newsite/`), Diff-Preview und Angebot.

## Legacy Demo-Hinweise

Die ursprünglichen Demo-Schritte (lokaler HTTP-Server, manuelles Anstoßen) bleiben hier
aus historischen Gründen dokumentiert. Für das neue PoC genügt der oben beschriebene
`renewal.py`-Aufruf; dieser Abschnitt wird in einer späteren Iteration bereinigt.



## Testing

1. `pip install -r requirements.txt`
2. `pip install pytest pytest-cov`
3. `pytest --cov=webrenewal tests/`

Die Tests nutzen die Dummy-Daten unter `tests/fixtures/` (HTML-Seiten und JSON-Artefakte), um deterministische Ergebnisse zu
ermöglichen. Die Coverage-Reports werden im Terminal sowie unter `htmlcov/index.html` abgelegt.

### Edge-Cases & SOLID-Teststruktur

* **Single Responsibility**: Jede Testdatei deckt genau ein Modul bzw. einen Agenten ab, wodurch Ursachenanalyse vereinfacht wird.
* **Open/Closed & Liskov**: Agenten werden über austauschbare Stubs/Fakes getestet, sodass Erweiterungen ohne Testbrüche möglich
  sind.
* **Interface Segregation**: Fixtures in `tests/conftest.py` kapseln Dummy-Daten (HTML, JSON, LLM-Antworten), wodurch Tests nur die
  benötigten Daten konsumieren.
* **Dependency Inversion**: Externe Systeme (LLMs, HTTP) werden konsequent gemockt, um deterministische, offline lauffähige
  Szenarien abzudecken – inkl. Timeouts und Fehlerpfade.

