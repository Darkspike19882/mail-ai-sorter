# Mail AI Sorter

Lokaler, DSGVO-konformer Mail-Client mit KI-gestuetzter Vorsortierung und Antwortunterstuetzung. Alles laeuft lokal — keine Cloud, kein Abo, kein Tracking.

## Was es kann

**Mail-Client**
- Unified Inbox ueber mehrere IMAP-Konten
- Thread-Aufloesung (Message-ID / In-Reply-To / References)
- Email-Detail mit HTML/Text, Anhaengen, Tags, Thread-Timeline
- Bulk-Aktionen: Gelesen, Stern, Loeschen, Verschieben, Taggen
- Pagination und Kontext-Persistenz (URL + localStorage)

**Suche & KI-Frage**
- Volltextsuche ueber FTS5 (Betreff, Absender, Body, Keywords)
- Filter nach Konto, Ordner, Zeitraum (7/30/90 Tage)
- Gelbe Match-Snippets in den Suchergebnissen
- KI-Frage-Panel: Frage an alle Emails, Antwort mit Quellenangaben, direkter Link zur Ursprungs-Email

**Antworten**
- Inline-Composer im Detail-Pane (kein Modal fuer Antworten)
- KI-Entwurf mit Thread-Kontext, 4 Ton-Optionen (Freundlich, Formal, Kurz, Bestimmt)
- Vorlagen-System mit CRUD, Picker-Dropdown, KI-Anpassung
- Draft-Auto-Save (localStorage, 1s Debounce)
- Compose-Modal fuer neue Emails mit Anhaengen

**Automatisierung**
- Sorter: Regeln, Absender-Cache, LLM-Klassifizierung (15 Kategorien)
- 30-Min-Delay fuer Paperless-ngx Integration
- Daemon mit Start/Pause/Stop/Quiet-Hours
- Sortier-Historie in SQLite mit Begruendung pro Aktion
- Review-UI: Tabelle mit Stats, farbcodierten Method-Badges

**KI (alles lokal via Ollama)**
- Email-Analyse (Prioritaetsscore, Ton, Handlungsbedarf)
- Zusammenfassungen, Antwortentwuerfe, Vorlagen-Anpassung
- RAG Q&A ueber Mail-Corpus
- Smart Digest (Tagesbericht via Telegram)

**Tastaturkuerzel**
- `/` Suchen, `?` KI-Frage, `r` Antworten, `Escape` Schliessen, `Strg+Enter` Senden

## Tech Stack

| Komponente | Technologie |
|------------|-------------|
| Backend | Python, Flask, SQLite (FTS5), APScheduler |
| Frontend | Alpine.js, Tailwind CSS (CDN), Lucide Icons |
| KI | Ollama (lokal), llama3.1:8b / gemma4:e4b |
| Persistenz | SQLite (7 Tabellen: conversations, user_facts, email_summaries, rag_queries, email_embeddings, email_tags, reply_templates, sort_actions) |
| Deployment | Lokal, spaeter Tauri 2 fuer Desktop-Shell |

## Projektstruktur

```
mail-ai-sorter/
├── web_ui.py              # Flask-Bootstrap + Blueprint-Registrierung
├── config_service.py      # Gemeinsame Config/Secrets-Schicht
├── memory.py              # SQLite-Persistenz (Migrationen, Batch-Lookups)
├── llm_helper.py          # Ollama-Wrapper (Chat, Analyze, Reply, Adapt)
├── rag_engine.py          # RAG ueber FTS5-Index
├── sorter.py              # Kern-Sortierlogik (Regeln/Cache/LLM/Delay)
├── sorter_daemon.py       # Hintergrund-Daemon
├── smtp_client.py         # SMTP mit STARTTLS + Reply-Header
├── index.py               # FTS5-Index CLI
├── health_monitor.py      # Health-Checks + Telegram-Alerts
├── routes/                # 10 Flask-Blueprints
│   ├── page_routes.py     # Seiten (Dashboard, Inbox, Config, Logs, Stats)
│   ├── inbox_routes.py    # IMAP/Suche/Flags/Bulk/Send
│   ├── llm_routes.py      # KI-Analyse, Quick-Reply, Adapt-Template
│   ├── rag_routes.py      # RAG Q&A, Status, History
│   ├── template_routes.py # Vorlagen CRUD
│   ├── sorter_routes.py   # Daemon-Steuerung, Sortier-Historie
│   ├── config_routes.py   # Konfiguration
│   ├── memory_routes.py   # Memory/Facts
│   ├── health_routes.py   # Health-Check
│   └── telegram_routes.py # Telegram-Integration
├── services/              # Service-Layer
│   ├── imap_service.py    # IMAP-Verbindung, Mail-Liste, Detail, Flags
│   ├── inbox_service.py   # Dekoration, Smart-Priorities, Batch-Lookups
│   ├── llm_service.py     # LLM-Orchestrierung
│   ├── rag_service.py     # RAG-Wrapper
│   ├── stats_service.py   # Dashboard-Statistiken
│   └── sorter_service.py  # Daemon-State, Sorter-Steuerung
├── templates/             # 7 HTML-Templates (Jinja2 + Alpine.js)
│   ├── base.html
│   ├── dashboard.html
│   ├── inbox.html         # Haupt-Inbox mit allen Features
│   ├── configuration.html
│   ├── logs.html          # Logs + Sortier-Historie
│   ├── stats.html
│   └── setup.html
└── .planning/             # GSD-Roadmap, Requirements, Phase-Artefakte
```

## Schnellstart

### Voraussetzungen

- macOS (Apple Silicon empfohlen)
- Python 3.11+
- [Ollama](https://ollama.ai) mit einem installierten Modell

### Installation

```bash
git clone https://github.com/Darkspike19882/mail-ai-sorter.git
cd mail-ai-sorter
python3 -m venv venv
source venv/bin/activate
pip install flask requests beautifulsoup4 lxml dominate schedule
```

### Ollama einrichten

```bash
# Ollama installieren (falls nicht vorhanden)
brew install ollama

# Modell herunterladen
ollama pull llama3.1:8b

# Ollama starten
ollama serve
```

### App starten

```bash
source venv/bin/activate
python3 web_ui.py
```

Dann http://localhost:5001 im Browser oeffnen.

### Ersteinrichtung

1. Setup-Wizard: http://localhost:5001/setup
2. Email-Konto anlegen (IMAP-Zugaenge fuer Gmail, iCloud, GMX etc.)
3. KI-Modell waehlen (llama3.1:8b empfohlen)
4. Sorter konfigurieren (Kategorien, Regeln, Delay)

## Konfiguration

- `config.json` — App-Konfiguration (Konten, Kategorien, Regeln, KI-Einstellungen)
- `secrets.env` — Passwoerter, API-Tokens (gitignored)
- `state.json` — Daemon-Zustand

### IMAP-Hinweise

- **Gmail**: [App-Passwort erstellen](https://support.google.com/accounts/answer/185833)
- **iCloud**: [App-spezifisches Passwort](https://support.apple.com/de-de/HT204397)
- **GMX/Web.de**: [IMAP aktivieren](https://hilfe.gmx.net/e-mail/pop3-imap/imap-zugang.html)

## Sortierung

### Kommandozeile

```bash
# Testlauf (nichts aendern)
./run.sh --dry-run --max-per-account 10

# Echte Sortierung
./run.sh --max-per-account 50

# Alle Mails
./run.sh --all --max-per-account 100
```

### Daemon (automatisch)

Der Daemon laeuft im Hintergrund und sortiert im konfigurierten Intervall. Gesteuert ueber die Web-UI oder die API:

- Start: `POST /api/sorter/start`
- Pause: `POST /api/sorter/pause`
- Stop: `POST /api/sorter/stop`

### Sortier-Logik

1. **Regeln** — User-definierte Regeln nach Absender/Betreff
2. **List-Unsubscribe** — Newsletter-Erkennung via Header
3. **Cache** — Gelernte Absender-Kategorie-Zuordnungen
4. **LLM** — KI-Klassifizierung als Fallback

Jede Aktion wird mit Methode und Begruendung in der Datenbank gespeichert und in der Review-UI angezeigt.

### Paperless-Integration

Neue Emails werden erst nach Ablauf der konfigurierten Verzoegerung (Standard: 30 Min) verarbeitet. Das gibt Paperless Zeit fuer die PDF-Extraktion.

## KI-Modelle

| Modell | RAM | Speed | Empfehlung |
|--------|-----|-------|------------|
| llama3.1:8b | ~7GB | Schnell | Beste Balance |
| gemma4:e4b | ~10GB | Mittel | Hohe Praezision |
| phi3:mini | ~5GB | Sehr schnell | Minimum |

## Roadmap

- [x] **Phase 1**: Unified Inbox & Thread Reading
- [x] **Phase 2**: Search & Grounded Retrieval
- [x] **Phase 3**: Fast Reply Workflow
- [x] **Phase 4**: Delayed Sorting & Reviewability
- [ ] **Phase 5**: Local-First Trust & Deployment (Tauri-Shell, Deployment-Haertung)

## Lizenz

MIT License — siehe [LICENSE](LICENSE)
