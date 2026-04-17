---
phase: 02-search-grounded-retrieval
plan: implementation-overview
type: execute
wave: overview
depends_on: []
files_modified:
  - index.py
  - rag_engine.py
  - routes/inbox_routes.py
  - routes/rag_routes.py
  - templates/inbox.html
  - memory.py
autonomous: true
requirements: [SRCH-01, SRCH-02, SRCH-03, SRCH-04]

must_haves:
  truths:
    - "User can run fast full-text search across indexed emails"
    - "User can narrow search results by account, folder, and date range"
    - "User sees highlighted match snippets in search results showing exactly where the query matched"
    - "User can ask AI-assisted questions over the local mail corpus and see grounded results tied back to source emails"
    - "User can view and re-execute previous AI Q&A queries from history"
    - "User sees Ollama online/offline status in the AI panel"
  artifacts:
    - path: "index.py"
      provides: "Extended search() with account, folder, since, before params"
      contains: "account.*folder.*since.*before"
    - path: "rag_engine.py"
      provides: "Extended search_emails() with filters; Ollama health check in get_status()"
      contains: "ollama_reachable"
    - path: "routes/inbox_routes.py"
      provides: "Extended api_search() with filter params and match_snippet in response"
      contains: "match_snippet"
    - path: "routes/rag_routes.py"
      provides: "GET /api/rag/history endpoint; extended api_rag_query with filter params"
      contains: "/api/rag/history"
    - path: "templates/inbox.html"
      provides: "Filter chips, AI Q&A panel drawer, match snippet display, keyboard shortcuts"
      contains: "showAiPanel"
  key_links:
    - from: "templates/inbox.html"
      to: "/api/search"
      via: "runFilteredSearch() with account/folder/since params"
      pattern: "api/search.*account.*folder.*since"
    - from: "templates/inbox.html"
      to: "/api/rag/query"
      via: "askAiQuestion() POST"
      pattern: "api/rag/query"
    - from: "templates/inbox.html"
      to: "/api/rag/history"
      via: "loadAiHistory() fetch"
      pattern: "api/rag/history"
    - from: "routes/inbox_routes.py"
      to: "index.py search()"
      via: "direct import call with filter params"
      pattern: "search\(conn"
    - from: "routes/rag_routes.py"
      to: "rag_engine.py"
      via: "rag_service.query() and rag_service.get_status()"
      pattern: "rag_service\."
---

# Phase 2: Search & Grounded Retrieval — Implementation Plan

## Overview

**Goal:** Users can reliably rediscover emails and get grounded answers from their local mail history.

**Scope:** 3 plans across 3 waves. Each plan is self-contained with clear file ownership.

### Source Coverage Audit

| Source | Items | Covered By |
|--------|-------|------------|
| GOAL: Reliable search + grounded retrieval | 4 success criteria | Plans 1–3 |
| REQ SRCH-01: Fast full-text search | Search + match_snippet | Plan 01 (backend), Plan 03 (frontend) |
| REQ SRCH-02: Account/folder filtering | Filter params in API | Plan 01 (backend), Plan 03 (frontend) |
| REQ SRCH-03: Attachment text search | DEFERRED to Phase 3 per research decision — architecture prep only | Plan 01 (comment in `index_email()`) |
| REQ SRCH-04: AI Q&A with grounded citations | RAG extensions + AI panel | Plan 02 (backend+frontend) |

**SRCH-03 disposition:** Text extraction infrastructure (pdfplumber, python-docx) does not exist. Per research decisions, attachment text extraction is DEFERRED to Phase 3. Plan 01 adds a comment marker on `index_email()` for future attachment_text parameter. The UI-SPEC's `match_source` field defaults to `"body"`.

---

## Plan Structure

### Plan 01: Backend Search Enhancements (Wave 1)

**Objective:** Extend `index.py search()`, `inbox_routes.api_search()`, and `rag_engine.search_emails()` with account, folder, since, before filters. Add `match_snippet` to search API response.

**Files:** `index.py`, `routes/inbox_routes.py`, `rag_engine.py`

**Tasks (3):**

1. **Extend `index.py` `search()` with account/folder/since/before params**
   - Add `account`, `folder`, `before` params to the `search()` function signature
   - Add corresponding WHERE clauses using the same `AND e.` / `AND ` pattern already used for `category`, `from_filter`, `since`
   - The `emails` table already has `account` and `folder` columns — zero migration needed
   - Add comment marker on `index_email()` for future `attachment_text` parameter (SRCH-03 architecture prep)

2. **Extend `routes/inbox_routes.py` `api_search()` with filter params and match_snippet**
   - Add `account`, `folder`, `since`, `before` query params from `request.args`
   - Add `match_snippet` to the FTS5 SELECT (using `snippet(emails_fts, 3, '[', ']', '...', 12)`)
   - Add `match_snippet` to the non-FTS fallback SELECT (using `snippet AS match_snippet`)
   - Add filter WHERE clauses following the same pattern as `category`
   - Include `match_snippet` in the response dict columns list and column mapping

3. **Extend `rag_engine.py` `search_emails()` with filters and add Ollama health check**
   - Add `account`, `folder`, `since`, `before` optional params to `search_emails()`
   - Add corresponding `AND e.account = ?` etc. WHERE clauses after the FTS5 JOIN
   - Pass `account`, `folder`, `since` through `query()` → `search_emails()` so RAG queries can be scoped
   - Add `ollama_reachable` boolean to `get_status()` — attempt `GET {ollama_url}/api/tags` with 2s timeout, return `True`/`False`
   - Add `ollama_reachable` and `ollama_error` fields to status response dict

**Verification:**
```bash
# Test search with filters via CLI
python3 -c "import index; c=index.get_db(); r=index.search(c, query='test', account='someaccount'); print(len(r))"
# Test search API with params
curl "http://localhost:5001/api/search?q=test&account=someaccount&folder=INBOX&since=2025-01-01"
# Test RAG status includes ollama_reachable
curl "http://localhost:5001/api/rag/status" | python3 -m json.tool | grep ollama_reachable
```

---

### Plan 02: AI Q&A Backend + Frontend Panel (Wave 2 — depends on Plan 01)

**Objective:** Add RAG history endpoint, extend RAG query with filter passthrough, and build the AI Q&A panel drawer in the inbox UI.

**Files:** `routes/rag_routes.py`, `rag_engine.py`, `templates/inbox.html`, `memory.py`

**Tasks (3):**

1. **Add `GET /api/rag/history` endpoint to `routes/rag_routes.py`**
   - Add new route `@rag_bp.route("/api/rag/history")` that calls `memory.get_rag_history(limit=20)`
   - Accept optional `?limit=N` query param (default 20, max 50)
   - Return JSON `{success: True, history: [...]}` with each item containing `id, query, answer, sources, email_count, created_at`
   - `memory.get_rag_history()` already exists at line 529 — no memory.py changes needed for this

2. **Extend `routes/rag_routes.py` `api_rag_query()` with filter passthrough**
   - Extract `account`, `folder`, `since`, `before` from `request.json`
   - Pass them through to `rag_service.query()` which passes to `rag_engine.query()` → `search_emails()`
   - Update `rag_service.query()` signature to accept optional filter kwargs
   - Update `rag_engine.query()` to forward filter params to `search_emails()`

3. **Build AI Q&A panel drawer in `templates/inbox.html`**
   - Add Alpine.js state properties: `showAiPanel`, `aiQuestion`, `aiAnswer`, `aiLoading`, `aiError`, `aiStatus`, `aiHistory`
   - Add methods: `openAiPanel()`, `closeAiPanel()`, `askAiQuestion()`, `openSourceEmail(source)`, `loadAiHistory()`
   - Add the "KI-Frage" button (sparkle icon) at the right end of the search input row (line ~105)
   - Add the AI panel drawer HTML as a fixed-position overlay:
     - 480px width on desktop, full-screen on mobile (<768px)
     - Semi-transparent backdrop (`bg-black/30`)
     - Slide-in from right with `translate-x` transition
     - Contains: title bar, status indicator, question input, answer display, source citation cards, history list
   - Status indicator: fetch `/api/rag/status` on panel open, show "{N} Emails | {model} | ● Online/Offline"
   - Source citation cards: each shows `[N]` date, sender, subject, "Email öffnen" link
   - "Email öffnen" calls `openSourceEmail(source)` which closes panel + opens the email in detail pane
   - History: fetch `/api/rag/history` on panel open, show last 5 as clickable links
   - Keyboard shortcut: `Shift+/` (`?`) opens the AI panel
   - Loading state: disabled input, spinner, "Antwort wird generiert..." text
   - Timeout handling: 30s timeout with error state
   - Error states: Ollama offline (input disabled), RAG error (red error box), timeout

**Verification:**
```bash
# Test history endpoint
curl "http://localhost:5001/api/rag/history?limit=5" | python3 -m json.tool
# Test filtered RAG query
curl -X POST "http://localhost:5001/api/rag/query" -H "Content-Type: application/json" \
  -d '{"query": "test question", "account": "someaccount"}' | python3 -m json.tool
# Visual check: open inbox, click "KI-Frage", ask a question, verify answer + sources appear
```

---

### Plan 03: Frontend Search Enhancements (Wave 3 — depends on Plan 01)

**Objective:** Add filter chips (account, folder, date), match snippet display in results, keyboard shortcuts, empty/error states, and responsive behavior.

**Files:** `templates/inbox.html`

**Tasks (3):**

1. **Add filter chip bar to search area**
   - Add Alpine.js state: `searchAccountFilter`, `searchFolderFilter`, `searchDateFilter`, `searchDateFrom`, `searchDateTo`
   - Add a second row below the search input (after line ~106) with:
     - Account filter chips: "Alle Konten" + one chip per account from `accounts[]`
     - Folder filter chips: appear only when specific account selected, populated from that account's `folders[]`
     - Date filter dropdown: "Datum" button with options (Alle, Letzte 7 Tage, Letzte 30 Tage, Letzte 90 Tage, Dieses Jahr, Benutzerdefiniert)
   - Active chip styling: `bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900`
   - Inactive chip styling: `border border-slate-300 text-slate-600`
   - Clicking a chip updates the filter state and re-triggers search
   - Add `runFilteredSearch()` method that calls `/api/search` with all filter params composed
   - Update `debounceSearch()` to call `runFilteredSearch()` instead of `runSearch()`
   - Update existing `runSearch()` to call `runFilteredSearch()`
   - "Zur Inbox" button resets all filters to default

2. **Add match snippet display in search result rows**
   - In the `mail-row` template (around line 143–163), after the subject line, add a conditional snippet line:
     - Shows only when `searchActive` and `mail.match_snippet` exist
     - Renders the FTS5 snippet with `[...]` markers highlighted in yellow (`bg-yellow-200 dark:bg-yellow-800/40`)
     - Font: 13px, text-slate-500, truncated to 2 lines
     - Parse `[` and `]` delimiters from FTS5 output to wrap matches in `<mark>` tags
   - Add `match_snippet` passthrough: ensure `api_search()` response includes it and `normalize_mail_item()` preserves it
   - Add `match_source` field defaulting to `"body"` (SRCH-03 prep — no attachment detection yet)

3. **Add keyboard shortcuts and empty/error states**
   - Global keyboard listener on the inbox container:
     - `/` → focus search input (anywhere on page)
     - `Escape` → clear search if active, close AI panel if open
     - `Enter` in search input → execute search immediately (bypass debounce)
   - Update search-active banner (lines 47–52) to show active filters:
     - When account filter active: append `in ${searchAccountFilter}`
     - When folder filter active: append `/${searchFolderFilter}`
   - Enhanced empty states:
     - No results with filters: "Keine Treffer mit aktuellen Filtern" with suggestion to adjust
     - FTS5 syntax error: amber warning with auto-retry after stripping special chars
   - Add date filter "Benutzerdefiniert" mode: show two date inputs (from/to)
   - Responsive: filter chips wrap to multiple rows on <1024px, stack on <768px

**Verification:**
```bash
# Visual verification checklist:
# 1. Type in search → filter chips appear, results show match snippets with yellow highlights
# 2. Click account chip → results filter to that account
# 3. Click folder chip → results further filter
# 4. Select "Letzte 30 Tage" → results filter to date range
# 5. Press / → search input focuses
# 6. Press Escape → search clears
# 7. On mobile viewport → filter chips wrap, AI panel goes full-screen
```

---

## Wave Structure

```
Wave 1 (Plan 01): Backend search enhancements
    ├── index.py: search() gets account/folder/since/before params
    ├── routes/inbox_routes.py: api_search() gets filters + match_snippet
    └── rag_engine.py: search_emails() gets filters + Ollama health check

Wave 2 (Plan 02): AI Q&A backend + frontend panel [depends on Plan 01]
    ├── routes/rag_routes.py: GET /api/rag/history + filter passthrough
    ├── rag_engine.py: query() forwards filters
    └── templates/inbox.html: AI panel drawer + all interaction

Wave 3 (Plan 03): Frontend search enhancements [depends on Plan 01]
    └── templates/inbox.html: filter chips, match snippets, keyboard, states
```

**Parallelization note:** Plans 02 and 03 both modify `templates/inbox.html` but touch different sections:
- Plan 02 adds the AI panel drawer (new HTML block at the end of the template)
- Plan 03 modifies the existing search bar area and mail-row template (top/middle of template)

These MUST be sequential because they share `templates/inbox.html`. If needed, Plan 03 can execute first (it doesn't depend on the AI panel), but safest execution order is 01 → 02 → 03.

---

## File Modification Map

| File | Plan 01 | Plan 02 | Plan 03 | Total Changes |
|------|---------|---------|---------|---------------|
| `index.py` | search() params + attachment_text comment | — | — | Low |
| `rag_engine.py` | search_emails() filters + Ollama check | query() filter passthrough | — | Medium |
| `routes/inbox_routes.py` | api_search() filters + match_snippet | — | — | Medium |
| `routes/rag_routes.py` | — | history endpoint + filter passthrough | — | Medium |
| `memory.py` | — | No changes needed (get_rag_history exists) | — | None |
| `templates/inbox.html` | — | AI panel drawer + Alpine state/methods | Filter chips + snippets + shortcuts | High |

---

## Acceptance Criteria

### SRCH-01: Fast Full-Text Search
- [ ] `GET /api/search?q=test` returns results with `match_snippet` field
- [ ] Match snippet uses `[` `]` delimiters from FTS5 for highlighting
- [ ] Search results display in existing mail list with snippet shown below subject

### SRCH-02: Account/Folder Filtering
- [ ] `GET /api/search?q=test&account=X&folder=Y&since=2025-01-01` returns filtered results
- [ ] Filter chips in UI allow selecting account, folder, and date range
- [ ] All filters compose as AND conditions
- [ ] "Zur Inbox" clears all filters

### SRCH-03: Attachment Text (DEFERRED)
- [ ] `index_email()` has comment marker for future `attachment_text` parameter
- [ ] `match_source` defaults to `"body"` in API response
- [ ] Full implementation deferred to Phase 3

### SRCH-04: AI-Assisted Q&A
- [ ] `GET /api/rag/history` returns previous RAG queries
- [ ] `POST /api/rag/query` accepts optional `account`, `folder`, `since` filters
- [ ] `GET /api/rag/status` includes `ollama_reachable` boolean
- [ ] AI panel opens from "KI-Frage" button and `?` shortcut
- [ ] Question returns answer with source citations linked to real emails
- [ ] "Email öffnen" on a source closes panel and opens the email
- [ ] History shows last 5 queries as clickable links
- [ ] Ollama offline state disables input with explanatory message

---

## Context for Executors

### Key Interfaces (from codebase)

**From `index.py` — current `search()` signature (line 124):**
```python
def search(
    conn: sqlite3.Connection,
    query: str = "",
    category: Optional[str] = None,
    from_filter: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 30,
) -> List[sqlite3.Row]:
```

**From `routes/inbox_routes.py` — current `api_search()` SQL (lines 84–106):**
```python
# FTS5 query path:
sql = """
    SELECT e.id, e.msg_uid, e.account, e.folder, e.from_addr, e.subject,
           e.date_iso, e.category, e.keywords
    FROM emails_fts
    JOIN emails e ON e.id = emails_fts.rowid
    WHERE emails_fts MATCH ?
    ORDER BY e.date_iso DESC
    LIMIT 20
"""
# Non-FTS fallback path uses WHERE 1=1 with category filter only
```

**From `rag_engine.py` — current `search_emails()` SQL (lines 38–50):**
```python
rows = conn.execute("""
    SELECT e.id, e.account, e.folder, e.msg_uid, e.from_addr, e.subject,
           e.date_iso, e.category, e.snippet, e.keywords,
           snippet(emails_fts, 3, '[', ']', '...', 15) AS match_snippet
    FROM emails_fts
    JOIN emails e ON e.id = emails_fts.rowid
    WHERE emails_fts MATCH ?
    ORDER BY e.date_iso DESC
    LIMIT ?
""", (safe_query, limit)).fetchall()
```

**From `memory.py` — existing `get_rag_history()` (line 529):**
```python
def get_rag_history(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM rag_queries ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]
```

**From `templates/inbox.html` — Alpine.js state (lines 366–402):**
```javascript
function inboxApp() {
    return {
        accounts: [], mails: [], totalMails: 0,
        searchQuery: '', searchTimer: null,
        isUnified: true, currentAccount: '', currentFolder: 'INBOX',
        selectedMail: null, selectedMailKey: '',
        activePriorityFilter: 'all',
        showCompose: false, composeMode: 'new',
        compose: { account: '', to: '', cc: '', subject: '', body: '', ... },
        // ... existing methods: runSearch(), debounceSearch(), loadMails(), etc.
    };
}
```

**From `services/inbox_service.py` — `normalize_mail_item()` (line 38):**
- Normalizes uid, date, from, etc.
- Does `normalized.update(item)` at the end — so extra fields like `match_snippet` will pass through automatically

### Pattern to Follow

The existing codebase uses a consistent pattern for SQL filtering:
1. Build SQL string with parameterized `?` placeholders
2. Append `AND column = ?` conditionally based on param presence
3. Append param to the `params` list
4. Use `e.` prefix when the FTS5 JOIN path is active, bare column name otherwise

Follow this exact pattern for the new `account`, `folder`, `before` filters.

### No New Dependencies

This phase adds zero new Python or JavaScript packages. All changes extend existing code using:
- SQLite FTS5 (already in use)
- Alpine.js (already loaded in base.html)
- Tailwind CSS CDN (already loaded)
- Lucide icons (already loaded)
- Ollama HTTP API (already used by rag_engine.py)
