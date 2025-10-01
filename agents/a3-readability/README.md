# Agent A3 – Readability

---

## 1. Übersicht / Rolle im System

Der **Readability Agent (A3)** übernimmt die in **A2 (Crawler)** gewonnenen Daten und konzentriert sich darauf, die **wesentlichen Inhalte einer Website** herauszufiltern. Ziel ist es, die HTML-Struktur zu reduzieren und nutzbare Inhalte wie Texte, Titel und Überschriften in eine klare, maschinenlesbare Form zu bringen.

A3 arbeitet als „Content Extractor“ zwischen Rohdaten und semantischer Analyse. Seine Aufgabe ist nicht Optimierung, sondern **reine inhaltliche Extraktion**, die als Basis für SEO-Checks (A6), Content-Rewrites (A11) und Angebotsdokumente (A15) dient.

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **CrawlResult.json** (von A2 erzeugt)

  ```json
  {
    "pages": [
      {
        "url": "https://www.example.com/",
        "status": 200,
        "html": "<html><head><title>Beispiel</title></head><body><h1>Willkommen</h1><p>Unsere Leistungen…</p></body></html>",
        "rendered": true
      }
    ]
  }
  ```

### Ausgabe

* **ContentExtract.json**

  ```json
  {
    "pages": [
      {
        "url": "https://www.example.com/",
        "title": "Beispiel",
        "headings": ["Willkommen"],
        "text": "Unsere Leistungen…",
        "lang": "de",
        "word_count": 320,
        "readability_score": 72.5
      }
    ]
  }
  ```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **Parser**: BeautifulSoup / lxml für DOM-Analyse
* **Readability-Engine**: `trafilatura` oder `readability-lxml` zur Haupttext-Extraktion
* **Language-Detection**: CLD3, langdetect, spaCy-Pipelines
* **NLP-Basis**: Tokenizer für Word Count, Satzgrenzen
* **Metriken**: Flesch-Reading-Ease oder andere Lesbarkeitsindizes

### Algorithmen

* **Boilerplate Removal**: Entfernen von Navigationsleisten, Footern, Werbeblöcken
* **Heading-Hierarchie**: Sammeln von H1–H6 in linearer Struktur
* **Text-Extraction**: Fließtexte in logischer Reihenfolge extrahieren
* **Lang Detection**: per `<html lang>` oder NLP-basierter Klassifizierung
* **Readability Score**: z. B. Flesch-Wert, berechnet aus Satz- und Wortlängen

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Ein- und Auslesen der JSON-Artefakte
* **Memory MCP**: Persistenz der extrahierten Texte für RAG-artige Wiederverwendung
* **LLM (optional)**: für Validierung, ob der extrahierte Text „vollständig und sinnvoll“ ist
* **Input vom Nutzer** (optional): Sprachpräferenz, gewünschte Extraktions-Tiefe (z. B. nur H1+H2)

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * CrawlResult.json laden
   * Output-Struktur vorbereiten

2. **Parsing pro Seite**

   * HTML mit lxml/bs4 parsen
   * `<title>` extrahieren
   * `<h1>`–`<h6>` sammeln

3. **Readability Extraction**

   * trafilatura/readability-Library anwenden
   * Haupttext in reiner Textform gewinnen
   * Boilerplate (Menus, Footer, Ads) entfernen

4. **Language Detection**

   * Attribut `<html lang>` auswerten
   * Wenn fehlt → NLP-gestützte Spracherkennung

5. **Metrics**

   * Word Count ermitteln
   * Flesch-Reading-Ease Score oder alternative Lesbarkeitskennzahlen berechnen

6. **Validation**

   * LLM oder Heuristik: Ist extrahierter Text zu kurz, zu redundant, nicht sinnvoll?
   * Bei Mängeln: Retry mit alternativer Extraktionsstrategie

7. **Output**

   * ContentExtract.json speichern
   * Optional: Plaintext-Files pro Seite im Filesystem ablegen

---

## 6. Quality Gates & Non-Functional Requirements

* **Korrektheit**: ≥ 90 % der sichtbaren Haupttexte müssen extrahiert werden
* **Vollständigkeit**: Keine wichtigen Sections (Hero, Leistungen, Kontakt) fehlen
* **Sprachkonsistenz**: richtige Locale pro Seite
* **Performance**: Extraktion ≤ 1 Sekunde pro Seite bei Standard-Hardware
* **Lesbarkeit**: Score-Metriken müssen stabil reproduzierbar sein
* **Robustheit**: funktioniert bei minified HTML, Inline-JS/CSS, obfuscation

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Container/Microservice, leichtgewichtige Python- oder Java-Pipeline
* **Scaling**: Horizontal skalierbar, parallel pro Seite
* **Frequency**: nach jedem Crawl (A2) automatisch ausgeführt
* **Observability**:

  * Logs: Länge Text, erkannte Sprache, Score
  * Metriken: Seiten pro Minute, Extraktionsquote
  * Alerts: wenn Text < 50 Wörter oder Score < 20

---

## 8. Erweiterungspotenzial & offene Fragen

* **Multi-Lingual Pages**: getrennte Extraktion pro Sprachversion (z. B. `/de/` und `/en/`)
* **Section-Tagging**: Inhalte in Kategorien einordnen (Hero, About, Services)
* **NLP-Anreicherung**: Named Entity Recognition für Firmen, Produkte, Orte
* **Custom Stopwords**: Entfernen irrelevanter Texte wie Cookie-Banner
* **Offene Frage**: Soll A3 nur „plain text“ liefern oder auch HTML-Snippets (für A11 Rewriter)?

---

📄 **Fazit**:
A3 wandelt die Roh-HTMLs in **strukturierte Content-Daten** um. Ohne A3 wäre keine fundierte SEO-, Accessibility- oder Content-Analyse möglich. Technologie-agnostisch lässt sich der Agent sowohl mit **Python (trafilatura, bs4)** als auch mit **Java (Jsoup, Boilerpipe)** realisieren.
---

## Aktueller Implementierungsstand

**Bereits funktionsfähig**

- Extrahiert Seitentexte via Trafilatura/BeautifulSoup und berechnet Flesch-Readability.
- Ermittelt optional die Seitensprache aus dem HTML-Lang-Attribut.

**Offene Schritte bis zur Production-Readiness**

- Abschnitts- und Heading-Erkennung für strukturierte Inhalte.
- Mehrsprachige Normalisierung sowie Domain-spezifische Tokenisierung.

