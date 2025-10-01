# Agent A16 – Memory

---

## 1. Übersicht / Rolle im System

Der **Memory Agent (A16)** ist der **Persistenz- und Gedächtnis-Agent** des gesamten Systems.
Während andere Agenten Daten analysieren, generieren oder vergleichen, kümmert sich A16 um deren **dauerhafte Speicherung, Versionierung und Abrufbarkeit**.

Ziele:

* Zentrale Ablage für **alle Artefakte** (Analysen, Pläne, Builds, Angebote).
* Ermöglicht **Langzeitvergleiche** (z. B. Kunde X Version 1 vs. Version 3).
* Unterstützt **Agentenzusammenarbeit**, indem Ergebnisse schnell wiederverwendbar sind.
* Grundlage für **RAG-Erweiterungen** (Retrieval-Augmented Generation).

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **Alle JSON-Artefakte** (A0–A15): Tools, CrawlResults, Reports, Plans, ContentBundles, BuildArtifacts, OfferDocs.
* **User Queries**: „Zeig mir das letzte Angebot für physioheld.ch“, „Liste alle Accessibility Reports der letzten 6 Monate“.

Beispiel:

```json
{
  "artifact": "SEOReport",
  "domain": "physioheld.ch",
  "version": "2025-09-26",
  "data": {"issues":[{"id":"missing-meta-description"}]}
}
```

### Ausgabe

* **Persistierte Ablage** (z. B. LibSQL DB oder Filesystem).
* **MemoryQueryResult.json**

```json
{
  "results": [
    {"type":"SEOReport","domain":"physioheld.ch","date":"2025-09-26","issues":3},
    {"type":"A11yReport","domain":"physioheld.ch","date":"2025-09-26","violations":23}
  ]
}
```

---

## 3. Interne Abhängigkeiten

### Technologien

* **MCP Memory LibSQL**: SQLite-kompatibel, leichtgewichtig, lokal oder remote.
* **Filesystem MCP**: Speicherung großer Artefakte (HTML, PDFs, Images).
* **Schema Normalisierung**: JSON-Schemas werden in DB-Strukturen abgebildet.
* **Versionierung**: Jede Speicherung mit Zeitstempel + Versionsnummer.

### Algorithmen

* **Indexierung**: Metadaten (Domain, Datum, Typ) werden separat indiziert.
* **Retention**: Policy für Löschfristen (z. B. DSGVO-konform nach X Monaten).
* **Search/Query**: Abfragen über Schlüsselwörter, Domains, Zeiträume.

---

## 4. Externe Abhängigkeiten

* **Alle Agenten (A0–A15)**: liefern Input.
* **Query-Interface (z. B. API)**: Nutzer oder Validator-Agenten können nach Artefakten fragen.
* **Compliance Module**: prüft DSGVO-Konformität (z. B. keine unnötige Speicherung von PII).

---

## 5. Ablauf / Workflow intern

1. **Input empfangen**

   * JSON oder Datei von anderem Agent.

2. **Metadaten erzeugen**

   * Domain, Typ, Datum, Version.

3. **Persistenz**

   * Kleine JSON-Daten in LibSQL speichern.
   * Große Dateien (Bilder, HTML, PDFs) im Filesystem speichern + Referenz in DB.

4. **Indexierung**

   * Automatisch Index-Einträge erstellen für schnelle Suche.

5. **Query-Funktion**

   * Nutzer oder andere Agenten können Ergebnisse abrufen („letzte SEO Reports für Kunde XY“).

6. **Output zurückgeben**

   * JSON-Ergebnisse für Integration in Reports, Angebote oder Dashboards.

---

## 6. Quality Gates & Non-Functional Requirements

* **Zuverlässigkeit**: Kein Datenverlust (ACID-Transaktionen bei LibSQL).
* **Abfragegeschwindigkeit**: < 200ms für Metadaten-Suchen.
* **DSGVO-Konformität**: Daten nur so lange speichern wie nötig.
* **Erweiterbarkeit**: Neue Artefakt-Typen leicht einbindbar.
* **Sicherheit**: Verschlüsselte Speicherung optional (für sensible Daten).

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Als eigenständiger Service, persistente DB + Filesystem.
* **Scaling**: Lokale DB für Einzelkunden, zentralisierte DB für Multi-Tenant.
* **Observability**:

  * Logs: Speichervorgänge, Abfragen.
  * Metrics: Anzahl Artefakte, Speicherplatzverbrauch.
  * Alerts: wenn Speicher > 80% oder Query-Fehler auftreten.

---

## 8. Erweiterungspotenzial & offene Fragen

* **RAG-Integration**: Artefakte direkt in Vektor-DB einspielen für AI-Abfragen.
* **Multi-Cloud Sync**: DB + Filesystem in Cloud-Speicher replizieren.
* **Delta-Speicherung**: Nur Unterschiede statt Vollkopien speichern.
* **Kunden-Dashboards**: Web-Oberfläche für gespeicherte Reports.

---

📄 **Fazit**:
A16 ist das **Gedächtnis** des Systems. Ohne ihn sind die Verbesserungen einmalig und nicht nachvollziehbar.
Mit ihm entsteht eine **historische Datenbasis**, die für Angebote, Audits und zukünftige Optimierungen entscheidend ist.
---

## Aktueller Implementierungsstand

**Bereits funktionsfähig**

- Speichert Angebotsschnappschüsse in einer In-Memory-Map für spätere Abfragen.
- Normalisiert Domains als Schlüssel.

**Offene Schritte bis zur Production-Readiness**

- Persistente Ablage (LibSQL, Redis) und Ablaufstrategien.
- Abfragen nach Historie/Änderungsdiffs und Berechtigungen.

