# Agent A4 – Tech-Fingerprint

---

## 1. Übersicht / Rolle im System

Der **Tech-Fingerprint Agent (A4)** identifiziert die zugrundeliegende **Technologie einer Website**. Ziel ist es, präzise und nachvollziehbar zu bestimmen:

* Welches **CMS** oder Framework wird genutzt?
* Welche **JavaScript-Libraries** laufen im Frontend?
* Welche **CSS-Frameworks** oder UI-Libraries sind eingebunden?
* Welche **Servertechnologien** oder Header-Hinweise existieren?

Der Agent ergänzt A3 (Inhalte) um eine **technologische Landkarte**, die später für **Renewal-Planung (A10)** und **Migration (A13 Builder)** essenziell ist.

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **CrawlResult.json** (aus A2)

  ```json
  {
    "pages": [
      {
        "url": "https://www.example.com/",
        "status": 200,
        "html": "<html><head><meta name='generator' content='WordPress 6.1' />...</head></html>",
        "headers": {"server": "nginx", "x-powered-by": "PHP/7.4"},
        "scripts": [{"src": "/wp-includes/js/jquery/jquery.min.js"}],
        "links": ["/wp-content/themes/twentytwentyone/"],
        "rendered": true
      }
    ]
  }
  ```

### Ausgabe

* **TechFingerprint.json**

  ```json
  {
    "framework": {
      "name": "WordPress",
      "version": "6.1",
      "evidence": ["/wp-content/", "meta generator=WordPress"]
    },
    "jsLibs": [
      {"name": "jQuery", "version": "3.6.0", "src": "/wp-includes/js/jquery/jquery.min.js"}
    ],
    "cssFramework": {
      "name": "Bootstrap",
      "version": "3.3.7",
      "evidence": ["link href=/bootstrap.min.css"]
    },
    "server": {"type": "nginx", "language": "PHP/7.4"}
  }
  ```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **Parser**: BeautifulSoup / lxml zum Scannen nach `<script>`, `<link>`, `<meta>`
* **Fingerprint-Datenbank**: YAML/JSON-Signaturen, ähnlich Wappalyzer
* **Regex-Patterns**: für Versionsstrings (`jquery-([\d\.]+)\.js`)
* **Header-Parser**: Analyse von `server`, `x-powered-by`, `set-cookie`
* **Optional**: Hash- oder Pattern-Matching von Assets (z. B. `wp-content`, `drupal.js`)

### Algorithmen

* **Meta-Tag Analyse** (`generator`, `framework`)
* **Pfad-Muster** (z. B. `/wp-content/`, `/sites/all/modules/`)
* **Lib Detection** (jQuery, React, Angular, Vue über `window.`-Objekte oder Dateinamen)
* **Version Parsing** (Regex in Script- und CSS-Dateinamen)
* **Cross-Validation** (mehrere Evidenzen für hohe Sicherheit)

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Speichern der JSON-Ergebnisse
* **Fetch MCP**: Zusätzliche Abfragen (z. B. `robots.txt`, Version.txt von CMS, CDN-Assets)
* **Playwright MCP**: Für dynamische Erkennung von `window.React`, `ng-version`, `Vue.config`
* **Memory MCP**: Persistenz historischer Tech-Fingerprints für Delta-Analysen

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * CrawlResult laden
   * Liste bekannter Patterns initialisieren

2. **CMS/Framework Detection**

   * Suche nach Meta `generator`
   * Prüfen von Pfaden (`/wp-content/`, `/typo3/`, `/sites/default/`)
   * Heuristiken aus Assets

3. **JavaScript Libs**

   * Scannen aller `<script src>`
   * Regex für bekannte Libs (`jquery`, `react`, `vue`, `angular`)
   * Optional: Ausführung in Browser, Dump von `window`-Properties

4. **CSS Frameworks**

   * `<link rel=stylesheet>` analysieren
   * Muster für Bootstrap, Tailwind, Foundation etc.

5. **Server/Backend**

   * Header-Analyse: `server`, `x-powered-by`, Cookies (`PHPSESSID`, `ASP.NET`)
   * TLS-Zertifikate (Issuer, Technologiehinweise)

6. **Version Extraction**

   * Regex auf Dateinamen (`bootstrap-3.3.7.min.css`)
   * Meta-Generator-Signaturen

7. **Confidence Scoring**

   * Evidenzen sammeln
   * Score 0–1 pro Technologie

8. **Output**

   * TechFingerprint.json speichern

---

## 6. Quality Gates & Non-Functional Requirements

* **Genauigkeit**: ≥ 85 % für gängige CMS/Frameworks
* **Robustheit**: funktioniert auch bei minified/obfuscated HTML
* **Transparenz**: Jede Erkennung mit „evidence“ begründen
* **Performance**: ≤ 1 Sekunde pro Seite (ohne Playwright), ≤ 5 Sekunden mit dynamischem Eval
* **Updatability**: Fingerprint-Datenbank muss versionierbar und erweiterbar sein

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: als Microservice (Python, Java oder Node möglich)
* **Scaling**: horizontal, parallele Scans pro Domain
* **Persistence**: Memory MCP für Deltas (z. B. „WordPress 5.9 → 6.1“)
* **Observability**: Logs mit Evidenzen und Scores, Metriken: Trefferquote, Analysezeit

---

## 8. Erweiterungspotenzial & offene Fragen

* **Framework Minor Versions**: Sollen Patch-Level erfasst werden (z. B. Bootstrap 5.3.1) oder nur Major?
* **Security-Check Integration**: Soll A4 schon bekannte CVEs für erkannte Versionen melden (z. B. jQuery 1.12.4 unsicher)?
* **SPAs**: Viele Frameworks (React/Vue) nur im Runtime erkennbar → Browser notwendig
* **Custom Frameworks**: Wie mit Eigenentwicklungen umgehen? (nur als „unknown framework“ markieren?)

---

📄 **Fazit**:
A4 liefert eine **technologische Fingerprint-Karte** der Ziel-Website. Er bildet die Grundlage für alle späteren Empfehlungen, Upgrades und Sicherheitsbewertungen. Durch seine modulare Pattern-Datenbank kann er unabhängig von der Sprache (Python/Java/Node) implementiert werden.
---

## Aktueller Implementierungsstand

**Bereits funktionsfähig**

- Regex-basierte Heuristiken identifizieren gängige Frameworks wie Bootstrap, jQuery und WordPress.
- Speichert Evidenz-URLs zur Nachvollziehbarkeit.

**Offene Schritte bis zur Production-Readiness**

- Erweiterte Signaturen für moderne Frameworks und Build-Tool-Ketten.
- Korrelation mit HTTP-Headern und Asset-Hashes für höhere Genauigkeit.

