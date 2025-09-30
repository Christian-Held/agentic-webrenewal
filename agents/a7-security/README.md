# Agent A7 – Security

---

## 1. Übersicht / Rolle im System

Der **Security Agent (A7)** prüft die Zielwebsite (basierend auf den Daten aus A2 CrawlResult) auf **sicherheitsrelevante Schwächen**.
Er ist komplementär zu A4 (Tech-Fingerprint): während A4 Technologien erkennt, bewertet A7 deren **Sicherheitskonfiguration**.
Ziel: **frühe Identifikation von Risiken**, die in das Renewal-Angebot (A15) einfließen und rechtlich/vertraglich abgesichert dokumentiert werden können.

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
        "headers": {
          "server": "nginx",
          "x-powered-by": "PHP/7.4",
          "content-security-policy": "",
          "strict-transport-security": ""
        },
        "html": "<html>...</html>"
      }
    ]
  }
  ```

### Ausgabe

* **SecurityReport.json**

  ```json
  {
    "headers": {
      "hsts": false,
      "csp": false,
      "xframe": "SAMEORIGIN",
      "xcontenttype": false
    },
    "mixedContent": ["/page-x"],
    "tls": {
      "valid": true,
      "issuer": "Let's Encrypt",
      "expiresInDays": 54
    },
    "cookies": [
      {"name": "PHPSESSID", "secure": false, "httponly": true, "samesite": "Lax"}
    ],
    "risks": [
      {"id": "outdated-php", "severity": "high", "description": "PHP 7.4 unsupported since 2022"}
    ]
  }
  ```

---

## 3. Interne Abhängigkeiten

### Libraries / Technologien

* **HTTP Header Parser**: direkte Auswertung aus CrawlResult.headers
* **TLS-Inspector**: Python `ssl` oder externe Tools (z. B. `cryptography`)
* **Cookie-Parser**: Analyse `Set-Cookie` Header
* **Mixed-Content Detector**: Suche nach `http://`-Assets auf HTTPS-Seiten
* **Vulnerability Mapping**: Abgleich mit CVE-Listen basierend auf TechFingerprint (A4)

### Algorithmen

* **Header Validation**: prüfen auf HSTS, CSP, X-Frame-Options, X-Content-Type-Options
* **TLS Expiry**: Ablaufdatum + Issuer prüfen
* **Cookie Flags**: Secure, HttpOnly, SameSite setzen
* **Mixed Content**: In HTML nach http://-Assets suchen
* **Tech Match**: falls A4 → PHP 7.4 erkannt → bekannte CVEs markieren

---

## 4. Externe Abhängigkeiten

* **Fetch MCP**: HEAD-Requests für TLS und Header-Validierung
* **Playwright MCP**: DOM prüfen auf Mixed Content (nach Rendering)
* **Memory MCP**: Speicherung historischer SecurityReports (z. B. „TLS-Zertifikat erneuert“)
* **Filesystem MCP**: Reports sichern

---

## 5. Ablauf / Workflow intern

1. **Initialization**

   * CrawlResult laden
   * Header + TLS-Daten erfassen

2. **Header-Check**

   * CSP vorhanden?
   * Strict-Transport-Security gesetzt?
   * X-Frame-Options korrekt?
   * X-Content-Type-Options gesetzt?

3. **TLS Validation**

   * Zertifikat gültig?
   * Ablaufdatum?
   * Aussteller?

4. **Cookie Audit**

   * Flags gesetzt: Secure, HttpOnly, SameSite
   * Session-Cookies ohne Schutz → Warnung

5. **Mixed Content**

   * Suche nach `http://`-Assets in HTML
   * Playwright-Check auf Laufzeit-Assets

6. **Vulnerability Mapping**

   * Abgleich TechFingerprint (A4) → bekannte CVEs
   * Markieren als `risks`

7. **Scoring**

   * Score 0–100 (gewichtete Severity)

8. **Output**

   * SecurityReport.json mit Findings

---

## 6. Quality Gates & Non-Functional Requirements

* **Vollständigkeit**: alle relevanten Security-Header prüfen
* **Genauigkeit**: keine False Positives bei Mixed Content
* **Aktualität**: CVE-Datenbank regelmäßig aktualisieren
* **Performance**: ≤ 3 Sekunden pro Seite
* **Verwertbarkeit**: Ergebnisse laienverständlich für Kunden dokumentierbar

---

## 7. Skalierung, Deployment, Betrieb

* **Deployment**: Container mit SSL-Bibliotheken
* **Scaling**: parallel pro Domain oder pro 50 Seiten
* **Persistence**: Memory MCP für Delta-Security („Zertifikat läuft in 10 Tagen ab“)
* **Observability**:

  * Logs: Anzahl Header-Verstöße, TLS-Status
  * Alerts: Zertifikat < 14 Tage Restlaufzeit

---

## 8. Erweiterungspotenzial & offene Fragen

* **Deep CVE Integration**: Soll A7 aktiv NVD- oder OSV-Datenbanken abfragen?
* **Penetration Light**: Soll A7 rudimentäre Penetrationstests (z. B. Directory Traversal) versuchen oder nur passiv prüfen?
* **Zero Trust Reports**: Soll die Integration in Security SIEM-Systeme (z. B. Splunk) möglich sein?
* **Liability**: Muss das System einen Disclaimer zu „Advisory only“ liefern, um rechtliche Risiken zu minimieren?

---

📄 **Fazit**:
A7 ist der **Sicherheitsprüfer**. Er verbindet technische Header-Checks, TLS-Validierung und bekannte Schwachstellen mit verständlichen Reports. Grundlage für **Compliance, Risikoberatung und Preisschätzung** im Angebot.
