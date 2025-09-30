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

Pipeline ausführen (Beispiel PhysioHeld):

```bash
python renewal.py https://www.physioheld.ch --log-level INFO
```

Alle Artefakte landen in `sandbox/`, inklusive Crawl-Daten, Analysen, Plan, Rewrite,
Theme-Tokens, Build (`sandbox/newsite/index.html`), Diff-Preview und Angebot.

## Legacy Demo-Hinweise

Die ursprünglichen Demo-Schritte (lokaler HTTP-Server, manuelles Anstoßen) bleiben hier
aus historischen Gründen dokumentiert. Für das neue PoC genügt der oben beschriebene
`renewal.py`-Aufruf; dieser Abschnitt wird in einer späteren Iteration bereinigt.


