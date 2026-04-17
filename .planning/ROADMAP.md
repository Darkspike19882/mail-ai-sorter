# Roadmap: Mail AI Sorter

## Overview

This roadmap turns the existing brownfield app into a daily-driver local mail client by first locking in the core reading workflow, then making search and reply genuinely fast, then shipping controlled automation, and finally hardening the full product around its local-first and DSGVO-conscious promise.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Unified Inbox & Thread Reading** - Users can read and move through mail across accounts in a thread-first workflow.
- [ ] **Phase 2: Search & Grounded Retrieval** - Users can quickly find mail and ask grounded questions over the local corpus.
- [ ] **Phase 3: Fast Reply Workflow** - Users can finish replies quickly with a minimal composer, snippets, and local AI drafting.
- [ ] **Phase 4: Delayed Sorting & Reviewability** - Users can rely on bounded automation that waits, explains itself, and stays controllable.
- [ ] **Phase 5: Local-First Trust & Deployment** - Users can run the full product without required cloud dependencies and with a DSGVO-conscious operating model.

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
- [ ] 02-01-PLAN.md — Backend search enhancements (extend search API + FTS filters + Ollama health check)
- [ ] 02-02-PLAN.md — AI Q&A backend + frontend panel (RAG history endpoint + AI panel drawer)
- [ ] 02-03-PLAN.md — Frontend search enhancements (filter chips + match snippets + keyboard shortcuts)
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
**Plans**: TBD
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
**Plans**: TBD
**UI hint**: yes

### Phase 5: Local-First Trust & Deployment
**Goal**: Users can adopt the app as a privacy-conscious daily driver without any required cloud dependency for core workflows.
**Depends on**: Phase 4
**Requirements**: LOCL-01, LOCL-03
**Success Criteria** (what must be TRUE):
  1. User can complete core mail, search, and AI-assisted workflows without any required cloud service.
  2. User can run the product in a local deployment model that keeps mail data and intelligence under local control.
  3. User can evaluate the app as consistent with its local, open-source, DSGVO-conscious positioning.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Unified Inbox & Thread Reading | 3/3 | Completed | 2026-04-17 |
| 2. Search & Grounded Retrieval | 0/3 | Planning complete | - |
| 3. Fast Reply Workflow | 0/TBD | Not started | - |
| 4. Delayed Sorting & Reviewability | 0/TBD | Not started | - |
| 5. Local-First Trust & Deployment | 0/TBD | Not started | - |

---
*Granularity: standard (defaulted because no explicit granularity key exists in config.json)*
*Last updated: 2026-04-17 during phase 1 planning*
