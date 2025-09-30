# Agent A6 – SEO (Search Engine Optimization)

---

## 1. Übersicht / Rolle im System

Der **SEO Agent (A6)** analysiert die Inhalte einer Website (aus A2: CrawlResult und A3: ContentExtract) im Hinblick auf **Suchmaschinenoptimierung**.
Ziel: systematische Prüfung und Erkennung von SEO-Schwachstellen und -Potenzialen. A6 liefert konkrete Findings und Kennzahlen, die später in den **Renewal Plan (A10)** und das **Angebotsdokument (A15)** einfließen.

Während A3 für Text-Extraktion zuständig ist, setzt A6 darauf auf und überprüft Struktur, Metadaten und interne Verlinkung.

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **CrawlResult.json**
* **ContentExtract.json**

Beispiel:

```json
{
  "pages": [
    {
      "url": "https://www.example.com/",
      "title": "Beispiel",
      "headings": ["Willkommen"],
      "text": "Unsere Leistungen…",
      "html": "<html><head><title>Beispiel</title><meta name='description' content=''></head></html>"
    }
  ]
}
```

### Ausgabe

* **SEOReport.json**

```json
{
  "issues": [
    {
      "id": "missing-meta-description",
      "where": ["/", "/leistungen"]
    },
    {
      "id": "no-canonical",
      "where": ["/"]
    },
    {
      "id": "duplicate-title",
      "where": ["/leistungen", "/angebot"]
    }
  ],
  "sitemap": {
    "found": true,
    "urls": 120
  },
  "linking": {
    "internalLinks": 85,
    "brokenLinks": ["https://old.example.com/page-x"]
  },
  "schemaOrg": {
    "detected": ["LocalBusiness", "BreadcrumbList"],
    "missing": ["FAQPage"]
  }
}
```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **Parser**: BeautifulSoup/lxml zum Analysieren von `<title>`, `<meta>`, `<link rel="canonical">`
* **Sitemap-Parser**: `sitemap-parser` oder eigene XML-Auswertung
* **Link-Checker**: HTTP-HEAD-Anfragen (Fetch MCP) zur Validierung interner/externer Links
* **Schema.org Detection**: JSON-LD-Blöcke im `<script type="application/ld+json">` parsen
* **Duplicate Detection**: Hashing von Titles, Meta-Descriptions

### Algorithmen

* **Meta-Check**: Prüfen, ob jede Seite Title/Description hat, ob Länge passt
* **Canonical-Check**: `<link rel="canonical">` vorhanden?
* **Sitemap-Existenz**: /sitemap.xml, robots.txt → Einträge zählen
* **Internal Linking**: Linkgraph erstellen, Broken Links per Fetch prüfen
* **Schema.org**: vorhandene Typen extrahieren, fehlende empfehlen

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Speichern der SEOReports
* **Fetch MCP**: Abfragen von /robots.txt, /sitemap.xml, Broken Links
* **Playwright MCP (optional)**: DOM nach dynamisch erzeugten Metadaten durchsuchen
* **Memory MCP**: Delta-Analyse zwischen Scans („Meta-Description ergänzt am 2025-09-01“)

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * CrawlResult & ContentExtract laden
   * Liste aller URLs erstellen

2. **Meta-Checks**

   * `<title>` prüfen: Länge 30–65 Zeichen, keine Duplicates
   * `<meta name=description>` prüfen: Länge 50–160 Zeichen, keine Leere

3. **Canonical & Robots**

   * Prüfen auf `<link rel=canonical>`
   * robots.txt analysieren (Disallow-Regeln, Sitemap-Hinweis)

4. **Sitemap Parsing**

   * /sitemap.xml laden
   * Anzahl URLs zählen
   * Vergleichen mit gecrawlten Seiten

5. **Link-Analyse**

   * Alle internen Links sammeln
   * Broken Links via Fetch prüfen
   * Link-Graph-Analyse (孤立 Pages identifizieren)

6. **Schema.org Analyse**

   * JSON-LD Blöcke auslesen
   * Typen (LocalBusiness, FAQPage, BreadcrumbList) erkennen
   * Fehlende Typen als Empfehlung

7. **Scoring**

   * Score 0–100 pro Kategorie (Meta, Canonical, Links, Schema.org)
   * Aggregiert in Gesamt-SEO-Score

8. **Output**

   * SEOReport.json schreiben

---

## 6. Quality Gates & Non-Functional Requirements

* **Coverage**: Alle Seiten aus CrawlResult prüfen
* **Performance**: ≤ 2 Sekunden pro Seite (ohne externe Requests)
* **Genauigkeit**: Broken Links nur mit HEAD/GET validieren, keine False Positives
* **Erweiterbarkeit**: Neue SEO-Regeln leicht hinzufügbar
* **Output**: Jede Issue mit ID, Beschreibung, betroffenen URLs

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Containerisierbarer Service (Python oder Java)
* **Scaling**: Parallel pro Domain oder pro 100 URLs
* **Persistence**: Memory MCP für SEO-Historie (z. B. „Meta-Descriptions hinzugefügt“)
* **Observability**: Logs mit Anzahl Issues, Score pro Kategorie, Broken Link Count

---

## 8. Erweiterungspotenzial & offene Fragen

* **Mobile SEO**: Soll A6 auch Mobile Rendering prüfen (Viewport, Mobile-Friendliness)?
* **PageSpeed**: Soll Performance (CLS, LCP, FID) Teil von SEO-Agent werden oder bei A7 Security/Performance?
* **Backlinks**: Externe Links analysieren (Ranking-Signal) → evtl. eigenes Modul?
* **Keyword Density**: Soll A6 Content-Analyse mit Keywords durchführen oder A11 Rewriter?

---

📄 **Fazit**:
A6 ist der **Suchmaschinen-Optimierer** im Agentensystem. Er macht die Website für Google & Co. sichtbar, sorgt für Meta-/Struktur-Vollständigkeit und liefert wertvolle Eingaben für Rewrites (A11) und Angebote (A15).
