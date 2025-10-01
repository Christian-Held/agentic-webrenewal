# Agent A15 – Offer

---

## 1. Übersicht / Rolle im System

Der **Offer Agent (A15)** ist der **Geschäftsabschluss-Agent**.
Er nimmt die von den Analyse- und Vergleichs-Agenten erzeugten Daten und wandelt sie in ein **verständliches, kundenorientiertes Angebot** um.

Ziele:

* Alle Ergebnisse (SEO, Accessibility, Security, Performance, Design, Diffs) in einem **strukturierten Angebotsdokument** bündeln.
* Unterschied **vorher/nachher** transparent darstellen.
* Klare **Leistungspakete, Preise, Zeitrahmen** anbieten.
* Ausgabe in **Markdown** (für spätere Konvertierung in PDF oder HTML).

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **PreviewIndex.json (A14)** → Vorher/Nachher-Preview + Metrik-Deltas
* **RenewalPlan.json (A10)** → Liste empfohlener Maßnahmen
* **A11yReport.json (A5)**, **SEOReport.json (A6)**, **SecurityReport.json (A7)** → Bewertungsgrundlage
* **BuildArtifact.json (A13)** → neue Website-Artefakte (Größe, Struktur, Assets)

Beispiel:

```json
{
  "preview": {"metrics": {"a11yDelta": "+38","perfDelta": "+22","seoDelta": "+15"}},
  "plan": {"actions":[{"id":"upgrade-bootstrap","impact":"hoch"}]},
  "a11y": {"summary":{"violations":23,"passes":120}},
  "seo": {"issues":[{"id":"missing-meta-description"}]},
  "security": {"headers":{"hsts":false}}
}
```

### Ausgabe

* **OfferDoc.json**

```json
{
  "summary": {
    "a11yDelta": "+38",
    "perfDelta": "+22",
    "seoDelta": "+15",
    "securityIssuesFixed": 3
  },
  "price": {"currency":"CHF","net":4200},
  "timeline": {"effort_hours": 48, "delivery_days": 14},
  "docPath": "sandbox/offer/angebot.md"
}
```

* **angebot.md (Markdown)**

  * Einleitung
  * Vorher/Nachher-Übersicht (Tabellen + Diagramme optional)
  * Maßnahmenliste (mit Priorität/Impact)
  * Zeit- und Kostenrahmen
  * Call-to-Action (z. B. Unterschrift oder Bestelllink)

---

## 3. Interne Abhängigkeiten

### Technologien

* **LLM (mehrere)**: Um aus den JSON-Reports ein verständliches Angebot zu formulieren.
* **Template-System**: Markdown-Template + Variablen aus JSON.
* **Validator-Agent**: prüft, ob Angebot vollständig (Summary, Preis, Timeline, CTA).

### Algorithmen

* **Preisberechnung**: Aufwand (RenewalPlan.estimate_hours) × interner Stundensatz × Risikoaufschlag.
* **Wertdarstellung**: Umrechnung der Deltas in Nutzen („+22 Performance = 0.8s Ladezeit schneller“).
* **Paketierung**: Leistungen in Module (Basic, Standard, Premium).

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Speichert Angebot (angebot.md, angebot.pdf).
* **Memory MCP**: Ablage von Angeboten für Nachvollziehbarkeit.
* **Comparator (A14)**: liefert Deltas für die Nutzen-Argumentation.
* **Kundeninterface**: Übergabe von Angeboten als Link, E-Mail oder PDF.

---

## 5. Ablauf / Workflow intern

1. **Input aggregieren**

   * Alle Reports (A5–A14) + Plan (A10) einlesen.

2. **Analyse**

   * Deltas und Verbesserungen berechnen.
   * Maßnahmen nach Impact und Priorität sortieren.

3. **Preisermittlung**

   * Stundensatz × Aufwand (aus Plan).
   * ggf. Upsell-Optionen (SEO-Paket, Security-Hardening).

4. **Dokumenterstellung**

   * LLM generiert Angebot in Markdown.
   * Strukturiert: Einleitung → Analyse → Maßnahmen → Nutzen → Preis → Timeline → CTA.

5. **Output speichern**

   * OfferDoc.json + angebot.md.
   * optional: PDF-Export.

---

## 6. Quality Gates & Non-Functional Requirements

* **Vollständigkeit**: Dokument muss mindestens enthalten: Summary, Maßnahmen, Preis, Timeline, CTA.
* **Klarheit**: Für Nicht-Techniker verständlich.
* **Seriosität**: Corporate-Design-kompatibel (Logo, Farben).
* **Konsistenz**: Angebot spiegelt RenewalPlan und Deltas korrekt wider.
* **Performance**: Erstellung < 3 Sekunden.

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Als eigenständiger Service oder Funktion (on-demand).
* **Scaling**: Kann parallel mehrere Angebote generieren.
* **Persistence**: Angebote archiviert in Memory MCP oder DB.
* **Observability**:

  * Logs: Anzahl generierter Angebote
  * Metrics: Conversion-Rate (angenommene Angebote)
  * Alerts: Falls Angebot unvollständig oder fehlerhaft

---

## 8. Erweiterungspotenzial & offene Fragen

* **Mehrsprachigkeit**: Angebot automatisch in DE/EN/FR generieren.
* **Custom Branding**: CI/CD-konforme Angebote mit Firmenlogo.
* **Dynamische Preisgestaltung**: basierend auf Wettbewerb oder Kundenhistorie.
* **Digitale Signatur**: Angebot direkt online annehmbar (z. B. mit DocuSign).

---

📄 **Fazit**:
A15 ist der **Business-Connector**. Er übersetzt technische Verbesserungen in einen **greifbaren Mehrwert** mit Preis, Nutzen und Timeline.
Ohne ihn bleibt der Prozess rein technisch – mit ihm wird er zu einem **verkaufsfähigen Produkt**.
---

## Aktueller Implementierungsstand

**Bereits funktionsfähig**

- Erstellt Angebotstext aus Plan-Aktionen und Diff-Zusammenfassung inklusive Richtpreis.
- Verwendet Domain-Namen als kundenfreundliches Label.

**Offene Schritte bis zur Production-Readiness**

- Mehrseitige Angebots-PDFs, Branding-Templates und Versionierung.
- Mehrsprachige Angebote sowie CRM-Schnittstellen.

