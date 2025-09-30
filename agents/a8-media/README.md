# Agent A8 – Media

---

## 1. Übersicht / Rolle im System

Der **Media Agent (A8)** analysiert und bewertet alle **Medienressourcen** einer Website.
Schwerpunkt: Bilder, aber erweiterbar auf Videos, PDFs, Fonts.
Ziel: **Optimierungspotenzial erkennen** (Dateigröße, Format, Responsiveness, ALT-Texte, SEO-Relevanz).

Er liefert präzise **MediaReports**, die in den Renewal Plan (A10) einfließen und später beim Builder (A13) für automatische Optimierung genutzt werden (z. B. WebP-Generierung).

---

## 2. Eingaben / Ausgaben (Schemas)

### Eingabe

* **CrawlResult.json**

  ```json
  {
    "pages": [
      {
        "url": "https://www.example.com/",
        "images": [
          {"src": "/img/hero.jpg", "alt": ""}
        ],
        "html": "<html><body><img src='/img/hero.jpg'></body></html>"
      }
    ]
  }
  ```

### Ausgabe

* **MediaReport.json**

  ```json
  {
    "images": [
      {
        "url": "/img/hero.jpg",
        "bytes": 820000,
        "format": "jpeg",
        "dimensions": {"width": 1920, "height": 1080},
        "hasAlt": false,
        "webpCandidate": "/img/hero.webp",
        "issues": ["large-file", "missing-alt"]
      }
    ]
  }
  ```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **HTTP Fetch**: für Media-Assets (HEAD/GET → Content-Length, Content-Type)
* **Pillow (Python)** oder **ImageIO**: Bildanalyse (Größe, Format)
* **ExifTool (optional)**: Metadaten-Analyse
* **Parser**: BeautifulSoup/lxml für `<img>`, `<picture>`, `<source>`

### Algorithmen

* **Format-Erkennung**: MIME-Type + Magic Bytes
* **Dimension-Ermittlung**: Bilddatei öffnen oder `<img width/height>` auslesen
* **Dateigröße-Bewertung**: Schwellenwerte (>500 KB, >1 MB)
* **ALT-Text Check**: leere oder fehlende `alt`-Attribute markieren
* **Responsive Check**: `<picture>` und `srcset` prüfen
* **Optimierungsvorschlag**: Alternative Formate (WebP/AVIF) empfehlen

---

## 4. Externe Abhängigkeiten

* **Filesystem MCP**: Speichern von Reports
* **Fetch MCP**: Laden der Bilder (HEAD/GET)
* **Playwright MCP (optional)**: Screenshots/Rendering → Viewport-spezifische Darstellung
* **Memory MCP**: Historie speichern („Bildgröße reduziert von 820 KB → 120 KB“)

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * CrawlResult.json laden
   * Liste aller Media-Assets extrahieren

2. **Image Fetch**

   * HEAD-Requests → Größe + Typ
   * Fallback GET (bei fehlendem Content-Length)

3. **Metadata Analyse**

   * MIME + Magic Bytes prüfen
   * Abmessungen bestimmen
   * Exif-Daten (z. B. unnötige Metadaten)

4. **Accessibility Check**

   * ALT-Text vorhanden?
   * ALT-Text sinnvoll oder generisch („image.jpg“)?

5. **Performance Analyse**

   * Große Dateien → Optimierungsvorschlag
   * Nicht-optimierte Formate → WebP/AVIF-Kandidaten

6. **Responsive Analyse**

   * `<picture>` und `srcset` prüfen
   * Fehlende Responsive-Strategie markieren

7. **Output**

   * MediaReport.json mit Issues und Vorschlägen

---

## 6. Quality Gates & Non-Functional Requirements

* **Genauigkeit**: Formate und Größen müssen 100 % korrekt sein
* **Performance**: Analyse ≤ 1 Sekunde pro Bild (bei HEAD, ohne GET-Download)
* **Kompatibilität**: unterstützt JPEG, PNG, GIF, SVG, WebP, AVIF
* **Barrierefreiheit**: ALT-Texte müssen immer validiert werden
* **Nachvollziehbarkeit**: jedes Issue mit klarer Begründung

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Container mit Pillow/Fetch-Tools
* **Scaling**: Parallel-Analyse pro Bild (async IO)
* **Persistence**: Memory MCP für Bild-Historie
* **Observability**:

  * Logs: Anzahl Bilder, Ø-Bytes, ALT-Probleme
  * Metrics: Summe Einsparpotenzial (z. B. „10 MB → 3 MB möglich“)
  * Alerts: Wenn >20 % Bilder über 1 MB

---

## 8. Erweiterungspotenzial & offene Fragen

* **Video-Support**: Soll A8 auch MP4/WebM prüfen (Größe, Streaming)?
* **Font-Check**: Laden von Webfonts (TTF, WOFF2) analysieren?
* **Automatische Konvertierung**: Soll A8 selbst optimierte Kopien generieren oder nur Empfehlungen?
* **Lizenzprüfung**: Bilder auf Urheberrecht prüfen (Reverse Image Search, optional)?

---

📄 **Fazit**:
A8 liefert den **Medienoptimierungs-Report**. Ohne ihn bleiben Performance- und Accessibility-Probleme unsichtbar. Er ist direkt anschlussfähig an A10 (Plan), A11 (Content-Rewrite, z. B. ALT-Texte generieren) und A13 (Builder für WebP/AVIF).
