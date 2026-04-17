# Project Research Summary

**Project:** Mail AI Sorter
**Domain:** local-first AI-powered desktop/web mail client and sorter
**Researched:** 2026-04-17
**Confidence:** HIGH

## Executive Summary

Mail AI Sorter should be built as a local-first, single-user power mail client with AI as assistive augmentation, not as an autonomous agent. The research is unusually consistent: strong products in this category win on triage speed, thread readability, fast search, and low-friction reply workflows; the local/privacy differentiator only matters if the app is also fast and trustworthy enough to replace a daily-driver inbox. Experts build this kind of product around a canonical local mail store, projection-driven search/thread read models, and optional AI services layered on top rather than embedded in the core request path.

The recommended approach is a brownfield modernization: keep Python as the local service boundary, move from Flask toward FastAPI + Pydantic, make SQLite + FTS5 the canonical local persistence/search layer, and build the primary UX in React/Vite, with Tauri added only when desktop packaging becomes a milestone goal. Product scope should stay tight around unified inbox, thread-first reading, powerful local search, keyboard-heavy triage, reply drafting, and delayed Paperless-aware automation with explicit reviewability and per-account caps.

The biggest risks are structural, not cosmetic: unstable IMAP identity handling, brittle threading on messy real-world headers, UI latency caused by local LLM calls in the interaction path, unsafe automation before trust is earned, and SQLite contention once sync/indexing/automation all run concurrently. Mitigation is clear from the research: UID-based canonical identity, rebuildable local thread/search projections, assistive AI with auditability and undo, explicit delayed-automation state machines, and storage hardening before advanced search and automation scale-up.

## Key Findings

### Recommended Stack

The stack recommendation is opinionated and cohesive: use Python for the local backend, SQLite as the product's durable local truth, and a modern React client for the fast triage UX. This keeps the existing brownfield code path viable while replacing the weakest long-term pieces: Flask for typed app boundaries and ad hoc UI/service coupling for a clearer API + projection architecture.

**Core technologies:**
- **FastAPI + Pydantic (Python 3.12/3.13):** typed local API/service boundary — better fit than Flask for async workflows, schema validation, and frontend contracts.
- **SQLite + FTS5 + SQLAlchemy + Alembic:** canonical local data store and search index — simplest reliable way to support local-first search, projections, and schema evolution.
- **React 19 + TypeScript + Vite:** primary inbox/thread/search/composer UI — best fit for a fast, keyboard-heavy client shell.
- **TanStack Query / Router / Virtual:** stateful client ergonomics — supports cached reads, deep linking, and large mailbox virtualization.
- **Ollama + official Python client:** local LLM runtime — preserves the local-only AI constraint without extra orchestration layers.
- **Tauri 2:** desktop packaging shell — use later for distribution, not as the first milestone bottleneck.

**Critical versions:**
- FastAPI **0.136.x** with Pydantic **2.13.x**
- SQLAlchemy **2.0.49** with Alembic **1.18.x**
- React **19.2.x** with Vite **8.0.x**
- Tauri CLI/API kept on **2.10.x** together
- SQLite **3.45+** preferred with FTS5 enabled

### Expected Features

The research is clear that v1 must feel like a real mail client first and an AI product second. Table stakes are unified inbox, strong thread reading, fast search, keyboard triage, core triage actions, send later/follow-up support, and privacy/account compatibility messaging. The project's differentiated wedge is not “autonomous AI email,” but controlled local-first assistance: reply drafting, human-in-the-loop triage, delayed automation tied to Paperless readiness, and eventually answer-mode search with citations.

**Must have (table stakes):**
- **Fast unified inbox + thread-centric reading** — core daily-driver baseline.
- **Powerful local search including thread and attachment recall** — necessary for both user value and credible AI assist.
- **Keyboard-first triage workflow** — required for the intended power-user positioning.
- **Core triage actions** — archive, delete, snooze, labels/tags, bulk actions, mute, star/pin.
- **AI thread summary + reply draft assistance** — minimum AI value that directly saves time.
- **Delayed/background sorting with reviewability and per-account caps** — signature workflow, not an add-on.

**Should have (competitive):**
- **Human-in-the-loop AI triage queue** — safer than full automation and aligned with trust.
- **Inbox work-queue states** — Needs reply / Waiting / Review later improves session-based triage.
- **Snippets/templates + AI personalization** — strong fit for the 80–90% reply completion goal.
- **Answer-mode AI search with citations** — differentiating if retrieval quality is already strong.
- **Per-account throttled automation with audit trail** — makes caution a product feature.

**Defer (v2+):**
- **Team/shared inbox collaboration** — out of scope for the local single-user thesis.
- **Mobile parity and cross-device sync** — too much surface area for v1.
- **Autonomous send/reply agents** — high trust risk, weak fit for launch.
- **Large-scale semantic-first search** — secondary to exact/local lexical recall.

### Architecture Approach

The architectural throughline is to treat IMAP as upstream transport, but the local database as the application's read source of truth. Core boundaries should be: sync/reconciliation, canonical mail store, thread/search projections, automation engine with durable waiting states, and an assistive LLM sidecar that enriches existing local data rather than controlling baseline UX. The UI should only read local projections; sync, indexing, and automation should run asynchronously with explicit state and auditing.

**Major components:**
1. **Sync engine + canonical mail store** — normalize remote mail once using UID-based identities and persist it locally.
2. **Read-model services for inbox/thread/search** — serve fast local projections instead of live IMAP reads.
3. **Automation engine** — enforce Paperless gating, cooldown windows, run caps, and auditability.
4. **LLM assist service** — provide summaries, reply drafts, classification, and retrieval augmentation as optional enrichment.
5. **UI shell** — deliver keyboard-first triage, thread reading, compose, settings, and status views.

### Critical Pitfalls

The research says the roadmap should be organized around avoiding structural failures early, not patching them later.

1. **Unstable IMAP identity handling** — use `(account, mailbox, UIDVALIDITY, UID)` as canonical remote identity and test expunge/reconnect cases early.
2. **Fragile threading on messy headers** — use a proven threading approach, support placeholder parents, and keep thread cache rebuildable.
3. **Unsafe AI automation before trust exists** — default to suggestions, explanations, undo, audit logs, and bounded automation windows.
4. **Blocking the client on local LLM latency** — keep LLMs off the interaction path, stream long outputs, and cache/generated states explicitly.
5. **SQLite contention under concurrent reads/writes** — use WAL intentionally, keep transactions short, and monitor busy errors/checkpoint health.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Local Data Foundation
**Rationale:** Everything else depends on a trustworthy canonical local model; this is where the highest-cost mistakes happen.
**Delivers:** UID-based message/account/folder/thread/attachment schema, migrations, local source-of-truth rules, backup/restore assumptions, and initial repository boundaries.
**Addresses:** Unified inbox, thread view, search, local-first privacy posture.
**Avoids:** IMAP identity drift, fake local-first architecture, future migration pain.

### Phase 2: Sync and Read-Model Performance
**Rationale:** The product only becomes believable once inbox and thread reads are local, fast, and decoupled from IMAP latency.
**Delivers:** Per-account sync engine, checkpoints, idempotent reconciliation, inbox/thread APIs, virtualization-ready list models, and async refresh behavior.
**Uses:** FastAPI, Pydantic, SQLite/SQLAlchemy, React, TanStack Query/Virtual.
**Implements:** Sync engine, canonical store, inbox/thread query services.
**Avoids:** Live-IMAP UI, slow list rendering, unstable triage state.

### Phase 3: Search and Threading Reliability
**Rationale:** Search quality and trustworthy conversation views are core launch features and prerequisites for credible AI assist.
**Delivers:** FTS5-backed search projection, attachment-aware indexing, rebuildable thread cache, thread/detail read models, and corpus tests for broken headers.
**Addresses:** Powerful local search, thread-first reading, attachment-aware context.
**Avoids:** Thread fragmentation, poor recall, re-threading jank, attachment-blind AI.

### Phase 4: Fast Triage UX
**Rationale:** This is the user-visible phase that converts infrastructure into a daily-driver client.
**Delivers:** Keyboard-first navigation, bulk actions, explicit selection/focus state, command semantics, reversible triage actions, and a polished inbox/thread/composer flow.
**Addresses:** Keyboard-first triage workflow, core triage actions, send-later/follow-up-adjacent workflows.
**Avoids:** Focus brittleness, unstable optimistic actions, mouse-dependent workflows.

### Phase 5: Delayed Automation and Auditability
**Rationale:** The product's most distinctive workflow should ship only after state, trust, and visibility exist.
**Delivers:** Durable automation job table, Paperless eligibility states, 30-minute delay enforcement, per-account max-15 throttles, audit history, dry-run/undo surfaces, and explainable suggestions.
**Addresses:** Smart inbox prioritization, delayed sorting, human-in-the-loop triage foundations.
**Uses:** APScheduler, SQLite durable jobs, adapter boundaries for Paperless and IMAP actions.
**Avoids:** Premature moves, hidden delays, unsafe opaque automation.

### Phase 6: Assistive AI for Summary and Reply
**Rationale:** AI should consume a stable product foundation, not define it.
**Delivers:** Cached thread summaries, structured-context reply drafting, rewrite actions, snippets/templates, LLM availability states, and optional answer-mode search if retrieval quality is proven.
**Addresses:** AI summary, reply draft assistance, snippets/templates, answer-mode search.
**Uses:** Ollama sidecar, prompt contracts, local caches, search/thread context assembly.
**Avoids:** One-shot hallucinated replies, blocking UI on inference, over-trusted AI actions.

### Phase Ordering Rationale

- **Data model before UX** because inbox, search, automation, and AI all depend on stable local identity and projections.
- **Sync/read models before richer features** because any feature built on live IMAP reads will feel slow and brittle.
- **Search and threading before advanced AI** because summaries, reply drafting, and answer mode only become trustworthy when retrieval and thread context are solid.
- **Automation after auditability** because the project's differentiator is controlled delayed sorting, not autonomous demo magic.
- **AI last in the dependency chain but early in user value** because it should enhance a fast client, never hold it hostage.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3: Search and Threading Reliability** — threading heuristics on messy mail and attachment extraction/index quality merit deeper design validation.
- **Phase 5: Delayed Automation and Auditability** — Paperless integration edge cases, eligibility invariants, and undo/audit model need phase-specific research.
- **Phase 6: Assistive AI for Summary and Reply** — prompt contracts, context packaging, and per-action quality measurement deserve additional phase research.

Phases with standard patterns (skip research-phase):
- **Phase 1: Local Data Foundation** — well-documented stack and schema patterns.
- **Phase 2: Sync and Read-Model Performance** — established local-projection architecture for mail clients.
- **Phase 4: Fast Triage UX** — interaction design is hard, but the core implementation patterns are conventional enough to proceed directly.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Strong official-doc coverage and clear convergence around a modern local-first Python + React + SQLite + Ollama stack. |
| Features | HIGH | Competitive landscape is clear and aligned with project constraints; strong signal from current market leaders. |
| Architecture | HIGH | Recommendations are internally consistent, grounded in current brownfield context, and backed by official protocol/storage docs. |
| Pitfalls | MEDIUM | High-quality sources and good domain fit, but some guidance is inference-heavy and needs validation against this codebase's exact behavior. |

**Overall confidence:** HIGH

### Gaps to Address

- **Threading algorithm choice:** validate whether a JWZ-style implementation is sufficient or if project-specific heuristics are needed for imported/malformed mail.
- **Attachment extraction pipeline:** define which file types are indexed in v1 and how extraction failures affect search/AI quality.
- **Backup/restore product boundary:** decide what counts as canonical local intelligence and how export/recovery is exposed to users.
- **Paperless readiness contract:** clarify the concrete readiness signal and correlation mechanism before automating against it.
- **Desktop packaging timing:** decide whether Tauri enters the first roadmap or remains a later packaging milestone after the web UX stabilizes.
- **Privacy hardening details:** verify logging, notification redaction, secret storage, and crash/alert behavior before wider adoption.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — product goals, constraints, brownfield context, and scope boundaries.
- https://v2.tauri.app/start/ — Tauri 2 positioning and architecture flexibility.
- https://v2.tauri.app/concept/inter-process-communication/brownfield/ — brownfield embedding approach.
- https://v2.tauri.app/develop/sidecar/ — packaged sidecar support.
- https://fastapi.tiangolo.com/ — FastAPI capabilities and current guidance.
- https://docs.pydantic.dev/latest/ — Pydantic v2 baseline.
- https://docs.sqlalchemy.org/en/20/ and https://alembic.sqlalchemy.org/en/latest/ — ORM/migration standards.
- https://www.sqlite.org/fts5.html and https://www.sqlite.org/wal.html — local search and WAL/concurrency behavior.
- https://docs.ollama.com/api and https://docs.ollama.com/api/streaming — local LLM integration and streaming behavior.
- https://docs.python.org/3/library/imaplib.html and RFCs https://www.rfc-editor.org/rfc/rfc9051 , https://www.rfc-editor.org/rfc/rfc3501 , https://www.rfc-editor.org/rfc/rfc2683 — IMAP identity, resync, and protocol pitfalls.
- Paperless-ngx docs: https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/usage.md and https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/configuration.md — ingest/worker model and readiness constraints.
- Official product pages for Superhuman, Shortwave, Spark, Canary, and Thunderbird — competitive feature baselines and positioning.

### Secondary (MEDIUM confidence)
- PyPI and npm registry version lookups from 2026-04-17 — current package/version validation.
- https://github.com/mjs/imapclient — IMAPClient library status and positioning.
- https://www.inkandswitch.com/essay/local-first/ — local-first design principles.
- https://www.jwz.org/doc/threading.html — foundational threading approach reference.

### Tertiary (LOW confidence)
- No major low-confidence external source drove the roadmap; remaining uncertainty is mostly implementation-specific rather than source-quality-specific.

---
*Research completed: 2026-04-17*
*Ready for roadmap: yes*
