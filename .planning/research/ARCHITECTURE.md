# Architecture Research

**Domain:** local-first AI mail client / intelligent email sorter
**Researched:** 2026-04-17
**Confidence:** HIGH

## Standard Architecture

### System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        Interaction Layer                            │
├──────────────────────────────────────────────────────────────────────┤
│  Web/Desktop UI  │  Keyboard-first triage  │  Reply composer        │
│  Search views    │  Thread/detail views    │  Logs/config/status    │
├──────────────────────────────────────────────────────────────────────┤
│                    Local Application Core                           │
├──────────────────────────────────────────────────────────────────────┤
│ Query/API layer │ Sync engine │ Search/indexer │ LLM assist service  │
│ Thread builder  │ Rule engine │ Deferred jobs  │ Reply/summarize/RAG │
├──────────────────────────────────────────────────────────────────────┤
│                    Persistence / Projections                        │
├──────────────────────────────────────────────────────────────────────┤
│ Canonical mail store │ FTS search index │ LLM memory │ job/state DB  │
├──────────────────────────────────────────────────────────────────────┤
│                       External Adapters                             │
├──────────────────────────────────────────────────────────────────────┤
│ IMAP/SMTP │ Ollama │ Paperless handoff/check │ notifications         │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| UI shell | Fast inbox, thread, search, composer, hotkeys | Web UI or desktop shell over local HTTP API |
| Query/API layer | Read-model endpoints for inbox/search/thread/actions | Flask/FastAPI handlers over local services |
| Sync engine | Pull mailbox changes, normalize message metadata/body/attachments, track remote UIDs | IMAP worker with per-account checkpoints |
| Canonical mail store | Local source of truth for app reads | SQLite tables for accounts, folders, messages, threads, attachments, flags |
| Search/indexer | Build query-optimized projection for instant search | SQLite FTS5 projection with triggers/rebuild jobs |
| Thread/materializer | Assemble message detail + thread graph for UI | Service over local DB, not repeated IMAP fetches |
| Automation engine | Rule evaluation, delayed processing, move/tag/archive actions | Background worker + durable job table |
| LLM assist service | Summaries, reply drafts, classification, RAG context assembly | Local Ollama adapter with prompt contracts and caching |
| External adapters | IMAP/SMTP/Paperless/Ollama boundary and retries | Small adapter modules isolated from core domain |

## Recommended Project Structure

```text
mail_ai_sorter/
├── app/
│   ├── api/                 # HTTP routes/blueprints only
│   ├── ui/                  # templates, static assets, view composition
│   ├── domain/              # message, thread, account, automation models
│   ├── services/
│   │   ├── sync/            # IMAP sync, checkpoints, reconciliation
│   │   ├── inbox/           # inbox query/read-model services
│   │   ├── search/          # FTS projection + query building
│   │   ├── threads/         # conversation assembly and reply context
│   │   ├── automation/      # delayed rules, Paperless gating, job runner
│   │   └── llm/             # summarize, classify, reply, RAG
│   ├── adapters/
│   │   ├── imap.py          # remote mail provider boundary
│   │   ├── smtp.py          # send/reply boundary
│   │   ├── ollama.py        # LLM boundary
│   │   └── paperless.py     # consume/check boundary
│   ├── repositories/        # sqlite reads/writes, no business policy
│   ├── jobs/                # scheduled/background entrypoints
│   └── state/               # daemon status, logs, config helpers
├── data/
│   ├── app.db               # canonical app database
│   ├── search.db            # FTS projection if split
│   └── llm.db               # cached summaries/reply history/memory
└── scripts/                 # local run/rebuild/migration commands
```

### Structure Rationale

- **api/** stays thin so UX work does not re-entangle IMAP, LLM, and automation logic.
- **services/sync + repositories/** enforce the most important boundary: remote mailbox state must be normalized once, then served locally many times.
- **services/automation/** should be separate from sync so “mail arrived” and “mail is allowed to be auto-processed now” remain different states.
- **adapters/** isolate volatile integrations: IMAP quirks, Ollama changes, and Paperless readiness checks should not leak into domain code.

## Architectural Patterns

### Pattern 1: Local projection over remote mailbox

**What:** Treat IMAP as the upstream system of record for transport, but treat the local database as the app’s read source of truth.
**When to use:** Always for a fast mail client UX.
**Trade-offs:** Requires sync/reconciliation code, but avoids slow screen loads and repeated network fetches.

**Example:**
```python
# UI never asks IMAP directly for inbox rendering.
def list_inbox(account_id: str, cursor: str | None):
    return inbox_repo.fetch_page(account_id=account_id, cursor=cursor)

def sync_account(account_id: str):
    remote_changes = imap_adapter.fetch_changes_since(last_uid_for(account_id))
    mail_repo.upsert_messages(remote_changes)
    search_projector.update(remote_changes)
```

### Pattern 2: Deferred automation pipeline

**What:** New mail ingestion and rule execution are separated by a durable waiting state.
**When to use:** Required here because Paperless must run first and automation must wait at least 30 minutes.
**Trade-offs:** More job state to manage, but prevents premature moves/sorts and preserves user trust.

**Example:**
```python
def on_message_ingested(message_id: str):
    jobs.enqueue(
        "automation_candidate",
        message_id=message_id,
        not_before=now() + timedelta(minutes=30),
    )

def run_automation_candidate(message_id: str):
    if not paperless_adapter.is_ready(message_id):
        return jobs.retry_later(message_id, delay_minutes=10)
    rules_engine.apply(message_id)
```

### Pattern 3: LLM as assistive sidecar, not core transaction path

**What:** Reading, searching, tagging, and replying must remain functional without the model.
**When to use:** Always in a local-first client where models can be slow or unavailable.
**Trade-offs:** Slightly more fallback logic, but much better reliability.

**Example:**
```python
def get_thread_view(thread_id: str):
    thread = thread_repo.get(thread_id)
    analysis = llm_cache_repo.get_thread_analysis(thread_id)
    return {"thread": thread, "analysis": analysis, "llm_available": ollama.is_up()}
```

## Data Flow

### Request Flow

```text
[User opens inbox]
    ↓
[UI]
    ↓
[Inbox API]
    ↓
[Inbox service]
    ↓
[Local mail store + FTS index]
    ↓
[Decorated read model: flags, thread hints, AI summary, tags]
    ↓
[UI renders immediately]
```

### State Management

```text
[Remote mailbox / local actions]
    ↓
[Sync + command handlers]
    ↓
[Canonical local DB]
    ↓
[Derived projections: inbox, threads, search, AI cache]
    ↓
[UI queries projections, not remote systems]
```

### Key Data Flows

1. **Mail ingest:** IMAP `UID`-based fetch → normalize headers/body/attachments → store in local DB → update thread projection → update FTS index. Python’s `imaplib` docs explicitly warn that message sequence numbers change and advise using UIDs; that boundary matters here.
2. **Fast triage:** UI inbox request → local query only → optional async refresh trigger in background. Do not block inbox paint on IMAP or Ollama.
3. **Thread reading:** local thread assembler → fetch cached analysis/tags → only fall back to on-demand body fetch if local body is missing.
4. **Reply assistance:** thread context + sender metadata + recent thread messages → prompt builder → Ollama `/api/chat` → draft stored separately from sent mail.
5. **Delayed automation:** ingest event → job enters `waiting_for_paperless` / `not_before` state → Paperless readiness check + 30-minute gate → rules evaluate → bounded actions (max 15/account/run).
6. **Search:** write/update message rows → FTS5 trigger/projector update → query API returns ranked snippets from local index.

## Suggested Build Order

1. **Canonical local mail model first**
   - Accounts, folders, messages, attachments, threads, flags, checkpoints.
   - This is the dependency for fast UX, search, automation, and LLM context.

2. **Sync engine + reconciliation second**
   - Per-account IMAP sync, UID checkpoints, idempotent upserts, conflict handling.
   - Without this, every later feature becomes network-coupled and brittle.

3. **Read-model APIs for inbox/thread/detail third**
   - Make the app feel fast before adding more AI.
   - Brownfield implication: move current IMAP-heavy reads behind local repositories first.

4. **Search/index projection fourth**
   - Add FTS-backed search over the local store, not a separate mail scrape path.

5. **Automation scheduler with Paperless gating fifth**
   - Add durable waiting states, job tables, rate limits, and audit logs before broader rules.

6. **LLM assistance last in the chain, but early in UX polish**
   - Summaries and reply drafts should consume existing thread/search context.
   - Keep outputs cached and optional so model latency never dictates baseline UX.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Single-user / local Mac | One process for web app + one background worker is enough; SQLite is the right default |
| Heavy personal archive | Split canonical DB and search/LLM cache DBs, add incremental sync and incremental projection rebuilds |
| Multi-account power-user | Per-account sync cursors, per-account job queues, aggressive local caching, attachment lazy-loading |
| Beyond local-first scope | Only then consider separate worker processes or a desktop shell; still avoid microservices |

### Scaling Priorities

1. **First bottleneck:** repeated IMAP reads in request path. Fix with local projections and async refresh.
2. **Second bottleneck:** search/index churn and large body payloads. Fix with incremental indexing, lazy attachment/body hydration, and cache invalidation discipline.

## Anti-Patterns

### Anti-Pattern 1: “Live IMAP UI”

**What people do:** Render inboxes and thread views by calling IMAP directly from request handlers.
**Why it's wrong:** UI latency, flaky behavior, difficult pagination, and poor offline/local feel.
**Do this instead:** Sync once into a canonical local store; serve all normal reads from local projections.

### Anti-Pattern 2: Mixing ingestion and automation

**What people do:** Move/sort messages immediately when first seen.
**Why it's wrong:** Breaks the Paperless-first requirement, complicates reprocessing, and makes automation hard to trust.
**Do this instead:** Model explicit states: `ingested` → `waiting_for_paperless` → `eligible_for_automation` → `processed`.

### Anti-Pattern 3: LLM in the critical path

**What people do:** Require classification or reply generation before rendering or storing mail.
**Why it's wrong:** Local models are variable in latency and availability.
**Do this instead:** Persist mail first; enrich asynchronously; show cached or pending AI status in UI.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| IMAP | pull sync + optional IDLE wakeups | Use UIDs, not sequence numbers; Python 3.14 `imaplib.idle()` makes low-latency refresh easier |
| SMTP | explicit send command from composer | Keep sending separate from draft generation |
| Ollama | local `/api/chat` adapter with timeouts | Treat as optional enrichment/service degradation boundary |
| Paperless | file handoff or readiness check before automation | Separate “document handed off” from “mail can now be moved” |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| UI ↔ query services | HTTP/JSON | Return read models, not raw IMAP structures |
| Sync ↔ repositories | direct service calls | Idempotent upserts only |
| Sync ↔ automation | durable job/event | Never direct synchronous rule execution |
| Thread/search ↔ LLM | service calls with cached outputs | Prompt inputs come from local DB only |

## Sources

- Project context and observed brownfield structure: `/Users/michaelkatschko/mail-ai-sorter/.planning/PROJECT.md`, `web_ui.py`, `services/imap_service.py`, `services/sorter_service.py`, `index.py`, `memory.py`, `routes/llm_routes.py`.
- Python `imaplib` docs (3.14.4): https://docs.python.org/3/library/imaplib.html — UIDs over message numbers; `IDLE` support now available. **HIGH**
- SQLite FTS5 docs: https://www.sqlite.org/fts5.html — external content tables, triggers, tokenizers, ranking/snippets. **HIGH**
- Ollama API docs: https://docs.ollama.com/api — local `/api/chat` boundary for assistive generation. **HIGH**
- Paperless-ngx usage docs: https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/usage.md — separate web server, consumer, task processor; mail ingestion and processed-mail tracking. **HIGH**
- Paperless-ngx configuration docs: https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/main/docs/configuration.md — consumption dir, scheduled tasks, email parsing, worker configuration. **HIGH**

---
*Architecture research for: local-first AI mail client / intelligent email sorter*
*Researched: 2026-04-17*
