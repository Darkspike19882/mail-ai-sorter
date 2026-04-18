# Roadmap: Superhero Mail

## Overview

Superhero Mail ist der Umbau von Mail AI Sorter zu einem Superhuman-inspirierten, lokalen Mail-Client. Phase 0 etabliert das neue Branding + FastAPI, danach folgen Command Palette, Split Inbox, AI-Features und weitere Superhuman-Features.

## Phases

- [x] **Phase 1: Unified Inbox & Thread Reading** - Users can read and move through mail across accounts in a thread-first workflow.
- [x] **Phase 2: Search & Grounded Retrieval** - Users can find mail and ask grounded questions over the local corpus.
- [x] **Phase 3: Fast Reply Workflow** - Users can finish replies quickly with a minimal composer, snippets, and local AI drafting.
- [x] **Phase 4: Delayed Sorting & Reviewability** - Users can rely on bounded automation that waits, explains itself, and stays controllable.
- [ ] **Phase 5: Superhero Rebranding + FastAPI** - Rebranding zu Superhero Mail + Migration von Flask zu FastAPI.
- [ ] **Phase 6: Command Palette (Cmd+K)** - Zentrale Suchleiste fuer alle Aktionen, Keyboard-First.
- [ ] **Phase 7: Split Inbox + Inline AI Summary** - Multiple Inbox-Views + 1-Zeilen-KI-Zusammenfassung.
- [ ] **Phase 8: Snooze + Send Later** - Zeitgesteuerte Wiedervorlage und Senden.
- [ ] **Phase 9: Snippets + Follow-ups + Inbox Zero** - Templates, Follow-up-Reminders und Celebration-Animation.

## Phase Details

### Phase 1: Unified Inbox & Thread Reading
**Goal**: Users can read and navigate email from multiple accounts in one coherent, thread-centered client workflow.
**Depends on**: Nothing (first phase)
**Requirements**: INBX-01, INBX-02, INBX-03
**Success Criteria** (what must be TRUE):
  1. User can open one unified inbox that shows mail from multiple configured accounts.
  2. User can open a conversation in a thread-centered view instead of reading messages in isolation.
  3. User can move quickly between the message list and thread detail without losing context.
**Plans**:
  1. Plan 1 - Harden Unified Inbox Data Flow
  2. Plan 2 - Make Reading Truly Thread-Centered
  3. Plan 3 - Preserve Navigation Context And Verify Phase 1
**UI hint**: yes

### Phase 2: Search & Grounded Retrieval
**Goal**: Users can reliably rediscover emails and get grounded answers from their local mail history.
**Depends on**: Phase 1
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04
**Success Criteria** (what must be TRUE):
  1. User can run fast full-text search across indexed emails.
  2. User can narrow search results by account and folder when looking for a specific message set.
  3. User can find emails using context from attached or extracted document content when that content is available locally.
  4. User can ask AI-assisted questions over the local mail corpus and see grounded results tied back to source emails.
**Plans**: 3 plans
- [x] 02-01-PLAN — Backend search enhancements (extend search API + FTS filters + Ollama health check)
- [x] 02-02-PLAN — AI Q&A backend + frontend panel (RAG history endpoint + AI panel drawer)
- [x] 02-03-PLAN — Frontend search enhancements (filter chips + match snippets + keyboard shortcuts)
**UI hint**: yes

### Phase 3: Fast Reply Workflow
**Goal**: Users can complete most replies quickly with a focused composer and local AI assistance.
**Depends on**: Phase 2
**Requirements**: RPLY-01, RPLY-02, RPLY-03, RPLY-04, LOCL-02
**Success Criteria** (what must be TRUE):
  1. User can open a fast, minimal composer for replies and new outbound messages.
  2. User can generate a reply draft from the current email or thread context.
  3. User can insert predefined snippets/templates for recurring email cases.
  4. User can combine templates with AI adaptation so the final draft fits the current case while running against a local LLM.
**Plans**: 3 plans (executed inline)
**UI hint**: yes

### Phase 4: Delayed Sorting & Reviewability
**Goal**: Users can trust automatic sorting because it waits for the right moment, acts within clear limits, and remains understandable.
**Depends on**: Phase 3
**Requirements**: AUTO-01, AUTO-02, AUTO-03, AUTO-04
**Success Criteria** (what must be TRUE):
  1. Newly arrived mail is not processed by automation until at least 30 minutes have passed.
  2. Automation only proceeds when the message is eligible in the Paperless-aware workflow.
  3. User can have emails distributed into target folders automatically once they become eligible.
  4. User can review what sorting actions were taken or proposed and understand why they happened.
**Plans**: executed inline (existing sorter + sort_actions DB + review UI)
**UI hint**: yes

### Phase 5: Local-First Trust & Deployment
**Goal**: Users can adopt the app as a privacy-conscious daily driver without any required cloud dependency for core workflows.
**Depends on**: Phase 4
**Requirements**: LOCL-01, LOCL-03
**Success Criteria** (what must be TRUE):
  1. User can complete core mail, search, and AI-assisted workflows without any required cloud service.
  2. User can run the product in a local deployment model that keeps mail data and intelligence under local control.
  3. User can evaluate the app as consistent with its local, open-source, DSGVO-conscious positioning.
**Plans**: 2 plans
- [x] 05-01-PLAN — Credential security + network hardening + CSP (keyring migration, no-cloud test, CSP middleware)
- [x] 05-02-PLAN — Privacy documentation + data APIs (PRIVACY.md, export/delete endpoints)

### Phase 5: Superhero Rebranding + FastAPI
**Goal**: Rebrand zu Superhero Mail (Electric Blue, Blitz-Icon) und Migration von Flask zu FastAPI.
**Depends on**: Phase 4
**Requirements**: BRND-01, BACK-01
**Success Criteria** (what must be TRUE):
  1. Alle Templates zeigen "Superhero Mail" als Titel und Electric Blue als Farbschema.
  2. FastAPI ersetzt Flask als Backend, alle Routes funktionieren als APIRouter.
  3. Pydantic Models fuer alle Request/Response-Schemas.
  4. App startet und dient alle bestehenden Seiten korrekt aus.
**Plans**: TBD

### Phase 6: Command Palette (Cmd+K)
**Goal**: Zentrale Overlay-Suchleiste fuer alle Aktionen — Superhuman-Speed.
**Depends on**: Phase 5
**Requirements**: UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. Cmd+K oeffnet Command Palette Overlay.
  2. Fuzzy Search ueber alle Aktionen, Emails und Einstellungen.
  3. Jede Aktion per Tastatur ausfuehrbar.
**Plans**: TBD

### Phase 7: Split Inbox + Inline AI Summary
**Goal**: Split Inbox (Important/Newsletter/Alle) + 1-Zeilen-KI-Zusammenfassung pro Email.
**Depends on**: Phase 6
**Requirements**: UX-03, AI-01
**Plans**: TBD

### Phase 8: Snooze + Send Later
**Goal**: Emails zeitgesteuert wiedervorstellen und zeitverzoegert senden.
**Depends on**: Phase 7
**Requirements**: SNZ-01, SND-01
**Plans**: TBD

### Phase 9: Snippets + Follow-ups + Inbox Zero
**Goal**: Template-Bibliothek, Follow-up-Reminders und Inbox-Zero-Animation.
**Depends on**: Phase 8
**Requirements**: SNIP-01, FLLW-01, UX-04
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Unified Inbox & Thread Reading | 3/3 | Completed | 2026-04-17 |
| 2. Search & Grounded Retrieval | 3/3 | Completed | 2026-04-17 |
| 3. Fast Reply Workflow | 3/3 | Completed | 2026-04-17 |
| 4. Delayed Sorting & Reviewability | 1/1 | Completed | 2026-04-17 |
| 5. Local-First Trust & Deployment | 0/2 | Planned | - |
| 6. Command Palette (Cmd+K) | 0/TBD | Not started | - |
| 7. Split Inbox + Inline AI Summary | 0/TBD | Not started | - |
| 8. Snooze + Send Later | 0/TBD | Not started | - |
| 9. Snippets + Follow-ups + Inbox Zero | 0/TBD | Not started | - |

---
*Last updated: 2026-04-17 — Superhero Mail rebranding + new roadmap*
