# Agent A11 – Rewrite

---

## 1. Übersicht / Rolle im System

Der **Rewrite Agent (A11)** ist für die **Neuerstellung, Anpassung und Optimierung von Website-Inhalten** zuständig.
Er nimmt den von A3 (ContentExtract) gelieferten Originaltext, kombiniert ihn mit den Verbesserungszielen aus A10 (RenewalPlan), und erzeugt daraus:

* **verbesserte Texte** (stilistisch, sprachlich, SEO-optimiert),
* **ergänzte Meta-Daten** (Descriptions, Keywords, OpenGraph),
* **fehlende Inhalte** (Call-to-Action, Strukturblöcke),
* **optionale Übersetzungen** (Multilingual-Support).

Dabei kann er in zwei Modi arbeiten:

1. **Minimal Improve**: Inhalte bleiben weitgehend erhalten, nur kleinere Optimierungen.
2. **Full Rewrite/Regeneration**: Texte werden komplett neu geschrieben, ggf. nach Vorgaben für Tonalität, Branding oder Layout-Theme.

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **ContentExtract.json (A3)**
* **SEOReport.json (A6)**
* **RenewalPlan.json (A10)**

Beispiel:

```json
{
  "pages": [
    {
      "url": "/",
      "title": "Willkommen",
      "headings": ["Willkommen"],
      "text": "Wir sind eine kleine Praxis.",
      "meta": {}
    }
  ],
  "seo": {
    "issues": [{"id": "missing-meta-description", "where": ["/"]}]
  },
  "plan": {
    "actions": [{"id": "add-meta-desc", "reason": "fehlend", "impact": "mittel"}]
  }
}
```

### Ausgabe

* **ContentNew.json**

```json
{
  "pages": [
    {
      "url": "/",
      "title": "Physiotherapie in Zürich – modern & persönlich",
      "meta": {"description": "Ihre Praxis für individuelle Behandlung, Bewegung und Prävention."},
      "sections": [
        {"id": "hero", "html": "<section><h1>Willkommen bei PhysioHeld</h1><p>Individuelle Physiotherapie in Zürich.</p></section>"},
        {"id": "cta", "html": "<section><a href='/kontakt'>Jetzt Termin vereinbaren</a></section>"}
      ]
    }
  ]
}
```

---

## 3. Interne Abhängigkeiten

### Technologien

* **LLMs (mehrere parallel)**:

  * GPT-4.1-mini für strukturierte Outputs,
  * Claude/DeepSeek/Mistral für kreative Textalternativen,
  * Validator prüft Schema + Kohärenz.
* **Schema-Validator**: JSON-Output erzwingen.
* **SEO-Korpus / Keyword-DB**: zur Keyword-Ergänzung.
* **Multilingual-Lib** (optional): langdetect, Übersetzung via LLM.

### Algorithmen

* **Content Mapping**: Originaltexte → Plan-Ziele mappen.
* **Rewrite Rules**:

  * Grammatik & Stil verbessern,
  * SEO-Fixes (Meta, Keywords, Überschriften-Hierarchie),
  * Accessibility (leicht verständliche Sprache).
* **Creative Mode**: optional, wenn Kunde neues Branding/Layout will.
* **Validation**: alle Outputs gegen JSON-Schema prüfen.

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Speichern von ContentNew.json.
* **Memory MCP**: Speicherung historischer Content-Versionen.
* **SEO Tools (A6)**: Input für Keyword-Lücken.
* **Plan Agent (A10)**: Input für konkrete Tasks.

---

## 5. Ablauf / Workflow intern

1. **Input Aggregation**

   * ContentExtract, SEOReport, RenewalPlan laden

2. **Rewrite Strategy bestimmen**

   * Wenn Plan „Minimal Update“ → nur kleinere Verbesserungen
   * Wenn Plan „Full Rewrite“ → komplett neue Inhalte

3. **LLM-Aufruf (parallel)**

   * Mehrere Modelle generieren ContentNew.json
   * Varianten: konservativ, kreativ, SEO-stark

4. **Validation**

   * Schema-Validität
   * Lesbarkeit (z. B. Flesch-Index)
   * Keyword-Abdeckung vs. SEOReport

5. **Output-Erstellung**

   * ContentNew.json speichern
   * Delta zu Originalinhalt vermerken

---

## 6. Quality Gates & Non-Functional Requirements

* **Schema-Konsistenz**: JSON-Ausgabe immer valide
* **SEO-Abdeckung**: Fehlende Keywords müssen ergänzt werden
* **Lesbarkeit**: Zielgruppe verstehen, einfache Sprache, kurze Sätze
* **Branding-Flexibilität**: Tonalität per Parameter steuerbar (seriös, freundlich, technisch)
* **Mehrsprachigkeit**: optional, aber vorbereitet

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: eigenständiger Service mit LLM-Router
* **Scaling**: parallele Verarbeitung von >100 Seiten gleichzeitig
* **Persistence**: Versionierung (Original → Rewrite v1 → Rewrite v2)
* **Observability**:

  * Logs: Anzahl rewrites, Tokenverbrauch
  * Metrics: SEO-Scores vor/nach Rewrite
  * Alerts: Wenn Content leer/unvollständig

---

## 8. Erweiterungspotenzial & offene Fragen

* **Übersetzungen**: Soll A11 direkt Übersetzungen liefern oder nur Content-Rewrites?
* **Faktenprüfung**: Sollen Aussagen gegen externe Quellen geprüft werden (z. B. Medizinrecht, Preise)?
* **Bilder/Alt-Texte**: Soll A11 auch Texte für Media-Agent (A8) generieren?
* **Personalisierung**: Soll A11 Inhalte je nach Persona (z. B. „junger Patient“, „Senior“) variieren?

---

📄 **Fazit**:
A11 ist der **Content-Generator und Optimierer**. Er verwandelt die Analyseergebnisse + Plan in **hochwertige, SEO-optimierte Inhalte**.
Er ist stark LLM-getrieben, benötigt aber Validatoren, um **Schema-Validität und inhaltliche Qualität** sicherzustellen.

## Testing

* `pytest tests/unit/agents/test_rewrite_agent.py -q`
* Stub-LLMs simulieren JSON-Antworten sowie Fehlerfälle; Fallback-Bundles sichern den Edge-Case ab.
* Integrationstest verwendet einen statischen Bundle-Stub, um die Pipeline deterministisch zu halten.

