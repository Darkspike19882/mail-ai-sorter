# Requirements: Mail AI Sorter

**Defined:** 2026-04-17
**Core Value:** Ich kann einen grossen Email-Eingang lokal, schnell und mit minimalem mentalem Aufwand sichten, beantworten und vorsortieren.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Inbox & Threads

- [ ] **INBX-01**: User can read emails from multiple configured accounts in a unified inbox.
- [ ] **INBX-02**: User can open a conversation in a thread-centered view instead of reading isolated messages only.
- [ ] **INBX-03**: User can navigate quickly within a thread and between thread list and detail view.

### Search

- [ ] **SRCH-01**: User can run fast full-text search across indexed emails.
- [ ] **SRCH-02**: User can restrict search results by account and folder.
- [ ] **SRCH-03**: User can search with context that includes attachment/document content where available.
- [ ] **SRCH-04**: User can ask AI-assisted answer/search questions over the local mail corpus and see grounded results.

### Compose & Reply

- [ ] **RPLY-01**: User can generate an LLM-based reply draft from the current email or thread context.
- [ ] **RPLY-02**: User can use predefined reply snippets/templates for recurring email cases.
- [ ] **RPLY-03**: User can combine snippets/templates with AI adaptation so the draft fits the current case.
- [ ] **RPLY-04**: User can reply and compose in a fast, minimal composer optimized for high email volume.

### Automation & Sorting

- [ ] **AUTO-01**: Email automation waits at least 30 minutes before processing a newly arrived message.
- [ ] **AUTO-02**: Email automation only proceeds after the message is eligible according to the Paperless-driven workflow.
- [ ] **AUTO-03**: User can have emails automatically distributed into target folders.
- [ ] **AUTO-04**: User can review, understand, and control sorting actions instead of relying on opaque automation.

### Local-First Operations

- [ ] **LOCL-01**: User can use the app without any required cloud service for core mail, search, and AI workflows.
- [ ] **LOCL-02**: User can use AI-assisted features through local LLM execution.
- [ ] **LOCL-03**: User can operate the app in a way that supports a local, DSGVO-conscious deployment model.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Triage Workflow

- **TRIA-01**: User can triage email primarily with keyboard-first shortcuts and command-style actions.
- **TRIA-02**: User can snooze or schedule follow-up/reminder-style actions for emails.

### Automation Controls

- **AUTO-05**: User can enforce a maximum number of automatically processed emails per account per run.

### Search Enhancements

- **SRCH-05**: User can use richer AI answer/search workflows over larger local history and attachment sets.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Mobile App | Web/Desktop first; mobile is not required to validate the product's core value |
| Multi-user support | Initial product is single-user and local-first |
| Cloud sync / cloud dependency | Conflicts with local-first, open-source, DSGVO-conscious positioning |
| Team collaboration / shared inbox workflow | Not part of the initial single-user product thesis |
| Fully autonomous send/reply agent | Too risky for trust, correctness, and product fit in v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INBX-01 | TBD | Pending |
| INBX-02 | TBD | Pending |
| INBX-03 | TBD | Pending |
| SRCH-01 | TBD | Pending |
| SRCH-02 | TBD | Pending |
| SRCH-03 | TBD | Pending |
| SRCH-04 | TBD | Pending |
| RPLY-01 | TBD | Pending |
| RPLY-02 | TBD | Pending |
| RPLY-03 | TBD | Pending |
| RPLY-04 | TBD | Pending |
| AUTO-01 | TBD | Pending |
| AUTO-02 | TBD | Pending |
| AUTO-03 | TBD | Pending |
| AUTO-04 | TBD | Pending |
| LOCL-01 | TBD | Pending |
| LOCL-02 | TBD | Pending |
| LOCL-03 | TBD | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 0
- Unmapped: 18 ⚠️

---
*Requirements defined: 2026-04-17*
*Last updated: 2026-04-17 after initial definition*
