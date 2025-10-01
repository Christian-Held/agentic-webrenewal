# Agent A9 – Navigation

---

## 1. Übersicht / Rolle im System

Der **Navigation Agent (A9)** ist spezialisiert auf die **Analyse, Extraktion und Modellierung von Navigationsstrukturen** einer Website.
Er übernimmt die Rohdaten aus dem Crawler (A2) und ggf. dem Readability Agent (A3) und wandelt die vorhandenen Menüs, Breadcrumbs und interne Linkhierarchien in ein **strukturiertes Navigationsmodell (NavModel)** um.

Ziel: eine **vollständig maschinenlesbare Repräsentation der Website-Navigation** bereitzustellen, die für den **Builder (A13)** zur Generierung moderner, barrierefreier Menüs (inkl. ARIA, Breadcrumbs, Offcanvas) dient.

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **CrawlResult.json**
* Optional: **ContentExtract.json**

Beispiel:

```json
{
  "pages": [
    {
      "url": "https://www.example.com/",
      "html": "<html><body><nav><ul><li><a href='/leistungen'>Leistungen</a></li><li><a href='/kontakt'>Kontakt</a></li></ul></nav></body></html>"
    }
  ]
}
```

### Ausgabe

* **NavModel.json**

```json
{
  "root": {
    "id": "root",
    "label": "Start",
    "url": "/",
    "children": [
      {"id": "leistungen", "label": "Leistungen", "url": "/leistungen", "children": []},
      {"id": "kontakt", "label": "Kontakt", "url": "/kontakt", "children": []}
    ]
  },
  "breadcrumbs": {
    "/leistungen": ["Start", "Leistungen"],
    "/kontakt": ["Start", "Kontakt"]
  }
}
```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **Parser**: BeautifulSoup / lxml für `<nav>`, `<ul>`, `<ol>`, `<a>`
* **DOM Traversal**: Extraktion von Menühierarchien
* **Heuristiken**: Erkennung von Navigations-Elementen auch ohne `<nav>` (z. B. Footer-Links, Sidebar)
* **Breadcrumb Extractor**: Suche nach `<nav aria-label="breadcrumb">` oder `<ol class="breadcrumb">`
* **Graph-Bibliotheken**: zur Modellierung von Hierarchien

### Algorithmen

* **Link Classification**: interne vs. externe Links
* **Hierarchy Detection**: verschachtelte `<ul>`-Strukturen → Parent/Child
* **Breadcrumb Detection**: aus DOM und Schema.org (`BreadcrumbList`)
* **Deduplication**: mehrfach auftretende Menüs zusammenführen
* **Normalization**: Slugs generieren, IDs berechnen (`leistungen`, `kontakt`)

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Speichern von NavModel.json
* **Fetch MCP**: Nachladen von Sitemap/robots.txt zur Validierung der Navigationsstruktur
* **Playwright MCP (optional)**: für dynamische Menüs (JS-Dropdowns)
* **Memory MCP**: Speicherung historischer Navigationsmodelle → Delta-Vergleiche

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * CrawlResult laden
   * Root-URL bestimmen

2. **Menu Extraction**

   * `<nav>`-Elemente suchen
   * `<ul>/<li>/<a>` traversieren → Hierarchie abbilden
   * Fallback: Links im Header/Footer identifizieren

3. **Breadcrumb Extraction**

   * Suche nach `aria-label="breadcrumb"`
   * Suche nach `<script type="application/ld+json">` mit `"@type":"BreadcrumbList"`

4. **Hierarchy Normalization**

   * Slugs aus URLs generieren
   * Label bereinigen (Whitespace, Umlaute → Slugs)

5. **Cross-Validation**

   * Vergleich mit Sitemap.xml
   * Links in NavModel, die nicht in CrawlResult existieren → markieren

6. **Output**

   * NavModel.json generieren
   * Optional: nav.json für direkten Input in Builder (A13)

---

## 6. Quality Gates & Non-Functional Requirements

* **Vollständigkeit**: ≥ 95 % aller Top-Level-Links korrekt extrahiert
* **Hierarchie-Korrektheit**: Verschachtelungen müssen die visuelle Struktur widerspiegeln
* **Barrierefreiheit**: ARIA-Breadcrumbs, Skip-Links erkennen
* **Performance**: ≤ 1 Sekunde pro Seite
* **Erweiterbarkeit**: Mehrsprachige Menüs (z. B. `/de/`, `/en/`) abbildbar

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: als Microservice mit Parser-Libraries
* **Scaling**: parallele Verarbeitung mehrerer Seiten/Unterdomains
* **Persistence**: Memory MCP für Navigation-Historie („neue Menüpunkte hinzugefügt“)
* **Observability**:

  * Logs: Anzahl Menüpunkte, Breadcrumb-Treffer
  * Metrics: Δ in Menügröße (z. B. 12 → 20 Menüpunkte)
  * Alerts: fehlende Root-Navigation

---

## 8. Erweiterungspotenzial & offene Fragen

* **Mega Menüs**: Soll A9 auch komplexe Menüs mit Icons, Bildern extrahieren?
* **Context Menüs**: Erkennung dynamischer Menüs, die nur via Hover/JS sichtbar werden → Playwright nötig
* **Custom Navigation**: Wie umgehen mit SPAs, wo Menüs per JS dynamisch nachgeladen werden?
* **Breadcrumb Canonicalization**: Unterschiedliche Breadcrumbs pro Seite → welches ist „gültig“?

---

📄 **Fazit**:
A9 liefert die **Navigation Blueprint** einer Website. Damit kann der Builder (A13) eine **barrierefreie, konsistente Navigation** generieren. Zusammen mit A6 (SEO) und A5 (Accessibility) ist er ein zentrales Bindeglied für Usability und Ranking.

## Testing

* `pytest tests/unit/agents/test_navigation_agent.py -q`
* Testfälle prüfen verschachtelte Menüs sowie Fallback-Anker bei fehlenden `<nav>`-Elementen.
* Dummy-HTML ist unter `tests/fixtures/html/` abgelegt.

