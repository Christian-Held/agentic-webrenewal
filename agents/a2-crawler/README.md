# Agent A2 – Crawler

---

## 1. Übersicht / Rolle im System

Der **Crawler (A2)** ist das zentrale Modul für die Datenerhebung im Renewal-System. Er übernimmt den in **A1 (Scope/Seed)** definierten **ScopePlan** und führt darauf basierend einen vollständigen Crawl durch.

Seine Hauptaufgabe ist es, **alle relevanten Seiten, Assets und Metadaten** einer Website zuverlässig zu erfassen, sodass nachgelagerte Agenten (A3–A9) auf valide, konsistente Daten zugreifen können.

Wesentliche Eigenschaften:

* Unterstützung von **statischen und dynamischen Inhalten** (JS-Rendering via Playwright)
* Sammlung von **HTML, Headers, Assets (Bilder, CSS, JS), Links**
* Erkennung von **Fehlerseiten (404/500)**
* Speicherung aller Rohdaten in einem strukturierten JSON-Format (**CrawlResult**)

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **ScopePlan.json** (von A1 erzeugt)

  ```json
  {
    "root": "https://www.example.com",
    "maxPages": 200,
    "include": ["/", "/leistungen", "/kontakt"],
    "exclude": ["/admin", "/login"],
    "respectRobots": true,
    "locales": ["de-DE"]
  }
  ```

### Ausgabe

* **CrawlResult.json**

  ```json
  {
    "pages": [
      {
        "url": "https://www.example.com/",
        "status": 200,
        "headers": {
          "content-type": "text/html; charset=utf-8",
          "content-length": "5234"
        },
        "html": "<!doctype html><html>…</html>",
        "links": ["/leistungen","/kontakt"],
        "images": [
          {"src":"/img/hero.jpg","alt":"","bytes":820000,"format":"jpeg"}
        ],
        "scripts": [
          {"src":"/js/app.min.js","integrity":null}
        ],
        "rendered": true,
        "timestamp": "2025-09-26T11:00:00Z"
      }
    ]
  }
  ```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **HTTP/Fetch**: für schnelle HEAD/GET-Anfragen (z. B. kleine Assets, Robots.txt-Rechecks)
* **Playwright**: zum Rendern dynamischer Inhalte (SPAs, Lazy-Loading, JS-generierte DOMs)
* **Queue-System**: z. B. asyncio-Queue oder Kafka (bei Java: Spring Kafka Listener) → für paralleles Crawling
* **Parser**: BeautifulSoup/lxml für Linkextraktion
* **Rate-Limiter**: Verhindert Überlastung der Zielseite
* **Checksum/Hasher**: zur Erkennung von Duplicate Content

### Algorithmen

* **Frontier Management**: BFS/DFS über erlaubte Links, Respektierung von `maxPages`
* **Duplicate Detection**: Canonical-URLs + Checksums verhindern redundantes Crawlen
* **Render-Decision**: Heuristik entscheidet, ob Playwright-Rendering nötig ist (z. B. bei `<script src>` ohne sichtbaren Content)
* **Retry-Strategy**: Exponentielles Backoff bei 429/503

---

## 4. Externe Abhängigkeiten

* **Playwright MCP**: steuert Headless Chromium/Firefox/Webkit
* **Fetch MCP**: für schnelle HTTP-Requests
* **Filesystem MCP**: Speichern von CrawlResult.json und archivierten HTML-Seiten
* **Input vom Nutzer** (optional): Crawl-Strategie (z. B. nur bestimmte Unterverzeichnisse)

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * ScopePlan laden
   * Frontier mit Root-URL initialisieren

2. **Fetch Cycle**

   * URL aus Frontier entnehmen
   * Vorprüfung: Exclude-Regeln anwenden
   * HTTP-Request via Fetch MCP → Header + Body abrufen
   * Falls Content-Type `text/html` → Render-Decision

3. **Rendering** (optional)

   * Playwright öffnen
   * Seite laden, warten auf `networkidle`
   * DOM extrahieren (inkl. Shadow DOM)
   * Screenshots (optional für Preview-Agent)

4. **Parsing**

   * Links extrahieren und normalisieren
   * Bilder + Attribute (src, alt, Größe)
   * Scripts (src, inline code hash)
   * Stylesheets (src, inline length)

5. **Storage**

   * Ergebnisse als Page-Objekt in CrawlResult aufnehmen
   * Roh-HTML im Filesystem ablegen (`sandbox/raw/<hash>.html`)

6. **Iteration**

   * Neue Links in Frontier aufnehmen, solange `maxPages` nicht überschritten
   * Schleife bis Frontier leer oder Limit erreicht

7. **Finalisierung**

   * CrawlResult.json persistieren
   * Metadaten speichern (Laufzeit, Anzahl gefundener Seiten)

---

## 6. Quality Gates & Non-Functional Requirements

* **Abdeckung**: ≥ 95 % der in ScopePlan enthaltenen Seiten müssen erfasst werden
* **Respekt von Regeln**: Robots.txt, maxPages und Exclude-Regeln immer beachten
* **Performance**: Crawl von 200 Seiten ≤ 5 Minuten (bei 1MB/Page, mittlerer Latenz)
* **Schonung**: Rate-Limits respektieren (z. B. max. 5 parallele Requests, 500ms Delay)
* **Zuverlässigkeit**: Duplicate Detection, keine Endlosschleifen
* **Resilienz**: Fehlerhafte Seiten (404/500) werden markiert, aber blockieren nicht den Crawl
* **Transparenz**: Logs mit Crawled/Skipped/Errored URLs

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Microservice im Container, mit Playwright-Browser-Binaries gebundelt
* **Scaling**:

  * Horizontal → mehrere Crawler-Instanzen pro Projekt
  * Vertikal → parallele Browser-Sessions pro Instanz
* **Queueing**: Kafka-Topic `crawl.request` / `crawl.result` (bei verteiltem Betrieb)
* **Observability**:

  * Metrics: Pages crawled/sec, Error Rate, Avg Latency
  * Tracing: OpenTelemetry-Spans pro URL
* **Persistence**: CrawlResult im Filesystem oder Memory MCP

---

## 8. Erweiterungspotenzial & offene Fragen

* **Adaptive Crawling**: Priorisierung wichtiger Seiten (hohes Traffic-Potential, viele interne Links)
* **Incremental Crawling**: nur geänderte Seiten neu laden, Delta-Updates speichern
* **Media Focus**: optionale Tiefenanalyse für Bilder/Videos (Auflösung, Exif, Lizenzhinweise)
* **Preview Assets**: Screenshots in CrawlResult einbetten (für direkte Vergleiche)
* **Offene Frage**: Soll der Crawler aggressiv auf Single-Page-Apps eingehen (alle States simulieren), oder nur initialen DOM?

---

📄 **Fazit**:
A2 ist ein ressourcenintensiver, aber hochkritischer Microservice. Ohne valide Crawl-Daten sind nachgelagerte Analysen (SEO, A11y, Security) wertlos. Die klare Trennung von **Fetch (leichtgewichtig)** und **Render (schwergewichtig)** ist essenziell, um Skalierung und Effizienz zu gewährleisten.
---

## Aktueller Implementierungsstand

**Bereits funktionsfähig**

- Breitensuche über HTML-Seiten mit Link-Normalisierung und Domain-Filter.
- Maximale Seitenausbeute per CLI konfigurierbar.

**Offene Schritte bis zur Production-Readiness**

- JavaScript-Rendering und Asset-Download für komplexe SPAs.
- Adaptive Crawl-Strategien (Priorisierung, Rate-Limiting, Robots-Compliance).

