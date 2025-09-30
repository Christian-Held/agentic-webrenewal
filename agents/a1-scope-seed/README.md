# Agent A1 – Scope/Seed

---

## 1. Übersicht / Rolle im System

Der **Scope/Seed Agent (A1)** ist der zweite Baustein der Renewal-Pipeline. Seine Aufgabe ist es, aus einer gegebenen Domain oder URL den **Scope der Analyse** abzuleiten. Damit stellt er sicher, dass alle folgenden Schritte (Crawl, Analyse, Optimierung) zielgerichtet, ressourcenschonend und rechtlich sauber durchgeführt werden.

A1 arbeitet direkt nach der Tool-Discovery (A0) und beantwortet Fragen wie:

* Welche Start-URLs (Seeds) sollen gecrawlt werden?
* Welche Teile der Website sind in Scope (z. B. /leistungen), welche nicht (z. B. /admin, /login)?
* Welche Maximalgröße (Page-Limit) und Tiefe (Crawl-Depth) ist erlaubt?
* Müssen Robots.txt und Sitemaps beachtet werden?
* Welche Sprachen/Locales sind im Scope?

Das Ergebnis ist ein **ScopePlan**, ein formalisiertes JSON-Dokument, das die Basis für den Crawler (A2) darstellt.

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **Domain oder Root-URL**

  ```json
  {
    "root": "https://www.example.com"
  }
  ```
* optionale Parameter:

  * `maxPages`: int
  * `include[]`: Pfade, die eingeschlossen werden sollen
  * `exclude[]`: Pfade, die ausgeschlossen werden sollen
  * `respectRobots`: bool

### Ausgabe

* **ScopePlan.json**

  ```json
  {
    "root": "https://www.example.com",
    "maxPages": 200,
    "include": ["/", "/leistungen", "/kontakt"],
    "exclude": ["/admin", "/login"],
    "respectRobots": true,
    "locales": ["de-DE"],
    "sitemaps": [
      "https://www.example.com/sitemap.xml"
    ]
  }
  ```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **HTTP/Fetch**: Abruf von `robots.txt` und `sitemap.xml`
* **Parser**: XML-Parser für Sitemap-Auswertung, Regex für robots.txt
* **Language-Detection**: z. B. `langdetect`, CLD3 → für Sprach-/Locale-Erkennung
* **Validator**: JSON-Schema-Checker für ScopePlan

### Algorithmen

* **URL-Normalisierung**: Entfernen von Query-Params, Slashes, Session-IDs
* **Scope-Expansion**: Sitemap-URLs hinzufügen, die im Scope liegen
* **Scope-Reduction**: Exclude-Regeln anwenden (z. B. `/admin`)
* **Fallback**: Wenn keine Sitemap gefunden → heuristisch aus Navigation extrahieren (später A9)

---

## 4. Externe Abhängigkeiten

* **Fetch MCP**: um robots.txt, sitemap.xml und Startseite zuverlässig abzurufen
* **Filesystem MCP**: Speichern von ScopePlan.json
* **OpenAI LLM** (optional): für Klassifizierung, ob bestimmte Pfade wahrscheinlich nicht im Scope sind (z. B. `/wp-admin/`, `/cart/`)
* **Input vom Nutzer**: manuelle Präzisierungen sind möglich („max. 50 Seiten, /blog ausschließen“)

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * Eingabe-URL normalisieren (https vs. http, trailing slash)
   * Default-Werte setzen (`maxPages=200`, `respectRobots=true`)

2. **Fetch Robots.txt**

   * Regeln für Disallow/Allow auslesen
   * Wenn `respectRobots=true`, Filter entsprechend setzen

3. **Fetch Sitemap.xml**

   * URLs extrahieren, in ScopePlan aufnehmen
   * ggf. mehrere Sitemaps (Index-Sitemap) rekursiv folgen

4. **Heuristische Erweiterung**

   * Falls keine Sitemap → Links der Root-Page parsen (Navigation)
   * Basis-Include definieren (`/`, `/leistungen`, `/kontakt`)

5. **Locale Detection**

   * Lang-Attribut der Root-Page analysieren (`<html lang="de">`)
   * Fallback: LLM-gestützte Spracherkennung aus Textcontent

6. **Finalisierung**

   * ScopePlan.json erzeugen
   * Persistieren im Filesystem MCP und/oder Memory MCP

---

## 6. Quality Gates & Non-Functional Requirements

* **Korrektheit**: Alle Pfade müssen valide URLs sein
* **Vollständigkeit**: min. 90 % der relevanten Sitemaps/Pages sollen erkannt werden
* **Respekt vor Regeln**: Robots.txt immer berücksichtigen, außer explizit vom Nutzer übersteuert
* **Performance**: Erstellung des ScopePlans < 60 Sekunden für mittelgroße Seiten (≤ 10k URLs in Sitemap)
* **Erweiterbarkeit**: Einbindung von Multi-Locale (z. B. `/de/`, `/en/`) muss einfach möglich sein
* **DSGVO/Compliance**: keine private oder geschützte Bereiche (z. B. /login) crawlen

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Container-fähig, leichtgewichtig (nur Fetch, Parser, JSON Writer)
* **Scaling**: Scope-Erstellung ist nicht massiv parallel nötig, wird pro Domain 1× ausgeführt
* **Frequency**: bei jedem neuen Projekt oder bei Re-Scope (Website-Struktur hat sich geändert)
* **Observability**:

  * Logs: gefundene Sitemaps, Robots-Ergebnisse, Excludes
  * Metrics: Anzahl URLs im Scope, Laufzeit, Fehlerrate

---

## 8. Erweiterungspotenzial & offene Fragen

* **Adaptive Scope-Limits**: automatische Anpassung von `maxPages` an die Größe der Sitemap
* **Incremental Scope Updates**: nur neue URLs hinzufügen statt kompletten Scope neu zu bauen
* **Multi-Domain Handling**: Subdomains erkennen und optional in Scope aufnehmen
* **ML-Klassifizierung**: maschinelles Lernen, um automatisch irrelevante Bereiche (z. B. `/tracking/`, `/analytics/`) auszuschließen
* **Offene Frage**: Soll der Nutzer im GUI interaktiv Scope-Regeln bearbeiten können, oder bleibt A1 rein programmatisch?

---

📄 **Fazit**:
A1 ist ein schlanker, aber kritischer Microservice. Er definiert die Spielwiese für alle weiteren Agenten. Ob in **Python (aiohttp, lxml)** oder **Java (Spring Boot, Jsoup)**, die Logik bleibt dieselbe: **URL normalisieren → robots/sitemap evaluieren → Include/Exclude setzen → ScopePlan.json persistieren**.

