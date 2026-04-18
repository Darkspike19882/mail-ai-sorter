# Datenschutzerklärung — Superhero Mail

**Stand:** April 2026
**Version:** 1.0.0

---

## 1. Übersicht

Superhero Mail ist ein lokaler, Open-Source-E-Mail-Client mit KI-gestützter Vorsortierung und Antwortunterstützung. Die Anwendung wurde entwickelt, um einen grossen E-Mail-Eingang lokal, schnell und mit minimalem mentalem Aufwand zu sichten, beantworten und vorsortieren.

**Grundprinzipien:**

- **Lokal-first:** Alle Daten bleiben auf dem Gerät des Nutzers. Es gibt keine Cloud-Dienste, keine Telemetrie, kein Analytics.
- **DSGVO-bewusst:** Die Anwendung ist als Single-User-Desktop-App konzipiert, die Datenverarbeitung findet ausschliesslich lokal statt.
- **Open Source:** Der vollständige Quellcode ist einsehbar und auditierbar.
- **Kein Cloud-Zwang:** Kernfunktionen (E-Mail, Suche, KI) funktionieren ohne Internetverbindung mit dem Mail-Server (ausser beim Abruf/Versand).

Die KI-Funktionen nutzen ausschliesslich lokale LLMs über Ollama. Es werden keine Cloud-KI-APIs (OpenAI, Anthropic, Google AI etc.) verwendet.

---

## 2. Dateninventar (Data Inventory)

Die folgende Tabelle zeigt alle Arten von Daten, die Superhero Mail speichert, wo sie gespeichert werden, wie lange sie aufbewahrt werden und wofür sie verwendet werden:

| Datenart | Speicherort | Aufbewahrung | Verschlüsselung | Zweck |
|----------|-------------|-------------|-----------------|-------|
| E-Mail-Metadaten (Betreff, Von, Datum) | SQLite (mail_index.db) | Bis zur Löschung durch Nutzer | Nein (nur lokal) | Suche, Thread-Ansicht |
| E-Mail-Inhalt (Body) | SQLite (mail_index.db) | Bis zur Löschung durch Nutzer | Nein (nur lokal) | Suche, KI-Verarbeitung |
| E-Mail-Anhänge (Metadaten) | SQLite (mail_index.db) | Bis zur Löschung durch Nutzer | Nein (nur lokal) | Übersicht der Anhänge |
| Suchindex (FTS5) | SQLite (mail_index.db) | Bis zur Löschung durch Nutzer | Nein (nur lokal) | Volltextsuche |
| KI-Konversationsverlauf | SQLite (llm_memory.db) | Bis zur Löschung durch Nutzer | Nein (nur lokal) | Kontinuität der KI-Antworten |
| E-Mail-Zusammenfassungen | SQLite (llm_memory.db) | Bis zur Löschung durch Nutzer | Nein (nur lokal) | Schnelle Übersicht |
| Nutzerfakten & Präferenzen | SQLite (llm_memory.db) | Bis zur Löschung durch Nutzer | Nein (nur lokal) | Personalisierte KI-Antworten |
| Sortieraktionen-Log | SQLite (mail_index.db) | Bis zur Löschung durch Nutzer | Nein (nur lokal) | Nachvollziehbarkeit der automatischen Sortierung |
| Konto-Konfiguration | config.json | Dauerhaft | Nein | App-Konfiguration |
| IMAP-Passwörter | OS-Schlüsselbund (Keychain/SecretService) | Dauerhaft | Ja (OS-verwaltet) | Mail-Server-Zugriff |
| Telegram-Bot-Token (optional) | OS-Schlüsselbund / secrets.env | Dauerhaft | Ja | Benachrichtigungen (optional) |

**Hinweis:** Die IMAP-Passwörter werden nicht in config.json oder in Klartextdateien gespeichert. Stattdessen wird der OS-native Schlüsselbund (macOS Keychain, Linux Secret Service, Windows Credential Manager) über die `keyring`-Bibliothek verwendet.

---

## 3. Netzwerkflüsse (Network Flows)

Die folgenden Netzwerkverbindungen werden von Superhero Mail hergestellt:

| Ziel | Daten | Protokoll | Konfigurierbar |
|------|-------|-----------|----------------|
| IMAP-Server | Login-Daten, E-Mail-Lese/-Verschiebeaktionen | IMAP over TLS | Ja (Nutzer-konfigurierter Server) |
| SMTP-Server | Ausgehende E-Mails | SMTP over TLS | Ja (Nutzer-konfigurierter Server) |
| Ollama (localhost) | E-Mail-Inhalt für KI-Verarbeitung | HTTP (nur localhost) | Ja (URL & Modell konfigurierbar) |
| Paperless-ngx (optional, localhost) | E-Mail-Metadaten für Dokumentenablage | HTTP (nur localhost) | Ja (URL & Token konfigurierbar) |
| Telegram (optional) | Benachrichtigungen | HTTPS | Ja (Token & Chat-ID konfigurierbar) |

**Alle externen Verbindungen (IMAP, SMTP, Telegram) sind nutzerkonfigurierbar.** Es gibt keine versteckten oder fest codierten externen Verbindungen zu Cloud-Diensten.

---

## 4. Daten die NIEMALS die Maschine verlassen

Die folgenden Daten werden unter keinen Umständen über das Netzwerk übertragen:

- **E-Mail-Inhalt** (ausser bei aktivem Versand durch Nutzer via SMTP)
- **KI-Konversationsverlauf**
- **Suchindex** (FTS5)
- **Kontopasswörter** (werden nur an den Nutzer-konfigurierten IMAP/SMTP-Server gesendet)
- **Nutzerfakten und Präferenzen**
- **Sortieraktions-Logs**
- **Datenbankinhalte** (mail_index.db, llm_memory.db)

---

## 5. Keine Cloud-Dienste

Diese Anwendung verwendet **KEINE** der folgenden Dienste:

- **Cloud-Speicher oder Sync** — Keine Dropbox, Google Drive, iCloud etc.
- **Cloud-KI-APIs** — Kein OpenAI, Anthropic, Google AI, Cohere, Hugging Face Inference
- **Analytics oder Telemetrie** — Keine Nutzungsdaten werden erfasst oder übertragen
- **Crash-Reporting-Dienste** — Kein Sentry, Bugsnag, Crashlytics
- **Werbenetzwerke** — Keine Werbung
- **Externe Tracking-Dienste** — Keine Pixel, Cookies oder Fingerprinting

Die Abwesenheit von Cloud-Abhängigkeiten wird automatisiert durch `tests/test_no_cloud_deps.py` verifiziert. Dieser Test scannt den gesamten Codebase nach Verbindungen zu bekannten Cloud-Diensten und stellt sicher, dass keine unbeabsichtigten externen Verbindungen existieren.

---

## 6. Aufbewahrungsfristen (Retention)

| Datenart | Aufbewahrungsdauer | Löschung |
|----------|-------------------|----------|
| E-Mail-Daten (Metadaten + Inhalt) | Bis zur manuellen Löschung durch den Nutzer | `DELETE /api/data/delete` |
| KI-Daten (Konversationen, Fakten) | Bis zur manuellen Löschung durch den Nutzer | `DELETE /api/data/delete` |
| Sortieraktions-Logs | Bis zur manuellen Löschung durch den Nutzer | `DELETE /api/data/delete` |
| Konto-Konfiguration | Dauerhaft bis zur Deinstallation | Manuell über Einstellungen |
| Passwörter im OS-Schlüsselbund | Dauerhaft bis zur Löschung | `DELETE /api/data/delete` |

**Es gibt keine automatische Datenablaufung.** Alle lokalen Daten bleiben so lange gespeichert, bis der Nutzer sie explizit löscht. Der Nutzer hat die volle Kontrolle über die Aufbewahrungsdauer.

---

## 7. Nutzerrechte (User Rights) — DSGVO

Als Nutzer von Superhero Mail haben Sie die folgenden Rechte gemäss der Datenschutz-Grundverordnung (DSGVO):

| Recht | Beschreibung | Wie | API |
|-------|-------------|-----|-----|
| Recht auf Auskunft (Art. 15) | Sie können alle über Sie gespeicherten Daten einsehen | Alle Daten als ZIP exportieren | `GET /api/data/export` |
| Recht auf Löschung (Art. 17) | Sie können die Löschung aller Ihrer Daten verlangen | Alle Datenbanken und Passwörter löschen | `DELETE /api/data/delete` |
| Recht auf Datenübertragbarkeit (Art. 20) | Sie können Ihre Daten in einem strukturierten Format erhalten | Daten als ZIP exportieren (SQLite-Dump + JSON) | `GET /api/data/export` |

**Export-Format:** Der Datenexport erstellt eine ZIP-Datei mit:
- SQL-Dump aller SQLite-Datenbanken (mail_index.db, llm_memory.db)
- Konfiguration als JSON (ohne Passwörter)
- Diese Datenschutzerklärung (PRIVACY.md)
- Export-Metadaten (Zeitpunkt, App-Version)

**Hinweis zum Löschvorgang:** Die Löschung ist irreversibel. Alle E-Mails, KI-Daten und gespeicherten Passwörter werden unwiderruflich gelöscht. Die Konto-Konfiguration in config.json bleibt erhalten, damit die App weiterhin gestartet werden kann.

---

## 8. Sicherheitsmassnahmen

Superhero Mail implementiert die folgenden Sicherheitsmassnahmen:

### 8.1 Transportverschlüsselung
- **IMAP/SMTP:** Alle Verbindungen zu Mail-Servern nutzen TLS mit `ssl.create_default_context()`. Unsichere Verbindungen werden nicht unterstützt.
- **Ollama:** Kommunikation mit dem lokalen LLM über HTTP (nur localhost, Port 11434).

### 8.2 Passwortsicherheit
- **OS-Schlüsselbund:** IMAP-Passwörter werden im OS-native Schlüsselbund gespeichert (macOS Keychain, Linux Secret Service, Windows Credential Manager).
- **Kein Klartext:** Passwörter werden nicht in config.json, secrets.env oder anderen Klartextdateien gespeichert.
- **Keyring-Bibliothek:** Die `keyring` Python-Bibliothek (v25.7+) stellt die Integration mit dem OS-Schlüsselbund sicher.
- **Automatische Migration:** Bestehende Klartext-Passwörter werden beim ersten Start automatisch in den OS-Schlüsselbund migriert.

### 8.3 Netzwerksicherheit
- **Content Security Policy (CSP):** Blockiert externe Requests im Browser. Nur localhost und konfigurierte CDNs (Tailwind, jsdelivr, unpkg) sind erlaubt.
- **Lokale Bindung:** FastAPI lauscht nur auf localhost (127.0.0.1). Kein Zugriff aus dem lokalen Netzwerk.
- **Keine externen APIs:** Der Code enthält keine Verbindungen zu Cloud-APIs. Dies wird automatisiert geprüft.

### 8.4 KI-Sicherheit
- **Lokale LLMs:** Alle KI-Verarbeitung erfolgt über Ollama mit lokalen Modellen (z.B. llama3.1:8b).
- **Keine Cloud-API:** Keine Daten werden an externe KI-Dienste gesendet.
- **Graceful Degradation:** Wenn Ollama nicht verfügbar ist, funktioniert die App weiterhin ohne KI-Funktionen.

---

## 9. Automatisierte Verifikation

Die Sicherheits- und Datenschutzmassnahmen werden durch automatisierte Tests verifiziert:

| Test | Zweck | Datei |
|------|-------|-------|
| Cloud-Dependency-Check | Verifiziert Abwesenheit von Cloud-Abhängigkeiten im Code | `tests/test_no_cloud_deps.py` |
| Credential-Security-Test | Verifiziert Keychain-Integration und Passwort-Speicherung | `tests/test_credential_security.py` |
| Data-API-Test | Verifiziert Datenexport und -löschung | `tests/test_data_api.py` |

Diese Tests können jederzeit mit `python3 -m pytest tests/ -v` ausgeführt werden, um die Integrität der Datenschutzmassnahmen zu überprüfen.

---

## 10. Kontakt & Verantwortlichkeit

Superhero Mail ist ein Open-Source-Projekt. Bei Fragen zum Datenschutz:

- **Quellcode:** Vollständig einsehbar und auditierbar
- **Datenverantwortlicher:** Der Nutzer selbst (Single-User, lokal)
- **Datenverarbeitung:** Findet ausschliesslich auf dem Gerät des Nutzers statt

**Zusammenfassung:** Superhero Mail verarbeitet alle Daten lokal auf Ihrem Gerät. Es gibt keine Cloud-Dienste, keine Telemetrie, keine externen KI-APIs. Sie haben jederzeit die volle Kontrolle über Ihre Daten durch Export- und Lösch-APIs.
