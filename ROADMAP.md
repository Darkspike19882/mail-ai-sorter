# Mail AI Sorter — Master-Bauplan

> Lokaler, selbstgehosteter KI-Email-Assistent. Alles läuft auf dem Mac. Keine Cloud. 100% Privat.
> Stand: April 2026 | Repo: github.com/Darkspike19882/mail-ai-sorter

---

## Architektur

```
┌─────────────────────────────────────────────────────────┐
│                    Web UI (Flask :5001)                  │
│  Dashboard · Inbox · Stats · Config · Logs · Setup      │
│  Tailwind CSS · Alpine.js · Chart.js · DOMPurify         │
├────────────┬──────────┬───────────┬──────────────────────┤
│ IMAP Layer │SMTP Layer│ Sorter    │ LLM Layer            │
│ Lesen/Flag │ Senden   │ Daemon    │ Ollama (llama3.1:8b) │
│ Folder/UID │ Reply/Fwd│ Poll-Loop│ RAG · Chat · Tags    │
├────────────┴──────────┴───────────┴──────────────────────┤
│              SQLite (FTS5 + Embeddings + Tags)           │
├─────────────────────────────────────────────────────────┤
│  Health Monitor · Telegram Bot · Secrets (secrets.env)  │
└─────────────────────────────────────────────────────────┘
```

---

## Referenz-Projekte & Inspirationen

| Projekt | Was wir daraus übernehmen | Phase |
|---------|--------------------------|-------|
| **SmartLayer/mailroom** (42★) | JSON-CLI Pattern, Link-Extraktion, Phishing-Check, MCP Server, OAuth2, Multi-Account Connection Handling | 4, 6 |
| **safhac/privemail** (3★) | Tone-Analyse, Smart-Priorisierung, Antwort-Vorschläge, Ollama/LM Studio Integration, OAuth2 Setup Wizard | 5 |
| **fatbobman/mail-mcp-bridge** (13★) | MCP Bridge Pattern, Calendar (ICS) Integration | 6 |
| **bberkay/openmail** (17★) | Privacy-First Pattern, Desktop-App Layout, IMAP/SMTP Self-Hosted | 7 |

---

## Phase 0 — Fundament ✅ ERLEDIGT

| Feature | Datei | Status |
|---------|-------|--------|
| Flask Web UI (6 Seiten) | `web_ui.py`, `templates/*.html` | ✅ |
| IMAP Email-Client (lesen/schreiben/antworten/weiterleiten) | `web_ui.py` | ✅ |
| SMTP mit 18 Provider-Presets + STARTTLS | `smtp_client.py` | ✅ |
| Ollama KI-Sortierung (llama3.1:8b / gemma4:e4b) | `sorter.py` | ✅ |
| Sorter-Daemon (Poll-Loop, Ruhezeiten, Start/Stop) | `sorter_daemon.py` | ✅ |
| Telegram Bot (@MacMiniCharlieBot) | `telegram_bot.py` | ✅ |
| LLM Helper (Digest, Chat, Summary, Memory) | `llm_helper.py` | ✅ |
| Statistiken (6 Charts, Zeitfilter) | `templates/stats.html` | ✅ |
| Attachment-Upload | `templates/inbox.html` | ✅ |
| Dark Mode (localStorage) | `templates/base.html` | ✅ |
| Tastaturkürzel (j/k/r/a/f/c/s/d/Esc) | `templates/inbox.html` | ✅ |
| Sicherheit (secrets.env, DOMPurify, XSS) | `secrets.env`, diverse | ✅ |
| Health Monitor + Telegram Alerts | `health_monitor.py` | ✅ |
| 3 Bugfix-Runden (29 Fixes) | alle Dateien | ✅ |

---

## Phase 1 — Ordner-Baum & Navigation ⏳ NÄCHSTE

**Inspiration**: Roundcube, Thunderbird — klassischer 3-Spalten-Layout mit aufklappbarem Ordner-Baum

### 1.1 Ordner-Baum in Sidebar
```
📁 Gmail ▾
  📥 INBOX (12)
  📤 Sent (3)
  🗂 Paperless (2)
  🛒 Einkauf (4)
  📰 Newsletter (6)
  🍎 Apple (1)
  ▸ Mehr anzeigen (14 weitere)
```
- **Accounts aufklappbar** (▸/▾ Toggle per Alpine.js `x-show`)
- **Unread-Count** pro Ordner → IMAP STATUS Befehl (UNSEEN)
- **Hierarchisch**: `INBOX/Subfolder` mit Einrückung (Delimiter aus IMAP LIST)
- **Aktiver Ordner** hervorheben (bg-primary-100)
- **Sync-Button** zum Neuladen der Ordner ohne Page-Refresh

### 1.2 Verbesserte Unified Inbox
- "Alle Konten" als Gruppierung ganz oben in der Sidebar
- Per-Account Badge in der Mail-Liste (farbcodiert)
- Schnellwechsel zwischen Unified und Account-View

### 1.3 Ordner-Operationen
- Rechtsklick-Kontextmenü auf Ordnern (Alpine.js Dropdown)
- Ordner erstellen / umbenennen / leeren via IMAP CREATE/RENAME/EXPUNGE
- Unread-Count automatisch aktualisieren (alle 30s)

### Technische Umsetzung
- Neuer Endpoint: `GET /api/folders/tree?account=Gmail` → hierarchische Struktur
- Neuer Endpoint: `GET /api/folders/unread?account=Gmail` → `{INBOX: 12, Sent: 0}`
- Sidebar-Template: rekursives Alpine.js Template für Ordner-Hierarchie
- IMAP: `conn.list()` → parse Delimiter + Hierarchie

**Aufwand**: ~3h

---

## Phase 2 — RAG (Retrieval-Augmented Generation)

**Inspiration**: Privemail (lokale AI-Suche), Mailroom (search + JSON)

### 2.1 Email-Index erweitern
- Aktuell: SQLite FTS5 nur mit Header-Daten (subject, from, category)
- **Neu**: Body-Text (erste 2000 Zeichen) in FTS5 Index aufnehmen
- Embedding-Index (optional): `nomic-embed-text` via Ollama → Vektor-Suche
- Incrementelle Indexierung: Sorter Daemon schreibt neue Emails direkt in Index

### 2.2 RAG-Pipeline
```
User: "Wann war die letzte Amazon-Bestellung?"
  ↓
1. FTS5 Suche: "Amazon Bestellung" → Top-5 Emails
2. Email-Bodies als Context (max 4000 Tokens)
3. An Ollama: System-Prompt + Context + Frage
4. Antwort mit Quellen: "Die letzte Amazon-Bestellung war am 12.04.2026 [→ Email]"
  ↓
Dashboard zeigt Antwort + klickbare Quell-Emails
```

### 2.3 RAG API Endpoints
- `POST /api/rag/query` — Natürliche Frage → `{answer, sources[{subject, date, account, folder, uid}]}`
- `GET /api/rag/status` — `{indexed_emails, last_index, embedding_model}`
- `POST /api/rag/reindex` — Index komplett neu aufbauen
- `POST /api/rag/embed` — Embeddings für alle Emails generieren (Background-Job)

### 2.4 RAG im Dashboard
- "Frag deine Emails" Inputfeld (ersetzt bestehenden KI-Chat)
- Antworten mit **klickbaren Quellen** → öffnet Email im Detail
- Vorschläge: "Was hat Amazon letzte Woche geschickt?", "Wie viele Rechnungen diesen Monat?"
- RAG-Statusanzeige: "142 Emails indiziert"

### 2.5 Embedding-Suche (Optional, erfordert nomic-embed-text)
```bash
ollama pull nomic-embed-text  # 274MB
```
- Jede Email → Embedding-Vektor via Ollama `/api/embeddings`
- SQLite Vektor-Erweiterung oder simple Cosine-Similarity
- Semantische Suche: "Reklamation" findet auch "Retoure" und "Defekt"

**Aufwand**: ~4h

---

## Phase 3 — Hashtags & Labels

**Inspiration**: Gmail Labels, Notmuch (tag-based Email), Lierre

### 3.1 Datenmodell
```sql
CREATE TABLE email_tags (
    email_id INTEGER,
    account TEXT,
    folder TEXT,
    uid TEXT,
    tag TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    source TEXT DEFAULT 'user',  -- 'user', 'ai', 'rule'
    PRIMARY KEY (email_id, tag)
);
CREATE INDEX idx_tags_tag ON email_tags(tag);
```

### 3.2 Tag-UI im Email-Detail
```
Tags: [#rechnung ×] [#amazon ×] [+ Tag hinzufügen]
```
- Autocomplete bestehender Tags (Alpine.js Dropdown)
- Klick auf Tag → filtert Mail-Liste nach diesem Tag
- Farbcodierung: automatisch generiert aus Tag-Name (Hash → HSL)

### 3.3 Tag-Sidebar
```
🏷️ Tags
  #rechnung (12)
  #amazon (8)
  #steuer (5)
  #wichtig (3)
  + alle anzeigen
```

### 3.4 KI-Auto-Tagging
- LLM analysiert Email-Inhalt und schlägt Tags vor
- Tags als Ergänzung zu Kategorien (feingranularer)
- Beispiel: Kategorie "Finanzen" → Tags: #rechnung, #steuer, #gehalt
- Vorschläge werden beim Sortieren generiert, User kann bestätigen/ändern
- `POST /api/tags/auto-suggest` → `{tags: ["rechnung", "amazon", "2026"]}`

### 3.5 Tag-basierte Suche & Filter
- Sucheingabe: `#rechnung` → filtert nach Tag
- Kombiniert: `#rechnung category:finanzen date:last7d`
- Neue Endpoint: `GET /api/search?tag=rechnung&category=finanzen&days=7`
- Tag-Cloud in Statistiken

**Aufwand**: ~3h

---

## Phase 4 — Bulk-Aktionen & Email-Workflow

**Inspiration**: Mailroom (CLI Automation), Gmail (Multi-Select)

### 4.1 Multi-Select
- Checkboxen in Mail-Liste (links neben jedem Absender-Avatar)
- "Alle auswählen" Toggle in Toolbar
- Shift+Click für Bereichsauswahl
- Ausgewählte Anzahl: "3 Emails ausgewählt"

### 4.2 Bulk-Toolbar (erscheint bei Auswahl)
```
[3 ausgewählt] Als gelesen | Verschieben ▾ | Löschen | Tag ▾ | ★ Flag
```
- Als gelesen/ungelesen markieren
- Verschieben in Ordner (Dropdown mit Ordner-Liste)
- Löschen (mit Bestätigungsdialog)
- Tags zuweisen/entfernen
- Flaggen setzen/entfernen

### 4.3 Bulk API
- `POST /api/bulk/read` → `{uids: [...], action: "read"}`
- `POST /api/bulk/move` → `{uids: [...], target_folder: "Archive"}`
- `POST /api/bulk/delete` → `{uids: [...]}`
- `POST /api/bulk/tag` → `{uids: [...], tags: ["rechnung"]}`

### 4.4 Unsubscribe-Button
- List-Unsubscribe Header erkennen (bereits im Header-Fetch)
- Button im Email-Header: "Abbestellen" (mailto: oder http://)
- Ein-Klick → öffnet Unsubscribe-URL oder generiert Reply

### 4.5 Link-Extraktion & Phishing-Check
**Inspiration**: Mailroom `links` Befehl
- Alle Links aus Email-HTML extrahieren und anzeigen
- Verdächtige Links markieren:
  - Display-Text ≠ tatsächliche URL
  - IP-Adresse statt Domain
  - URL-Shortener (bit.ly, t.co)
  - Bekannte Phishing-Domains
- LLM-basierter Phishing-Score (0-100%)

**Aufwand**: ~3h

---

## Phase 5 — LLM Deep Integration

**Inspiration**: Privemail (Tone-Analyse, Smart-Priorisierung, Antwort-Vorschläge)

### 5.1 Antwort-Vorschläge (Quick-Reply)
```
┌─────────────────────────────────────┐
│ 🤖 KI schlägt vor:                   │
│                                     │
│ [Freundlich] "Hallo, danke für..."  │
│ [Kurz]     "Danke, bekomme ich."    │
│ [Formell]  "Sehr geehrte(r)..."     │
│                                     │
│ [Selber schreiben]                  │
└─────────────────────────────────────┘
```
- 3 kurze Optionen generieren (verschiedene Tone-Level)
- One-Click Übernahme ins Compose-Feld
- Kontext: vorherige Emails im Thread beachten
- `POST /api/llm/suggest-reply` → `{replies: [{tone, text}]}`

### 5.2 Tone-Analyse & Prioritäts-Score
- Jede Email bekommt:
  - **Dringlichkeit**: hoch / mittel / niedrig
  - **Stimmung**: freundlich / neutral / wütend / dringend / werblich
  - **Aktion nötig**: ja / nein (Fragen, Fristen, Aufgaben)
- Visualisierung: farbige Badges im Email-Header
- Automatisch beim Sortieren generiert und gecacht

### 5.3 Scheduled Summary
- **Täglich** (konfigurierbare Uhrzeit): "Du hast 8 neue Emails, 2 wichtig, 1 Rechnung"
- **Wöchentlich** (Montag morgen): Wochenrückblick mit Kategorie-Verteilung
- Per Telegram oder als Email an sich selbst
- Cron-Job im Sorter-Daemon
- Konfigurierbar: welche Kategorien, Mindest-Wichtigkeit

### 5.4 Email-Summary in Listenansicht
- 1-Zeilige KI-Zusammenfassung direkt unter dem Betreff
- "Amazon: Deine Bestellung vom 12.04. wurde versendet"
- Lazy-Loading: nur für sichtbare Emails generieren
- Cache in SQLite `email_summaries` Tabelle

### 5.5 Smart Prioritäts-Inbox
- Neue View: "Wichtig" / "Normal" / "Kann warten"
- Sortierung nach: Wichtigkeit + Dringlichkeit + Absender-Häufigkeit + User-Verhalten
- LLM bewertet automatisch jede neue Email
- Lernt aus User-Aktionen (welche Emails werden gelesen, ignoriert, sofort beantwortet)

**Aufwand**: ~5h

---

## Phase 6 — MCP Server & Integrationen

**Inspiration**: Mailroom (MCP Server), mail-mcp-bridge (Calendar Bridge)

### 6.1 MCP Server
```
Claude/Desktop → MCP Protocol → Mail AI Sorter (:5002)
                                      ↓
                              IMAP / SMTP / SQLite
```
- Model Context Protocol Server auf Port 5002
- Tools für Claude/ChatGPT:
  - `search_emails(query, folder, limit)` → JSON
  - `read_email(account, folder, uid)` → Full Email
  - `send_email(to, subject, body)` → Send Confirmation
  - `summarize_emails(folder, days)` → Summary
  - `tag_email(uid, tags)` → Tags setzen
  - `move_email(uid, target_folder)` → Verschieben
- `pip install mcp` → MCP Server Skeleton

### 6.2 Webhook/Bridge
- Incoming Webhooks für Automatisierung
- `POST /api/webhook/new-email` → Trigger bei neuer Email
- Kategorien-Filter: nur Webhook für "rechnung" Emails
- n8n / Home Assistant kompatibel

### 6.3 Kalender-Integration
**Inspiration**: mail-mcp-bridge (ICS Parsing)
- ICS Attachments erkennen (Content-Type: text/calendar)
- .ics Download-Button
- Termin-Vorschau: Datum, Uhrzeit, Ort, Teilnehmer
- Parser: `icalendar` Python Package

### 6.4 Kontakt-Management
- Neue Seite: Kontakte
- Absender-Verlauf: letzte 5 Emails, Häufigkeit, Kategorie-Verteilung
- KI-generierte Kontakt-Notizen: "Regelmäßiger Amazon-Kunde, bevorzugt Elektronik"
- SQLite Tabelle: `contacts (email, name, last_seen, email_count, notes)`

**Aufwand**: ~6h

---

## Phase 7 — Export, Backup & PWA

**Inspiration**: Openmail (Desktop-App), Mailroom (Export)

### 7.1 Email Export
- Einzelne Email als **HTML** (Bilder eingebettet als base64)
- Bulk-Export als **EML/ZIP** (mehrere Emails auf einmal)
- **PDF-Export** für Rechnungen (via Browser print → PDF)
- `GET /api/email/{account}/{folder}/{uid}/export?format=html`

### 7.2 Backup & Restore
- Automatisches SQLite Backup (täglich, max 7 Backups)
- Config + Secrets Export als verschlüsseltes ZIP
- Restore-Funktion im Setup-Assistenten
- `POST /api/backup/create` → `/backups/backup_2026-04-16.zip`
- `POST /api/backup/restore` → Config + DB wiederherstellen

### 7.3 PWA (Progressive Web App)
- `manifest.json` → Installierbar als App (Handy/Desktop)
- Service Worker für Offline-Cache (zuletzt geladene Emails)
- Push-Notifications via Browser (neue wichtige Email)
- Responsive Mobile-Layout verbessern (Touch-Targets, Swipe-Aktionen)

**Aufwand**: ~5h

---

## Gesamtübersicht

```
Phase 0 ✅ ████████████████████████████████████ 30h  Fundament
Phase 1 ⏳ ████████                            3h   Ordner-Baum
Phase 2 📋 ██████████                          4h   RAG
Phase 3 📋 ████████                            3h   Hashtags
Phase 4 📋 ████████                            3h   Bulk-Aktionen
Phase 5 📋 █████████████                       5h   LLM Deep
Phase 6 📋 ████████████████                    6h   MCP & Integrationen
Phase 7 📋 █████████████                       5h   Export & PWA
         ████████████████████████████████████████
         Gesamt: ~59h
```

| Phase | Feature | Status | Aufwand | Inspiriert von |
|-------|---------|--------|---------|---------------|
| 0 | Fundament | ✅ | 30h | Eigenbau |
| 1 | Ordner-Baum & Navigation | ⏳ | 3h | Roundcube, Thunderbird |
| 2 | RAG (KI durchsucht Emails) | 📋 | 4h | Privemail, Mailroom |
| 3 | Hashtags & Labels | 📋 | 3h | Gmail Labels, Notmuch |
| 4 | Bulk-Aktionen & Workflow | 📋 | 3h | Mailroom, Gmail |
| 5 | LLM Deep Integration | 📋 | 5h | Privemail |
| 6 | MCP Server & Integrationen | 📋 | 6h | Mailroom, mail-mcp-bridge |
| 7 | Export, Backup & PWA | 📋 | 5h | Openmail, Mailroom |
| | **Gesamt** | | **~59h** | |

---

## Technologie-Stack

| Komponente | Aktuell | Phase 1-4 | Phase 5-7 |
|-----------|---------|-----------|-----------|
| Backend | Flask (Python) | Flask + Blueprint | Flask + Blueprint |
| Frontend | Tailwind CDN + Alpine.js | Gleich | Gleich |
| Datenbank | SQLite FTS5 | FTS5 + Body-Index | FTS5 + Embeddings |
| LLM | Ollama (llama3.1:8b) | + nomic-embed-text | + Multi-Model |
| Notifications | Telegram Bot | Telegram | Telegram + Browser Push |
| Suche | FTS5 Volltext | FTS5 + RAG | FTS5 + Vektor + RAG |
| Auth | Keine | Keine | Session-Based |
| API | REST | REST | REST + MCP |

---

## Neue Abhängigkeiten (nach Phase)

| Package | Phase | Zweck | Größe |
|---------|-------|-------|-------|
| `nomic-embed-text` (Ollama) | 2 | Embeddings für RAG | 274MB |
| `icalendar` | 6 | ICS Calendar Parsing | ~100KB |
| `mcp` | 6 | MCP Server SDK | ~2MB |

---

## Datei-Struktur (Geplant)

```
mail-ai-sorter/
├── web_ui.py              → aufteilen in:
│   ├── app.py             (Flask App, Blueprints)
│   ├── routes/
│   │   ├── email.py       (Inbox, Detail, Send, Flag)
│   │   ├── config.py      (Config, Accounts, SMTP)
│   │   ├── stats.py       (Stats, Detailed)
│   │   ├── telegram.py    (Bot Config, Verify, Send)
│   │   ├── llm.py         (Chat, Digest, Summary)
│   │   ├── rag.py         (RAG Query, Index, Status)
│   │   ├── tags.py        (Tags CRUD, Search)
│   │   └── health.py      (Health, Monitor)
│   └── helpers/
│       ├── imap.py        (IMAP Connect, Fetch, Parse)
│       ├── config.py      (Config Load/Save, Secrets)
│       └── utils.py       (Safe Int, Decode Header, etc.)
├── smtp_client.py
├── telegram_bot.py
├── llm_helper.py
├── rag_engine.py          (NEU - Phase 2)
├── tag_manager.py         (NEU - Phase 3)
├── health_monitor.py
├── mcp_server.py          (NEU - Phase 6)
├── sorter.py
├── sorter_daemon.py
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── inbox.html         (erweitert: Ordner-Baum, Bulk)
│   ├── stats.html
│   ├── configuration.html
│   ├── logs.html
│   ├── setup.html
│   └── contacts.html      (NEU - Phase 6)
├── config.json
├── secrets.env
├── ROADMAP.md
└── requirements.txt
```
