# Agent A5 – Accessibility (A11y)

---

## 1. Übersicht / Rolle im System

Der **Accessibility Agent (A5)** prüft die gecrawlten Seiten (A2 → CrawlResult) automatisiert auf **Barrierefreiheit**.
Ziel: Systematische Erkennung von A11y-Verstößen nach **WCAG 2.1 / EN 301 549**.
A5 liefert sowohl einen **quantitativen Report** (Score, Anzahl Verstöße) als auch **detaillierte Findings** (z. B. fehlende ALT-Texte, Farbkontraste, ARIA-Fehler).

Dieser Agent stellt sicher, dass jede generierte Seite im Renewal-Prozess **mindestens A11y ≥ 95** erreicht (Quality Gate).

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **CrawlResult.json**

  ```json
  {
    "pages": [
      {
        "url": "https://www.example.com/",
        "status": 200,
        "html": "<html><head><title>Beispiel</title></head><body><img src='/hero.jpg'></body></html>",
        "rendered": true
      }
    ]
  }
  ```

### Ausgabe

* **A11yReport.json**

  ```json
  {
    "summary": {
      "violations": 5,
      "passes": 120,
      "score": 82
    },
    "violations": [
      {
        "id": "image-alt",
        "impact": "serious",
        "description": "Images must have alt attributes",
        "nodes": [
          {"target": "img[src='/hero.jpg']", "html": "<img src='/hero.jpg'>"}
        ]
      }
    ]
  }
  ```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **Playwright MCP**: um DOM nach Rendering zu inspizieren, inkl. dynamisch nachgeladenem Content
* **axe-core**: Standard-JavaScript-Library für A11y-Tests
* **Color Contrast Tools**: z. B. `color-contrast-checker`
* **Parser**: BeautifulSoup/lxml für Fallback-Analysen (falls axe blockiert wird)

### Algorithmen

* **axe Injection**: Clientseitige Ausführung von `axe.run(document)`
* **Kontrastanalyse**: Berechnung WCAG AA/AAA Scores
* **Fallback-Heuristik**: ALT-Attribute prüfen, Tabindex prüfen, `<label>`-Verknüpfung für Inputs

---

## 4. Externe Abhängigkeiten

* **Playwright MCP**: Browser Rendering + Script Injection
* **Filesystem MCP**: Speichern von Reports
* **Memory MCP**: Historie von Accessibility-Scores pro Kunde (Delta-Analyse)
* **LLM (optional)**: Erklärung der Findings in Kundensprache („Was bedeutet das?“)

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * CrawlResult.json laden
   * Liste URLs extrahieren

2. **Browser Session**

   * Playwright starten
   * Seite rendern, warten auf Network Idle

3. **axe Injection**

   * axe-core Script in DOM injizieren
   * `axe.run()` ausführen
   * JSON-Resultat speichern

4. **Zusatzprüfungen**

   * Farbkontrast prüfen (CSS + Computed Styles)
   * Semantik prüfen (fehlende Landmark-Roles)

5. **Scoring**

   * Score = 100 – (gewichtete Verstöße)
   * Impact-Klassen: minor, moderate, serious, critical

6. **Output**

   * A11yReport.json pro Domain
   * Summen/Violations/Beispiele

---

## 6. Quality Gates & Non-Functional Requirements

* **Score-Threshold**: Renewal muss A11y ≥ 95 liefern
* **Transparenz**: jeder Fund mit `description`, `impact`, `target`
* **Performance**: ≤ 5 Sekunden pro Seite (Rendering + Audit)
* **Resilienz**: Falls axe blockiert, Fallback auf heuristische Checks
* **Reproduzierbarkeit**: Ergebnisse bei Mehrfachlauf stabil

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Container mit Playwright + axe-core gebundelt
* **Scaling**: pro Seite parallel ausführbar (Container pro URL)
* **Scheduling**: bei jedem Crawl oder auf Kundenwunsch on-demand
* **Observability**:

  * Logs: Anzahl Verstöße pro Kategorie
  * Metrics: Durchschnitts-Score, Delta seit letztem Scan
  * Alerts: Score < 80 → Warnung

---

## 8. Erweiterungspotenzial & offene Fragen

* **Automatische Fix-Vorschläge**: Soll A5 nur melden oder auch Fix-Snippets (ALT, ARIA)?
* **CI/CD-Integration**: A11y-Test als Pflichtschritt im Deployment?
* **Mobile A11y**: Unterschiede Desktop/Mobile – zwei Profile notwendig?
* **User Flows**: nur einzelne Seiten testen oder Klickpfade (z. B. Checkout)?

---

📄 **Fazit**:
A5 ist der zentrale Qualitätsprüfer für Barrierefreiheit.
Ohne A5 kein vertrauenswürdiges „OfferDoc“, da Kunden explizit auf Accessibility achten (gesetzliche Vorgaben in EU/CH).
Technologie-agnostisch implementierbar: Python (Playwright + axe-core), Java (Selenium + Deque axe).
