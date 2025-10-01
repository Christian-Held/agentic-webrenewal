# Agent A14 – Comparator

---

## 1. Übersicht / Rolle im System

Der **Comparator Agent (A14)** ist der **Vergleichs- und Validierungsagent**.
Er ermöglicht es, die **alte Website** und die **neu generierte Website** (von A13 Builder) **visuell, strukturell und inhaltlich** zu vergleichen.
Damit schafft er Transparenz für Kunden und liefert die Grundlage für Angebotsdokumente (A15).

Ziele:

* Unterschiede in Inhalt, Layout, Struktur und Performance **sichtbar machen**.
* **Vorher/Nachher-Ansicht** für Kunden bereitstellen.
* Automatische **Diff-Reports** für Entwickler (Text, Code, Assets).
* Validierung gegen die definierten **Quality Gates** (A11y ≥95, Perf ≥90, SEO ≥90).

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **CrawlResult.json (A2)** → alte Website
* **BuildArtifact.json (A13)** → neue Website
* **A11yReport.json (A5)**, **SEOReport.json (A6)**, **SecurityReport.json (A7)** → für Bewertungsdeltas

Beispiel:

```json
{
  "oldsite": "sandbox/oldsite/",
  "newsite": "sandbox/newsite/",
  "a11y": {"summary":{"violations":23,"passes":120}},
  "seo": {"issues":[{"id":"missing-meta-description"}]}
}
```

### Ausgabe

* **PreviewIndex.json**

```json
{
  "old": "sandbox/oldsite/",
  "new": "sandbox/newsite/",
  "diff": "sandbox/preview/index.html",
  "metrics": {
    "a11yDelta": "+38",
    "perfDelta": "+22",
    "seoDelta": "+15",
    "sizeReductionKB": 820
  }
}
```

* **Preview HTML (sandbox/preview/index.html)** → Interaktive Vergleichsansicht

---

## 3. Interne Abhängigkeiten

### Technologien

* **Diffing Libraries**:

  * Python `difflib` für HTML/Text.
  * `bs4` (BeautifulSoup) für DOM-Struktur-Vergleich.
* **Asset Analyzer**: Dateigrößen, Bildformate vergleichen.
* **Performance Heuristiken**: Bytes geladen, DOM-Größe, Inline-Skripte.
* **UI Layer**: einfache HTML/JS-Seite mit Split-View (vorher/nachher).

### Algorithmen

* **Textdiff**: Absätze und Überschriften vergleichen.
* **Structural Diff**: DOM-Baum vs. DOM-Baum (Nodes, ARIA, Semantik).
* **Asset Diff**: Alte vs. neue Bilder, CSS, JS (Dateigröße, Formate).
* **Delta-Berechnung**: +/– Werte für A11y, SEO, Perf.

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Zugriff auf `oldsite/` und `newsite/`.
* **Memory MCP**: Ablage von Diff-Ergebnissen für spätere Reports.
* **Offer Agent (A15)**: nutzt PreviewIndex.json + deltas für Angebot.

---

## 5. Ablauf / Workflow intern

1. **Input sammeln**

   * Alte Site (CrawlResult → oldsite/), neue Site (BuildArtifact → newsite/).

2. **Vergleich durchführen**

   * HTML-Diff → Änderungen im Code.
   * Text-Diff → geänderte/verbesserte Inhalte.
   * Asset-Diff → Bildgrößen, Dateitypen.

3. **Delta-Berechnung**

   * A11y, SEO, Security, Performance gegen alte Werte berechnen.

4. **Preview generieren**

   * HTML mit Split-Screen Viewer: Alte Seite links, neue Seite rechts.
   * Highlight für Änderungen (z. B. rote/grüne Markierungen).

5. **Output speichern**

   * PreviewIndex.json mit Pfaden + Deltas.
   * index.html im Ordner `sandbox/preview/`.

---

## 6. Quality Gates & Non-Functional Requirements

* **Klarheit**: Diffs müssen auch für Nicht-Techniker verständlich sein.
* **Performanz**: Vergleich bis 500 Seiten < 10 Sekunden.
* **Neutralität**: Unterschiede dokumentieren, keine Bewertung → Bewertung erst in A15.
* **Zuverlässigkeit**: Keine False-Positives bei DOM-Diff.
* **Barrierefreiheit**: Preview selbst soll WCAG-konform sein.

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Service, der on-demand aufgerufen wird (nach A13).
* **Scaling**: Parallel für mehrere Kunden-Domains.
* **Persistence**: Alle Previews archiviert (zur Nachvollziehbarkeit für Kunden).
* **Observability**:

  * Logs: Anzahl verglichener Seiten
  * Metrics: Zeit pro Vergleich, Größe Diff-HTML
  * Alerts: wenn Vergleich unvollständig

---

## 8. Erweiterungspotenzial & offene Fragen

* **Visuelle Regressionstests**: Screenshots mit Playwright und Pixel-Diff.
* **Kundenfreundlicher Report**: Option für PDF mit Bildern + Zusammenfassung.
* **Timeline View**: mehrere Versionen im Verlauf (nicht nur alt vs. neu).
* **Automatisierte Screenshots**: Alte vs. neue Seite für visuelles Proofing.

---

📄 **Fazit**:
A14 ist der **Vergleichs- und Vertrauensanker**. Er macht Fortschritte sichtbar, dokumentiert Unterschiede und bereitet die Basis für Angebots- und Verkaufsprozesse.
Ohne A14 wäre das System eine Blackbox – mit A14 wird es für Kunden nachvollziehbar und überprüfbar.

## Testing

* `pytest tests/unit/agents/test_comparator_agent.py -q`
* Prüft direkte Zuordnung, Fallbacks und fehlende Dateien anhand der Build-Dummy-Seiten.
* Integrationstest validiert die realen Diff-Artefakte (`preview.json`).

