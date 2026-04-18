# Superhero Mail

## What This Is

Superhero Mail ist ein lokaler, DSGVO-konformer Open-Source-Mail-Client im Stil von Superhuman — aber 100% lokal, ohne Cloud, ohne Abo. Er bietet E-Mail-Superkraefte: Command Palette, Split Inbox, AI-Zusammenfassungen, Snooze, Send Later, Snippets und Follow-up-Reminders — alles betrieben durch lokale LLMs via Ollama. Das Projekt ist ein Fork/Umbau des bestehenden Mail AI Sorter.

## Core Value

Ich kann einen grossen Email-Eingang lokal, schnell und mit minimalen mentalen Aufwand sichten, beantworten und vorsortieren — mit Superhuman-Speed, aber ohne Cloud.

## Branding

- **Name:** Superhero Mail
- **Tagline:** "E-Mail-Superkraefte — 100% lokal, 100% dein."
- **Farbschema:** Electric Blue (#3B82F6) + Weiss
- **Icon:** Blitz-Symbol

## Requirements

### Validated

- ✓ Lokale Web-UI fuer Dashboard, Konfiguration, Inbox, Logs, Stats und Setup ist vorhanden — existing
- ✓ IMAP-basierte Inbox, Ordnernavigation und Unified Inbox ueber mehrere Konten sind vorhanden — existing
- ✓ Lokale Suche ueber indizierte Emails ist vorhanden — existing
- ✓ Email-Detailansicht mit Thread-Hinweisen, Anhaengen, Tags und Bulk-Aktionen ist vorhanden — existing
- ✓ LLM-gestuetzte Zusammenfassungen, Analyse und Quick-Reply-Entwuerfe sind vorhanden — existing
- ✓ Hintergrund-Sortierung mit Daemon-State, Quiet Hours und Health/Telegram-Basis ist vorhanden — existing

### Active

- [ ] Die App fuehlt sich als schneller, minimalistischer lokaler Mail-Client fuer taegliche Triage und Bearbeitung an.
- [ ] Email-Threads sind uebersichtlich, schnell lesbar und fuer Antwort-Workflows optimiert.
- [ ] Suche ist schnell genug und alltagstauglich, um Mails wie in einem modernen Power-User-Client direkt wiederzufinden.
- [ ] Antworten auf Emails lassen sich in 80-90 % der Faelle mit LLM-generierten oder vordefinierten Bausteinen schnell fertigstellen.
- [ ] Neue Emails werden erst verarbeitet, nachdem Paperless sie eingelesen hat und mindestens 30 Minuten vergangen sind.
- [ ] Die automatische Sortierung verteilt Emails kontrolliert auf Zielordner und verarbeitet pro Account maximal 15 Emails je Lauf.
- [ ] Die lokale, Open-Source- und DSGVO-konforme Betriebsweise bleibt auch bei weiterem Ausbau erhalten.

### Out of Scope

- Mobile App — Web/Desktop reicht fuer v1, mobile Clients kommen spaeter.
- Mehrbenutzerbetrieb — initialer Fokus ist Einzelperson/local-first statt geteilter Arbeitsflaeche.
- Cloud-Sync oder Cloud-Zwang — bewusst ausgeschlossen, um lokale Kontrolle und DSGVO-Konformitaet zu erhalten.
- Team- und Kollaborationsfunktionen — fuer v1 nicht Teil des Kernwerts.

## Context

Das bestehende Projekt ist bereits ein Brownfield-Codebase mit Flask-Web-UI, Route-/Service-Schicht, IMAP/SMTP-Anbindung, lokalem SQLite-Index, lokaler LLM-Integration ueber Ollama, RAG ueber indizierte Emails sowie Telegram- und Daemon-Unterstuetzung. Der aktuelle Ausbau ist funktional schon in Richtung intelligenter Mail-Client gegangen, aber das Produktziel soll jetzt klar auf einen alltagstauglichen, schnellen lokalen Email-Client mit starker Antwort- und Triage-Ergonomie fokussiert werden. Die automatische Vorsortierung soll mit dem bestehenden Oekosystem zusammenspielen, insbesondere mit Paperless als vorgelagertem Verarbeitungsschritt.

## Constraints

- **Betriebsmodell**: Lokal, Open Source und DSGVO-konform — keine Pflicht-Cloud, keine externe SaaS-Abhaengigkeit.
- **LLM-Strategie**: Lokale Modelle ueber Ollama — Antworten, Zusammenfassungen und Assistenz sollen ohne Cloud-API funktionieren.
- **Integration**: Paperless muss im Vorsortierungsablauf beruecksichtigt werden — Mails sollen erst nach dessen Einlesezeit weiterverarbeitet werden.
- **Produktfokus**: V1 ist vor allem starker Client + Antwortworkflow — moderne UX wichtiger als Feature-Breite.
- **Kontrollierbarkeit**: Automatische Sortierung bleibt bewusst gedrosselt — maximal 15 Emails pro Account je Lauf.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local-first statt Cloud-first | Datenschutz, DSGVO und Unabhaengigkeit vom Abo-Modell sind Kern des Produkts | — Pending |
| Brownfield auf bestehender App statt kompletter Neubau | Es existiert bereits nutzbare Funktionalitaet fuer Inbox, Suche, LLM und Sortierung | — Pending |
| Client- und Antwort-Workflow vor voller Automationsbreite priorisieren | Der groesste Alltagswert entsteht zuerst beim Lesen, Finden und Beantworten vieler Emails | — Pending |
| Superhuman-inspirierte UX — jetzt als "Superhero Mail" | Die App soll sich schnell und fokussiert anfuehlen, lokal/offen bleiben, und als eigenstaendiges Produkt positioniert werden | — Active (Phase 0 Rebranding) |
| Flask zu FastAPI Migration | FastAPI bietet bessere Typsicherheit, async, OpenAPI-Docs und passt besser zum Stack | — Active (Phase 0) |
| Paperless-verzoegerte Sortierung als Kernworkflow | Die automatische Verarbeitung soll mit dem bestehenden Dokumentenfluss zusammenspielen statt davor zu greifen | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-17 after initialization*
