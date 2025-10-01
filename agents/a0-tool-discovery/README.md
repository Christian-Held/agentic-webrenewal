# Agent A0 – Tool-Discovery

---

## 1. Übersicht / Rolle im System

Der **Tool-Discovery-Agent (A0)** ist der erste Baustein der gesamten Renewal-Pipeline. Seine Aufgabe ist es, die verfügbaren **MCP-Server und -Tools** zu identifizieren, zu bewerten und für die weiteren Agenten als **strukturierte ToolCatalog-Ausgabe** bereitzustellen.

Das System ist modular aufgebaut. Daher ist es kritisch, dass alle weiteren Services von Beginn an mit den richtigen Tool-Schnittstellen arbeiten. A0 bildet damit die Grundlage für eine **deterministische, reproduzierbare und transparente Auswahl**.

Die Discovery umfasst:

* das Scannen definierter Quellen (z. B. `https://mcp.so/`, `https://glama.ai/mcp/`, `https://smithery.ai/`, Hugging Face Blogposts)
* das Parsen und Extrahieren der relevanten Tool-Beschreibungen
* das Bewerten der Tools anhand definierter Kriterien (Passung zur Architektur, Reife, Lizenz, DSGVO etc.)
* das Erstellen einer konsolidierten **ToolCatalog.json**
* optional: das Generieren von **Usage-Snippets (Code)** als Markdown-Dateien zur direkten Integration

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **sources[]**: Liste von URLs, die durchsucht werden sollen

  ```json
  {
    "sources": [
      "https://mcp.so/",
      "https://glama.ai/mcp/",
      "https://smithery.ai/",
      "https://huggingface.co/blog/LLMhacker/top-11-essential-mcp-libraries"
    ]
  }
  ```
* optional: **Filterkriterien** (Kategorie, Sprache, Lizenz)

### Ausgabe

* **ToolCatalog.json**

  ```json
  {
    "tools": [
      {
        "category": "browser",
        "name": "@playwright/mcp",
        "homepage": "https://github.com/playwright-community/mcp",
        "runtime": "Node.js",
        "score": {
          "fit": 5,
          "maturity": 5,
          "license": 5,
          "compliance": 4,
          "performance": 4,
          "docs": 4,
          "interop": 3,
          "observability": 3
        },
        "total": 33
      },
      {
        "category": "filesystem",
        "name": "@modelcontextprotocol/server-filesystem",
        "homepage": "https://github.com/modelcontextprotocol",
        "runtime": "Node.js",
        "score": { ... },
        "total": 31
      }
    ]
  }
  ```

* **Markdown-Snippets** (z. B. `mcps/file-tools.md`) mit Usage-Examples

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **HTTP/Fetch**: für das Abrufen der Quellseiten
* **HTML-Parser**: `lxml`, `BeautifulSoup` oder Äquivalent
* **Regex**: zum Extrahieren von Toolnamen, GitHub-Repos, Installationsbefehlen
* **JSON-Schema-Validator**: Sicherstellung, dass `ToolCatalog` gültig ist
* **Scoring-Engine**: einfache Gewichtung (Passung=3, Reife=2, Lizenz=2, Sicherheit=2, Performance=2, Dokumentation=1, Interop=1, Observability=1)

### Algorithmen

* **Scoring**: gewichtete Summe → Gesamtpunktzahl
* **Normalisierung**: Deduplizieren von Tools aus verschiedenen Quellen
* **Kategorisierung**: automatische Einordnung (browser/fetch/filesystem/memory/…)

---

## 4. Externe Abhängigkeiten

* **MCP-Server selbst** (z. B. `@playwright/mcp`, `mcp-server-fetch`, `mcp-memory-libsql`) – werden nicht gestartet, aber ihre Existenz und Dokumentation wird referenziert
* **OpenAI LLM** (optional) für Text-Normalisierung und Klassifizierung der Toolbeschreibungen in definierte Kategorien
* **Quellen-APIs oder Websites**:

  * [https://mcp.so/](https://mcp.so/)
  * [https://glama.ai/mcp/](https://glama.ai/mcp/)
  * [https://smithery.ai/](https://smithery.ai/)
  * Hugging Face Blogartikel

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * Konfiguration laden (`sources[]`)
   * Sandbox-Verzeichnis für Outputs anlegen

2. **Fetching**

   * Jede Source via HTTP oder Browser-Render abrufen
   * HTML/Text speichern (Archivzwecke)

3. **Parsing**

   * Toolnamen und Beschreibungen extrahieren
   * Links zu GitHub/NPM/PyPI erkennen
   * Runtimes (Node.js, Python, Java) identifizieren

4. **Classification**

   * Tools anhand von Schlüsselwörtern/Kontext einer Kategorie zuordnen (z. B. „playwright“ → Browsing)
   * LLM-basierte Validierung (bei unsicheren Fällen)

5. **Scoring**

   * Jeder Dimension (Fit, Reife, Lizenz, etc.) wird ein Wert 1–5 zugewiesen
   * Gewichtung anwenden, Gesamtscore berechnen

6. **Output Generation**

   * ToolCatalog.json schreiben
   * Markdown-Snippets mit Usage-Beispielen generieren

7. **Validation**

   * JSON-Schema prüfen
   * bei Fehlern: Retry oder Fallback

---

## 6. Quality Gates & Non-Functional Requirements

* **Richtigkeit**: alle gefundenen Tools müssen existieren und installierbar sein
* **Reproduzierbarkeit**: wiederholter Lauf mit gleichen Quellen liefert gleiche Ergebnisse
* **Vollständigkeit**: min. 95 % der bekannten Core-MCPs müssen erkannt werden
* **Performance**: Discovery < 5 Minuten für definierte Quellen
* **Compliance**: nur Tools mit offener Lizenz (MIT, Apache, BSD) werden vorgeschlagen
* **Security**: keine Links zu obskuren oder unsicheren Quellen
* **Resilienz**: Quellen-Timeouts werden mit Retries und Fallback-Listen abgefangen

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: als Microservice im Container (Docker/Kubernetes)
* **Scaling**: Discovery ist I/O-lastig, horizontale Skalierung über parallele Worker
* **Frequency**: typischerweise wöchentlich oder bei Projekt-Setup auszuführen
* **Persistence**: ToolCatalog wird in Memory MCP (LibSQL) oder Filesystem persistiert
* **Observability**: Logs (Start, gefundene Tools, Scores), Metriken (Anzahl Tools, Laufzeit, Fehlerquote)

---

## 8. Erweiterungspotenzial & offene Fragen

* **Automatisierte Benchmarks**: Tools nicht nur beschreiben, sondern testweise starten und `list_tools()` validieren
* **Community-Signale**: GitHub Stars, NPM/PyPI-Downloads in Scoring aufnehmen
* **Security-Feed**: Tools mit bekannten CVEs markieren
* **Validator-Agent**: LLM-Vergleich von Discovery-Ergebnissen → Qualitätssteigerung
* **Frage**: Soll Discovery auch Tools für Spezialfälle (z. B. Audio, Video, ML) vorschlagen, oder nur die Kern-MCPs (Browsing, Fetch, Filesystem, Memory)?

---

📄 **Fazit**:
A0 ist ein klar abgrenzbarer Service, der in sich abgeschlossen entwickelt werden kann. Egal ob in **Python (asyncio, aiohttp, bs4)** oder **Java (Spring Boot, Jsoup, Kafka)** – die Hauptaufgaben sind Fetch → Parse → Score → Catalog.
Die Outputs (`ToolCatalog.json` + `.md` Snippets) bilden die Grundlage für alle weiteren Agenten.
---

## Aktueller Implementierungsstand

**Bereits funktionsfähig**

- Statische Werkzeugliste mit Playwright-, Fetch-, Filesystem- und LibSQL-MCP-Einträgen für den Pipeline-Start.
- Logging dokumentiert die Anzahl der zusammengestellten Tools.

**Offene Schritte bis zur Production-Readiness**

- Automatisches Discovery aus Projektkonfiguration oder externen Registern.
- Health-Checks und Capability-Metadaten zur Laufzeit prüfen.

