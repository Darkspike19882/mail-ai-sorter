# Stack Research

**Domain:** local-first AI-powered desktop/web mail client and sorter
**Researched:** 2026-04-17
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Tauri | 2.10.x | Desktop shell, packaging, native OS integration | This is the standard 2025+ choice for local-first desktop apps that want a web UI without Electron’s memory and bundle overhead. Tauri 2 explicitly supports brownfield frontend setups and sidecar binaries, which fits this project’s existing Python backend evolution path. | HIGH |
| React + TypeScript + Vite | React 19.2.x, TypeScript 5.8+, Vite 8.0.x | Main UI stack for inbox, thread view, triage, composer, settings | For a mail client, the frontend bottleneck is interaction speed: list rendering, optimistic UI, keyboard-heavy flows, and fast incremental rebuilds. React 19 is the mainstream UI baseline; Vite 8 keeps iteration fast; TypeScript is mandatory once thread state, drafts, search state, and AI actions get complex. | HIGH |
| FastAPI | 0.136.x | Local API/service boundary for mail operations, AI endpoints, background control, search APIs | The current app is Flask-based, but the next milestone needs a typed app boundary, async-friendly endpoints, streaming/SSE/WebSocket options, and cleaner schema handling for desktop/web reuse. FastAPI is the standard Python API layer for local AI apps in 2025 because it pairs naturally with Pydantic and generates clear contracts for the frontend. | HIGH |
| Pydantic | 2.13.x | Typed request/response schemas, settings, validation for AI and mail workflows | Pydantic v2 is the current validation standard in Python app stacks and is directly aligned with FastAPI. It matters here because LLM-assisted replies, prompt settings, account config, rules, and structured model outputs all need strict validation instead of “best effort” dict handling. | HIGH |
| SQLite + FTS5 | SQLite 3.45+ with FTS5 enabled | Primary local database and full-text search index | For a local-first single-user mail client, SQLite is still the default answer. FTS5 gives first-class local search, prefix search, ranking, highlighting, external-content indexing, and trigram/tokenizer options without introducing an extra service. It is simpler, more portable, and more debuggable than adding Meilisearch/OpenSearch to a desktop app. | HIGH |
| SQLAlchemy + Alembic | SQLAlchemy 2.0.49, Alembic 1.18.x | ORM/data access plus schema migrations | Once the app moves from “utility script with tables” toward “real local client database”, you want explicit migrations, typed models, and reliable schema evolution. SQLAlchemy 2 is the current stable Python database toolkit; Alembic is still the standard migration companion and has explicit SQLite batch migration guidance. | HIGH |
| Ollama + official Python client | Ollama API (stable, unversioned), ollama-python 0.6.1 | Local LLM runtime for summaries, reply drafting, classification, extraction | The project constraint is local-only AI. Ollama remains the practical standard for shipping local model access behind a simple localhost API. Keeping the official client and direct prompt orchestration is the right choice here because it preserves portability and avoids heavyweight agent abstractions. | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| @tanstack/react-query | 5.99.x | Server-state caching, background refresh, optimistic mutations | Use for mailbox lists, thread fetches, search results, reply generation jobs, and daemon status. Mail UIs constantly reconcile local UI state with a live backend; Query is the cleanest way to handle that without custom cache logic. | HIGH |
| @tanstack/react-router | 1.168.x | Type-safe routing for inbox/search/thread/settings flows | Use if the app graduates from a few pages into a real client shell with nested layouts, saved views, and thread/detail routing. Better fit than ad-hoc route state once keyboard navigation and deep linking matter. | MEDIUM |
| @tanstack/react-virtual | 3.13.x | Virtualized rendering for long mail lists and search results | Use for inbox, unified inbox, thread sidebars, and search hit lists. This is essential once the local index grows; rendering thousands of messages without virtualization will make the “fast client” goal feel fake. | HIGH |
| Tailwind CSS | 4.2.x | UI styling system for dense productivity UI | Use for rapid iteration on a compact, keyboard-first interface. Tailwind v4’s Vite integration and CSS-first config suit a desktop-style app with lots of one-off layout tuning. | HIGH |
| Zustand | 5.0.x | Small client-side state for ephemeral UI state | Use for local-only UI state such as selected thread, composer draft pane state, command palette visibility, and split-pane preferences. Do not use it as a replacement for server-state caching. | MEDIUM |
| APScheduler | 3.11.x | Local scheduled jobs for delayed sorting and periodic maintenance | Use for “sort only after Paperless processing + 30 minute delay”, per-account throttled runs, reindex jobs, and health checks. It is a much better fit than bringing in Redis/Celery for a single-user local app. | HIGH |
| IMAPClient | 3.1.x | Higher-level IMAP access | Use if you continue evolving the Python mail backend. It gives a cleaner, more Pythonic surface than raw imaplib and is tested against common providers. | MEDIUM |
| orjson | 3.10+ | Fast JSON serialization in the local API | Use on FastAPI responses for thread/search payloads and AI job results once payload sizes get large. | MEDIUM |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python dependency and environment management | Prefer this over ad-hoc pip usage for reproducible local/dev/build environments. |
| Ruff | Linting and formatting for Python | Fast enough to keep enabled continuously; use it to keep the backend migration from Flask to FastAPI disciplined. |
| Pyright or mypy | Static typing for Python | Use at least one. This stack only pays off if typed models and service boundaries are actually checked. |
| Playwright | End-to-end UI testing | Best fit for thread view, keyboard shortcuts, search UX, and reply workflow regression tests. |
| pytest | Backend/service tests | Keep protocol, parsing, scheduling, and rule-engine behavior covered here. |

## Installation

```bash
# Frontend core
npm install react react-dom @tanstack/react-query @tanstack/react-router @tanstack/react-virtual zustand
npm install -D vite typescript tailwindcss @tailwindcss/vite

# Desktop shell
npm install -D @tauri-apps/cli
npm install @tauri-apps/api

# Python core
uv add fastapi pydantic sqlalchemy alembic ollama apscheduler imapclient orjson uvicorn
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Tauri 2 | Electron | Use Electron only if you need a bundled Chromium runtime, mature browser-extension-style APIs, or Node-heavy desktop integrations that Tauri would fight you on. That is not this project today. |
| FastAPI | Flask | Use Flask only as a transition step while extracting existing routes. Do not keep investing in Flask as the long-term application boundary for streaming AI, typed contracts, and richer desktop/web reuse. |
| SQLite + FTS5 | Meilisearch / OpenSearch | Use a separate search engine only if you outgrow single-user local constraints and need multi-process or multi-user search infrastructure. For this project, it adds operational complexity without enough gain. |
| React SPA on Vite | Next.js / server-first React framework | Use Next.js only if the product becomes cloud-hosted and SEO/server rendering matter. For a local mail client, server-first complexity is mostly self-inflicted. |
| Direct Ollama integration | LangChain / agent framework first | Use a higher-level orchestration framework only if you later need multi-tool agents or model-provider abstraction. For reply drafting, classification, and extraction, direct prompts plus typed schemas stay simpler and easier to debug. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Electron as the default desktop shell | Too heavy for a local-first productivity app that should feel lean, ship small, and preserve battery/RAM. | Tauri 2 |
| Next.js or other SSR-first frameworks | They optimize for hosted web apps, not packaged local clients. You pay extra routing/rendering complexity for little product value here. | React + Vite |
| Redis/Celery for local delayed sorting | Adds an unnecessary daemon/service dependency for a single-user desktop app. Harder installs, harder recovery, more moving parts. | APScheduler + in-process job orchestration persisted in SQLite |
| A vector DB as the primary search engine | Users expect exact, fast mail search first. Semantic search is a secondary layer, not the foundation. | SQLite FTS5 as primary search; add embeddings later only as an assistive layer |
| LangChain-first architecture | Over-abstracts local LLM workflows, makes debugging prompt behavior harder, and often adds token/model plumbing you do not need. | Direct Ollama calls + Pydantic-validated outputs |

## Stack Patterns by Variant

**If you want the fastest brownfield path from the current app:**
- Keep Python as the core service layer.
- Replace Flask route surfaces with FastAPI incrementally.
- Build the new client UI in React/Vite first.
- Add Tauri as a packaging shell using the brownfield pattern and a bundled Python sidecar.
- Because this preserves existing IMAP/SMTP/LLM/domain logic while modernizing the UX and app boundary.

**If you stay browser-first for one more milestone before packaging desktop installers:**
- Use FastAPI + React/Vite only.
- Keep the desktop packaging boundary out of the critical path.
- Add Tauri after thread view, search UX, and reply workflows are stable.
- Because packaging too early can distract from the actual product bottlenecks: thread ergonomics, search speed, and reply quality.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| fastapi@0.136.x | pydantic@2.13.x | FastAPI is built around Pydantic v2 in current stable releases. |
| sqlalchemy@2.0.49 | alembic@1.18.x | This is the standard stable pairing; Alembic docs explicitly cover SQLAlchemy integration and SQLite migration patterns. |
| react@19.2.x | vite@8.0.x | Current mainstream frontend baseline. |
| react@19.2.x | @tanstack/react-query@5.99.x, @tanstack/react-router@1.168.x, @tanstack/react-virtual@3.13.x | Current TanStack major lines align with React 19 usage. |
| @tauri-apps/cli@2.10.x | @tauri-apps/api@2.10.x | Keep Tauri packages on the same major/minor family to avoid tooling drift. |
| sqlite 3.43+ | FTS5 external content / contentless-delete features | If you want newer FTS5 maintenance patterns, do not target an old SQLite runtime. |

## Recommended Opinionated Baseline

If I were defining the roadmap stack for this milestone, I would lock in:

1. **Python 3.12/3.13 + FastAPI + Pydantic** for the local backend.
2. **SQLite + FTS5 + SQLAlchemy + Alembic** for all local persistence and search.
3. **React 19 + Vite + TanStack Query/Router/Virtual + Tailwind 4** for the client UI.
4. **Ollama + official Python client** for all local AI features.
5. **Tauri 2** only as the desktop shell/package boundary, using sidecar packaging for the Python service when desktop distribution becomes a milestone goal.

That is the most standard 2025 stack in this niche because it is local-first, performant, easy to distribute, and does not introduce extra infrastructure that fights the product constraints.

## Sources

- `.planning/PROJECT.md` — existing brownfield constraints and current architecture context
- https://v2.tauri.app/start/ — Tauri 2 positioning, architecture flexibility, release-era docs (HIGH)
- https://v2.tauri.app/concept/inter-process-communication/brownfield/ — brownfield pattern is default (HIGH)
- https://v2.tauri.app/develop/sidecar/ — sidecar support for bundled external binaries such as Python services (HIGH)
- https://v2.tauri.app/plugin/localhost/ — localhost plugin exists but is explicitly cautioned as a security risk (HIGH)
- https://react.dev/blog/2024/12/05/react-19 — React 19 stable release (HIGH)
- https://fastapi.tiangolo.com/ — FastAPI features, Pydantic/Starlette dependency, current CLI/install guidance (HIGH)
- https://docs.pydantic.dev/latest/ — Pydantic v2.13.1 current stable docs (HIGH)
- https://docs.sqlalchemy.org/en/20/ — SQLAlchemy 2.0 current docs, release 2.0.49 (HIGH)
- https://alembic.sqlalchemy.org/en/latest/ — Alembic 1.18.x current docs, SQLite batch migration guidance (HIGH)
- https://www.sqlite.org/fts5.html — FTS5 capabilities, external content tables, ranking, tokenizers, prefix indexes (HIGH)
- https://docs.ollama.com/api — local Ollama API, localhost base URL, official Python/JS clients (HIGH)
- https://github.com/mjs/imapclient — IMAPClient positioning and release status (MEDIUM)
- https://tailwindcss.com/blog/tailwindcss-v4 — Tailwind v4 architecture and Vite integration (HIGH)
- PyPI JSON registry queried 2026-04-17 for: fastapi, sqlalchemy, alembic, pydantic, ollama, apscheduler, imapclient (MEDIUM)
- npm registry queried 2026-04-17 for: react, vite, tailwindcss, @tanstack/react-query, @tanstack/react-router, @tanstack/react-virtual, @tauri-apps/cli, @tauri-apps/api, zustand (MEDIUM)

---
*Stack research for: local-first AI-powered desktop/web mail client and sorter*
*Researched: 2026-04-17*
