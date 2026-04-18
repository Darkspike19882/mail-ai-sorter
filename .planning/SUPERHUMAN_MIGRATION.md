# Superhuman-Migration Plan

## Ziel
Einen lokalen, DSGVO-konformen Email-Client im Superhuman-Stil bauen:
- **Lokal-First** (kein Cloudzwang)
- **Offline-fähig**
- **Keyboard-first** UI
- **Schnell** (<50ms Interaktionen)
- **Lokale AI** (Ollama)

---

## Phase 1: Foundation (Woche 1-2)

### 1.1 Tauri + React Setup
```
Aufgaben:
□ Tauri 2.x Projekt erstellen (brownfield mit Python sidecar)
□ React 19 + TypeScript + Vite integrieren
□ TanStack Query für Server-State
□ TanStack Virtual für Mail-Listen
□ Tailwind CSS für Styling

Deliverable: Leere Shell, die Python-Backend startet
```

### 1.2 Basis-UI Components
```
Aufgaben:
□ Inbox-Liste (virtualisiert, 10k+ Items)
□ Thread-View
□ E-Mail-Composer
□ Sidebar mit Ordnern
□ Keyboard-Navigation

Deliverable: MVP-UI mit Grundfunktionen
```

### 1.3 FastAPI Migration
```
Aufgaben:
□ Flask → FastAPI migrieren
□ Pydantic Models für alle Endpoints
□ Typed Request/Response

Deliverable: Vollständige FastAPI API
```

---

## Phase 2: Local-First Architecture (Woche 3-4)

### 2.1 Lokale Datenbank
```
Aufgaben:
□ SQLite + FTS5 als primäre DB
□ Email-Cache lokal speichern
□ Such-Index on-demand

Entscheidung:
- SQLite-WASM für Tauri oder
- Python Sidecar mit SQLite

Technologie: SQLite 3.45+, SQLAlchemy 2.0, Alembic
```

### 2.2 Offline-Mode
```
Aufgaben:
□ IMAP-Sync im Hintergrund
□ Lokale Kopie aller Emails
□ Sync-Status anzeigen

Pattern:
┌──────────┐     ┌──────────┐
│  UI      │────►│ Lokale DB │
│ (lesen)   │◄────│          │
└──────────┘     └──────────┘
                      │
                      ▼ Sync im Hintergrund
                 ┌──────────┐
                 │  IMAP    │
                 │ Server   │
                 └──────────┘
```

### 2.3 Optimistic UI
```
Aufgaben:
□ Aktionen sofort sichtbar machen
□ Background-Sync
□ Conflict-Handling (Last-Write-Wins)

Beispiel:
- Email lesen → sofort "gelesen" anzeigen
- Sortieren → sofort in Liste verschieben
- Später mit IMAP synchronisieren
```

---

## Phase 3: Sync Engine (Woche 5-6)

### 3.1 CRDT-Implementierung
```
Optionen:
┌─────────┬──────────┬─────────┐
│ Library │ Komplex  │ Nutzung │
├─────────┼──────────┼─────────┤
│ Yjs     │ Mittel   │ Text    │
│ Loro    │ Niedrig  │ Alles   │
│ RxDB    │ Niedrig  │ NoSQL   │
│ Custom  │ Hoch     │ Volle   │
└─────────┴──────────┴─────────┘

Empfehlung: Loro (beste Performance, Rust-basiert)
```

### 3.2 Multi-Device Sync
```
Aufgaben:
□ Änderungen tracken (Lamport-Clock)
□ Konflikt-Merge (CRDT)
□ Sync-Queueverwaltung

Flow:
┌────────┐    ┌────────┐    ┌────────┐
│ Device │    │ Sync   │    │ Server│
│   A   │◄──►│Engine │◄──►│(Backup)│
└────────┘    └────────┘    └────────┘
     │                           │
     └───────────────────────────┘
        Byte-Level Sync (CRDT)
```

---

## Phase 4: AI Integration (Woche 7-8)

### 4.1 Lokale Embeddings
```
Aktuell (bleibt):
□ Ollama für Text-Generierung
□ Zusammenfassungen
□ Reply-Drafts

Neu:
□ Ollama Embeddings für Semantic Search
□ Hybrid Search: FTS5 + Embeddings
□ Vektor-Suche lokal

Keine externe Vector-DB nötig!
```

### 4.2 AI-Features (Superhuman-Style)
```
Features:
□ Write with AI → Draft generieren
□ Auto-Summarize → Langen Email zusammenfassen
□ Instant Reply → Schnellantwort
□ Ask AI → Über Email suchen/fragen
```

---

## Phase 5: Performance & Polish (Woche 9-10)

### 5.1 Speed Optimizations
```
□ Prefetching → Nächste Emails beim Scrollen laden
□ Pre-warming → AI-Index beim Start "wärmen"
□ Debounced Search → Nicht bei jedem Tastendruck
□ Virtualization → Nur sichtbare Items rendern
```

### 5.2 Keyboard Shortcuts
```
Navigation:
j/k     →上一行/下一行
Enter   → Thread öffnen
a       → Answer (Reply)
r       → Reply
f       → Forward
u       → Unread
x       → Archive
e       → Snooze

Commands:
 Cmd+K  → Command Palette
 /      → Search
```

---

## Technologie-Stack Zusammenfassung

| Phase | Technologie | Status |
|-------|-------------|--------|
| 1 | Tauri 2, React 19, TypeScript | ✓ Stack Research |
| 1 | TanStack Query/Virtual | ✓ Stack Research |
| 2 | SQLite + FTS5 + SQLAlchemy | - Todo |
| 2 | Offline-first Pattern | - Todo |
| 3 | Loro oder RxDB | - Todo |
| 4 | Ollama + Local Embeddings | - Todo |
| 5 | Keyboard Shortcuts | - Todo |

## Was NICHT brauchen (im Gegensatz zu Superhuman)

| Superhuman | Dein Projekt |
|-----------|-------------|
| turbopuffer | SQLite + FTS5 ✓ |
| Cloud LLMs | Ollama lokal ✓ |
| Google Cloud | Lokal/GitHub ✓ |
| Electron | Tauri (besser) ✓ |
| Realm | SQLite ✓ |

---

## Prioritäten-Reihenfolge

```
1. Tauri + React Shell zum Laufen bringen
2. Inbox mit Virtualisierung (Tempo!)
3. FastAPI Migration
4. Lokaler SQLite-Cache
5. Keyboard Shortcuts
6. Ollama AI-Features
7. CRDT Sync (falls Multi-Device)
```

## Warnung

> **Local-First ist mehr als nur Offline-Caching.**
> Es erfordert komplette Neuarchitektur der Datenflüsse.
> Superhuman hat ~50 Engineers dafür.
> **Start small, iterate.**

---