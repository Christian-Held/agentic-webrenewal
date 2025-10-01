# Agent A10 – Plan/Proposal

---

## 1. Übersicht / Rolle im System

Der **Plan/Proposal Agent (A10)** ist das **strategische Herzstück** der gesamten Pipeline.
Er sammelt die Ergebnisse der Analyse-Agenten (A3–A9) und erstellt daraus:

* **einen strukturierten Maßnahmenplan** mit konkreten Handlungsanweisungen,
* **eine Priorisierung nach Impact & Aufwand**,
* **eine erste Aufwandsschätzung** für die Umsetzung.

Der Output dient sowohl als **interne Steuerung** (für A11–A13) als auch als **Verkaufsgrundlage** (für A15 Offer Agent).

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **ContentExtract.json (A3)**
* **TechFingerprint.json (A4)**
* **A11yReport.json (A5)**
* **SEOReport.json (A6)**
* **SecurityReport.json (A7)**
* **MediaReport.json (A8)**
* **NavModel.json (A9)**

Beispielauszug:

```json
{
  "content": {"pages": [{"url": "/", "title": "Start"}]},
  "tech": {"framework": {"name": "WordPress", "version": "6.1"}},
  "a11y": {"summary": {"violations": 12, "score": 78}},
  "seo": {"issues": [{"id": "missing-meta-description", "where": ["/"]}]},
  "security": {"headers": {"hsts": false, "csp": false}},
  "media": {"images": [{"url": "/hero.jpg", "bytes": 1200000}]},
  "nav": {"root": {"id": "root", "children": []}}
}
```

### Ausgabe

* **RenewalPlan.json**

```json
{
  "goals": ["A11y>=95", "Perf>=90", "SEO>=90"],
  "actions": [
    {"id": "upgrade-bootstrap", "reason": "veraltet (v3.3.7)", "impact": "hoch", "effortH": 12},
    {"id": "img-opt", "reason": "hero.jpg >1MB", "impact": "hoch", "effortH": 4},
    {"id": "add-meta-desc", "reason": "fehlend auf 5 Seiten", "impact": "mittel", "effortH": 2}
  ],
  "estimate": {"effortH": 32, "durationDays": 10, "team": "1 Dev, 1 Designer"}
}
```

---

## 3. Interne Abhängigkeiten

### Technologien

* **LLM (mehrere Modelle parallel)**:

  * GPT-4.1-mini für JSON-Plan-Generierung,
  * Claude/DeepSeek für alternative Perspektiven,
  * Validator-Agent vergleicht Outputs.
* **Scoring/Validator Modul**: prüft Konsistenz der Outputs (Schema-Validität, Redundanz).
* **Aggregator**: führt Findings aus allen Agenten zusammen.

### Algorithmen

* **Issue Aggregation**: alle Findings aus A3–A9 sammeln.
* **Priorisierung**: Impact × Effort Matrix → Reihenfolge.
* **Plan-Schema Mapping**: Normalize zu RenewalPlan.json.
* **Validator**: bei mehreren LLM-Ergebnissen → „best of N“ wählen.

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Schreiben von RenewalPlan.json.
* **Memory MCP**: Speicherung historischer Pläne (Delta-Analysen).
* **Optional**: Zugriff auf Kostentabellen, Benchmarks (Stundensätze, Designpreise).
* **LLM-Router**: Flexibles Dispatching mehrerer Modelle pro Task.

---

## 5. Ablauf / Workflow intern

1. **Input Aggregation**

   * Reports A3–A9 laden
   * Findings in ein gemeinsames Issues-Objekt zusammenführen

2. **Goal Definition**

   * Standardziele: A11y ≥ 95, Perf ≥ 90, SEO ≥ 90
   * Zusätzliche Ziele aus TechFingerprint oder Kundenwünschen (z. B. „Mobile First“)

3. **LLM-Aufruf (parallel)**

   * Prompt: „Erstelle RenewalPlan.json aus diesen Inputs …“
   * Mindestens 2–3 Modelle parallel aufrufen

4. **Validation**

   * Ergebnisse vergleichen
   * Schema-Validität erzwingen
   * Bestes Ergebnis wählen

5. **Output-Erstellung**

   * RenewalPlan.json speichern
   * Delta zu früheren Plänen markieren

---

## 6. Quality Gates & Non-Functional Requirements

* **Schema-Konsistenz**: Plan muss JSON-valid sein
* **Nachvollziehbarkeit**: Jede Aktion muss mit `reason` und `impact` begründet sein
* **Priorisierung**: Hoch/Mittel/Niedrig klar unterscheiden
* **Effort Estimation**: Stunden und Teamrollen angeben
* **Performance**: Erstellung ≤ 5 Sekunden für 100 Issues
* **Flexibilität**: Muss sowohl für minimale Verbesserungen als auch für komplettes Redesign nutzbar sein

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: eigenständiger Service (Python/Java), LLM-agnostisch
* **Scaling**: parallele Pläne für mehrere Kunden-Websites
* **Persistence**: RenewalPlan-Versionierung im Memory MCP
* **Observability**:

  * Logs: Anzahl Actions, Gesamtaufwand
  * Metrics: Effort per Action, Score-Delta pro Kunde
  * Alerts: Plan enthält keine High-Impact-Aktionen → Flag

---

## 8. Erweiterungspotenzial & offene Fragen

* **Automatische Kostenkalkulation**: Soll A10 Preise (CHF/EUR/USD) direkt berechnen?
* **Branchenspezifische Playbooks**: Soll A10 Templates je Branche verwenden (Physio, Kanzlei, Architekt)?
* **Multi-Plan Optionen**: Soll A10 Varianten erzeugen („Minimal Update“, „Full Redesign“)?
* **Feedback-Loop**: Soll der Kunde Aktionen priorisieren dürfen → Rückschleife in A10?

---

📄 **Fazit**:
A10 ist der **Planungs- und Strategie-Agent**. Ohne ihn bleibt das System fragmentiert. Er verwandelt die Analyse-Outputs in einen **klar priorisierten Maßnahmenplan**, der sowohl Entwickler als auch Kunden verstehen.
Mit Multi-LLM-Architektur + Validator entsteht hier ein robustes, fehlerresistentes Agentic-System.
---

## Aktueller Implementierungsstand

**Bereits funktionsfähig**

- Leitet Maßnahmen aus A11y-, SEO-, Security- und Tech-Berichten ab.
- Berechnet Aufwandsschätzung und Zielmetriken basierend auf CLI-Parametern.

**Offene Schritte bis zur Production-Readiness**

- Gewichtung nach Business-Impact und Abhängigkeiten zwischen Tasks.
- Integration von Kostenmodellen und Kundenpräferenzen.

