# Phase 3: Fast Reply Workflow - Research

**Researched:** 2026-04-17
**Domain:** Email reply composition, LLM-powered draft generation, template/snippet management, SMTP sending
**Confidence:** HIGH

## Summary

This phase builds the fast reply workflow on top of an existing Flask backend that already has: (1) a Quick Reply sidebar widget that generates AI drafts via Ollama, (2) a full-screen compose modal for sending emails, (3) complete SMTP sending with IMAP Sent-folder persistence, and (4) thread context resolution via IMAP message-id/references headers. The gap between current state and requirements is narrower than it appears: the core AI draft → compose → send pipeline works end-to-end, but it lacks thread-aware context in prompts, has no template/snippet system, has no inline composer option, and the Quick Reply sidebar is disconnected from the full compose flow in a way that creates friction.

The existing `memory.py` SQLite schema has **no** table for reply templates/snippets — it would need a new `reply_templates` table. The `llm_helper.py` `draft_reply()` method accepts only a single email's subject, sender, and body — it needs a `thread_context` parameter to include prior thread messages in the prompt. The compose modal is a full-screen overlay; making it inline in the detail pane is feasible but requires restructuring the HTML grid layout.

**Primary recommendation:** Extend the existing Quick Reply + compose pipeline incrementally — add a `reply_templates` SQLite table, add thread context to the LLM prompt, create a `/api/reply-templates` CRUD endpoint, and convert the compose modal into an inline detail-pane panel with keyboard shortcuts.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RPLY-01 | Fast, minimal composer | Current compose is a full-screen modal (inbox.html lines 433-470). Restructure into inline detail-pane panel. See Q5 analysis below. |
| RPLY-02 | AI reply draft from email/thread context | Current Quick Reply works for single emails via `/api/llm/quick-reply`. Needs thread_context parameter. See Q2 analysis below. |
| RPLY-03 | Predefined snippets/templates | No existing template table. New `reply_templates` table needed in memory.py. See Q1 analysis below. |
| RPLY-04 | Template + AI adaptation via local LLM | Requires new endpoint combining template text + email context → Ollama. See Q3 analysis below. |
| LOCL-02 | All AI through local Ollama | Already implemented via `llm_helper.py` → Ollama localhost:11434. No changes needed — confirmed working. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Template/snippet CRUD storage | API / Backend (SQLite via memory.py) | — | Persistent user data belongs in the local database, not client-side |
| AI reply draft generation | API / Backend (llm_helper.py → Ollama) | — | LLM calls must go through the backend to keep Ollama URL/model config centralized |
| Thread context assembly | API / Backend (imap_service.py) | — | Thread resolution already lives in imap_service.build_thread_timeline |
| Composer UI state | Browser / Client (Alpine.js) | — | Ephemeral UI state (draft text, selected template, open/close) is client-side |
| SMTP sending | API / Backend (smtp_client.py) | — | Already fully implemented, no changes needed |
| Draft auto-save | API / Backend (SQLite) | Browser / Client (debounced POST) | Drafts should survive page reload → backend persistence needed |

## Current State Analysis

### Existing Quick Reply Flow (End-to-End)

**Step 1 — User triggers Quick Reply** (inbox.html line 323):
```
User clicks "Entwurf erzeugen" button in detail pane sidebar
→ Alpine.js calls generateQuickReply()
```

**Step 2 — Frontend sends request** (inbox.html lines 1069-1090):
```javascript
POST /api/llm/quick-reply
Body: { subject, from_addr, body (email content), tone, language }
```

**Step 3 — Route handler** (llm_routes.py lines 47-59):
```python
@llm_bp.route("/api/llm/quick-reply", methods=["POST"])
def api_llm_quick_reply():
    data = request.json or {}
    result = llm_service.draft_reply(
        subject=data.get("subject", ""),
        from_addr=data.get("from_addr", ""),
        body=data.get("body", ""),
        tone=data.get("tone", "freundlich"),
        language=data.get("language", "de"),
    )
```

**Step 4 — LLM Service** (llm_service.py lines 76-83):
```python
def draft_reply(subject, from_addr, body, tone="freundlich", language="de"):
    return get_llm().draft_reply(subject, from_addr, body, tone=tone, language=language)
```

**Step 5 — Ollama call** (llm_helper.py lines 170-206):
- Builds a German-language system prompt asking for JSON `{subject, reply}`
- Includes tone parameter (freundlich/formal/kurz/bestimmt)
- Sends email body truncated to 4000 chars
- Calls Ollama `/api/chat` endpoint
- Returns `{"subject": "...", "reply": "..."}` or null

**Step 6 — User uses draft** (inbox.html lines 1092-1097):
```javascript
useQuickReply() → opens compose modal → pre-fills subject and body
```

**Step 7 — User sends** (inbox.html lines 1160-1187):
```javascript
POST /api/send → smtp_client.send_email() → SMTP + IMAP Sent save
```

### Key Observation: What's Missing

| Gap | Impact | Complexity |
|-----|--------|------------|
| No thread context in LLM prompt | AI replies lack awareness of prior conversation | MEDIUM — extend `draft_reply()` to accept optional thread messages |
| No template/snippet storage | RPLY-02/RPLY-03 impossible without data layer | LOW — add SQLite table + CRUD routes |
| No template + AI merge endpoint | RPLY-04 requires combining template text + email context → LLM | MEDIUM — new endpoint + prompt |
| Compose is full-screen modal only | Friction for fast reply workflow | MEDIUM — HTML restructuring |
| No draft auto-save | Risk of losing work on accidental navigation | LOW — debounced save to SQLite or localStorage |

## Standard Stack

### Core (Already In-Place)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Flask | 3.0+ | Backend framework | ✅ Installed, all routes use Flask Blueprints |
| SQLite | 3.51.0 | Local database (llm_memory.db) | ✅ Via memory.py with thread-local connections |
| Ollama | 0.20.7 | Local LLM runtime | ✅ Running on localhost:11434 |
| Alpine.js | (CDN) | Frontend reactivity | ✅ Used throughout inbox.html |
| smtp_client.py | Local | SMTP sending + IMAP Sent save | ✅ Complete implementation |

### Supporting (To Be Added)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (no new dependencies needed) | — | — | All required infrastructure already exists |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite table for templates | config.json section | Config is not ideal for user-created content that grows over time; SQLite is cleaner for CRUD |
| SQLite table for templates | Separate JSON file | Concurrent access, no indexing, no migration path — SQLite wins |
| New template endpoint in llm_routes | New dedicated blueprint | Keep reply templates in a new `reply_routes.py` for separation of concerns |

**Installation:**
```bash
# No new pip/npm packages needed for this phase
```

## Architecture Patterns

### System Architecture: Reply Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                     Browser / Client                             │
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌────────────────────┐      │
│  │ Template  │    │  AI Draft    │    │  Inline Composer   │      │
│  │ Picker    │───▶│  Generation  │───▶│  (edit + send)     │      │
│  │ (sidebar) │    │  (Ollama)    │    │  (detail pane)     │      │
│  └─────┬─────┘    └──────┬───────┘    └────────┬───────────┘      │
│        │                 │                     │                  │
└────────┼─────────────────┼─────────────────────┼──────────────────┘
         │                 │                     │
    GET/POST          POST                   POST
  /api/reply-    /api/llm/thread-        /api/send
  templates       reply or /quick-reply
         │                 │                     │
┌────────┼─────────────────┼─────────────────────┼──────────────────┐
│        ▼                 ▼                     ▼                  │
│  ┌───────────┐    ┌──────────────┐    ┌─────────────────┐        │
│  │ memory.py │    │ llm_helper   │    │ smtp_client.py  │        │
│  │ (SQLite)  │    │ → Ollama API │    │ → SMTP server   │        │
│  │ templates │    │ localhost     │    │ + IMAP Sent     │        │
│  │ table     │    │ :11434       │    │ save            │        │
│  └───────────┘    └──────────────┘    └─────────────────┘        │
│                     API / Backend                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (Changes Only)
```
routes/
├── reply_routes.py          # NEW: CRUD for reply templates
├── llm_routes.py            # MODIFIED: add thread-reply endpoint
└── inbox_routes.py          # UNCHANGED: send endpoint stays here

services/
├── llm_service.py           # MODIFIED: add thread_context param
└── imap_service.py          # UNCHANGED: thread resolution stays here

memory.py                    # MODIFIED: add reply_templates table
llm_helper.py                # MODIFIED: extend draft_reply with thread context

templates/
└── inbox.html               # MODIFIED: inline composer + template picker
```

### Pattern 1: Template CRUD (SQLite)
**What:** Standard CRUD for user-managed reply templates
**When to use:** For any user-created content that needs persistence
**Example:**
```python
# memory.py — new table in SCHEMA
CREATE TABLE IF NOT EXISTS reply_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subject_template TEXT DEFAULT '',
    body_template TEXT NOT NULL,
    tone TEXT DEFAULT 'neutral',
    category TEXT DEFAULT 'general',
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

# memory.py — CRUD functions
def save_reply_template(name, body_template, subject_template='', tone='neutral', category='general') -> int
def get_reply_templates(category=None) -> List[Dict]
def get_reply_template(template_id: int) -> Optional[Dict]
def update_reply_template(template_id, **fields) -> bool
def delete_reply_template(template_id) -> bool
```

### Pattern 2: Thread-Aware AI Reply
**What:** Extend existing draft_reply to include thread messages
**When to use:** When user wants AI to consider the full conversation
**Example:**
```python
# llm_helper.py — extended draft_reply
def draft_reply(
    self,
    subject: str,
    from_addr: str,
    body: str,
    tone: str = "freundlich",
    language: str = "de",
    thread_context: Optional[List[Dict]] = None,  # NEW
) -> Optional[Dict[str, str]]:
    # Build prompt including thread history if available
    thread_section = ""
    if thread_context:
        for msg in thread_context[-5:]:  # Last 5 messages
            thread_section += f"\n--- Vorherige Nachricht von {msg.get('from', '?')} ---\n"
            thread_section += f"Betreff: {msg.get('subject', '')}\n"
            thread_section += f"{msg.get('body_text', '')[:1000]}\n"
    # Include thread_section in prompt...
```

### Pattern 3: Template + AI Adaptation
**What:** Merge template text with email context via LLM
**When to use:** User picks a template, AI adapts it to fit the current email
**Example:**
```python
# llm_helper.py — new method
def adapt_template(
    self,
    template_body: str,
    template_subject: str,
    email_subject: str,
    email_from: str,
    email_body: str,
    tone: str = "freundlich",
    language: str = "de",
    thread_context: Optional[List[Dict]] = None,
) -> Optional[Dict[str, str]]:
    system = (
        "Du bist ein Email-Assistent. Passe eine Vorlage an den aktuellen Email-Kontext an. "
        "Ersetze Platzhalter wie {name}, {thema}, {datum} sinnvoll. "
        "Antworte IMMER als JSON mit den Feldern: subject, reply."
    )
    prompt = (
        f"Vorlage:\n{template_body}\n\n"
        f"Original-Betreff: {email_subject}\n"
        f"Absender: {email_from}\n"
        f"Original-Inhalt: {email_body[:2000]}\n\n"
        f"Passe die Vorlage an diese Email an. Ton: {tone}. Sprache: {language}."
    )
```

### Anti-Patterns to Avoid
- **Storing templates in config.json:** Config is for app configuration, not user content. Templates will grow, need CRUD, and may eventually support sharing. SQLite is the right home. `[VERIFIED: config.json used for accounts + global settings only]`
- **Generating AI replies client-side:** All Ollama calls must go through the backend. The frontend should never know the Ollama URL. `[VERIFIED: current architecture follows this pattern]`
- **Putting the compose modal inside the thread sidebar:** The detail pane already has a 2-column grid (content + analysis sidebar). The composer should replace the email content view or sit below it, not nest deeper into the sidebar.
- **Making the inline composer always visible:** It should appear on-demand (keyboard shortcut `r` or button click) and be dismissible, similar to how Superhuman handles replies.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SMTP sending | Custom SMTP logic | smtp_client.send_email() | Already handles SSL/STARTTLS, presets, attachments, IMAP Sent save `[VERIFIED: smtp_client.py lines 173-228]` |
| Thread resolution | Manual IMAP threading | imap_service.build_thread_timeline() | Already handles message-id, references, in-reply-to lookups `[VERIFIED: imap_service.py lines 165-224]` |
| LLM communication | Raw HTTP to Ollama | LLMHelper.chat() | Handles JSON formatting, timeouts, error recovery `[VERIFIED: llm_helper.py lines 28-66]` |
| Email normalization | Manual field mapping | inbox_service.normalize_mail_item() | Handles date parsing, from/to normalization, uid coercion `[VERIFIED: inbox_service.py lines 38-74]` |

## Common Pitfalls

### Pitfall 1: Thread Context Truncation
**What goes wrong:** Sending entire thread bodies to LLM exceeds context window or makes generation slow
**Why it happens:** Thread messages can be long, especially with HTML emails
**How to avoid:** Limit thread context to last 5 messages, strip HTML to plain text, truncate each message to ~1000 chars. The current `draft_reply` already truncates single email body to 4000 chars — apply similar limits per-thread-message.
**Warning signs:** Ollama timeouts, gibberish replies, or very slow draft generation (>15s)

### Pitfall 2: Template Variables Not Resolved
**What goes wrong:** Templates with placeholders like `{name}` get sent to the user literally
**Why it happens:** If the AI adaptation step fails or is skipped, unresolved placeholders remain
**How to avoid:** Always run templates through the AI adaptation endpoint before showing them. For basic variable substitution without AI (when Ollama is down), implement a simple fallback that extracts the sender's name from the from field.
**Warning signs:** User sees `{name}` or `{thema}` in the draft text

### Pitfall 3: Inline Composer Overwrites Email Content
**What goes wrong:** When the inline composer opens, the email body disappears and the user can no longer reference it while composing
**Why it happens:** Replacing the email content div with the composer div means the source email is gone
**How to avoid:** Use a split layout — show the email header + collapsed body above the composer, or use a tab/accordion pattern. The current grid layout `grid lg:grid-cols-[1fr_320px]` already has space for this.
**Warning signs:** User opens reply, can't see the original email

### Pitfall 4: Draft Loss on Navigation
**What goes wrong:** User starts typing a reply, accidentally clicks another email, draft is gone
**Why it happens:** Alpine.js state is ephemeral — selecting a new email resets the compose state
**How to avoid:** Implement auto-save to localStorage with a debounce (simpler) or SQLite drafts table (more robust). Check for unsaved draft before allowing navigation.
**Warning signs:** User reports losing reply text

### Pitfall 5: Tone Dropdown German Labels Don't Match LLM Prompt
**What goes wrong:** The frontend uses German tone labels (freundlich, formal, kurz, bestimmt) but the LLM prompt may not handle all of them well
**Why it happens:** The tone parameter is passed directly to the prompt without mapping
**How to avoid:** Test all 4 tone settings with the actual LLM model. Consider mapping tones to more specific prompt instructions (e.g., "kurz" → "max 3 sentences, no pleasantries").
**Warning signs:** "Kurz" tone still generates long replies, or "bestimmt" tone is too aggressive

## Code Examples

### New reply_templates Table Schema
```python
# Source: [DESIGNED for this codebase, following existing memory.py patterns]
# In memory.py SCHEMA string, add:

"""
CREATE TABLE IF NOT EXISTS reply_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subject_template TEXT DEFAULT '',
    body_template TEXT NOT NULL,
    tone TEXT DEFAULT 'neutral',
    category TEXT DEFAULT 'general',
    sort_order INTEGER DEFAULT 0,
    is_builtin INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_templates_category ON reply_templates(category);
"""
```

### Template CRUD Functions
```python
# Source: [Following existing memory.py function patterns]
# memory.py additions:

def save_reply_template(
    name: str, body_template: str, subject_template: str = "",
    tone: str = "neutral", category: str = "general",
    sort_order: int = 0, is_builtin: bool = False,
) -> int:
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO reply_templates (name, subject_template, body_template, tone, category, sort_order, is_builtin)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, subject_template, body_template, tone, category, sort_order, int(is_builtin)),
    )
    conn.commit()
    return cursor.lastrowid

def get_reply_templates(category: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT * FROM reply_templates WHERE category = ? ORDER BY sort_order, name",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM reply_templates ORDER BY sort_order, name"
        ).fetchall()
    return [dict(r) for r in rows]

def get_reply_template(template_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    row = conn.execute("SELECT * FROM reply_templates WHERE id = ?", (template_id,)).fetchone()
    return dict(row) if row else None

def update_reply_template(template_id: int, **fields) -> bool:
    conn = get_db()
    allowed = {"name", "subject_template", "body_template", "tone", "category", "sort_order"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = "datetime('now')"
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [template_id]
    conn.execute(f"UPDATE reply_templates SET {set_clause} WHERE id = ?", values)
    conn.commit()
    return True

def delete_reply_template(template_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM reply_templates WHERE id = ? AND is_builtin = 0", (template_id,))
    conn.commit()
    return conn.total_changes > 0
```

### Thread-Aware Reply Endpoint
```python
# Source: [Extended from existing llm_routes.py patterns]
# llm_routes.py — new endpoint:

@llm_bp.route("/api/llm/thread-reply", methods=["POST"])
def api_llm_thread_reply():
    data = request.json or {}
    thread_context = data.get("thread_context", [])
    # Fetch full body for each thread message if not provided
    if data.get("account") and data.get("folder") and data.get("uid"):
        acc = get_account(data["account"])
        if acc:
            try:
                detail = imap_service.get_email_detail(acc, data["folder"], data["uid"])
                thread_context = detail.get("thread", [])
            except Exception:
                pass
    result = llm_service.draft_reply(
        subject=data.get("subject", ""),
        from_addr=data.get("from_addr", ""),
        body=data.get("body", ""),
        tone=data.get("tone", "freundlich"),
        language=data.get("language", "de"),
        thread_context=thread_context,
    )
    if not result:
        return _json_error("LLM nicht erreichbar", 503)
    return jsonify({"success": True, **result})
```

### Template Adaptation Endpoint
```python
# Source: [New endpoint following existing llm_routes.py patterns]
# llm_routes.py — new endpoint:

@llm_bp.route("/api/llm/adapt-template", methods=["POST"])
def api_llm_adapt_template():
    data = request.json or {}
    template_id = data.get("template_id")
    if template_id:
        template = memory.get_reply_template(template_id)
        if not template:
            return _json_error("Vorlage nicht gefunden", 404)
        template_body = template["body_template"]
        template_subject = template.get("subject_template", "")
        tone = template.get("tone", data.get("tone", "freundlich"))
    else:
        template_body = data.get("template_body", "")
        template_subject = data.get("template_subject", "")
        tone = data.get("tone", "freundlich")

    result = llm_service.adapt_template(
        template_body=template_body,
        template_subject=template_subject,
        email_subject=data.get("subject", ""),
        email_from=data.get("from_addr", ""),
        email_body=data.get("body", ""),
        tone=tone,
        language=data.get("language", "de"),
        thread_context=data.get("thread_context"),
    )
    if not result:
        return _json_error("LLM nicht erreichbar", 503)
    return jsonify({"success": True, **result})
```

### Seed Default Templates
```python
# Source: [Following existing _ensure_tables pattern in memory.py]
# memory.py — call in get_db() after _ensure_indexes:

def _seed_default_templates(conn):
    count = conn.execute("SELECT COUNT(*) FROM reply_templates").fetchone()[0]
    if count > 0:
        return
    defaults = [
        ("Bestätigung", "Re: {subject}", "Hallo,\n\nvielen Dank für Ihre Nachricht. Ich habe die Informationen zur Kenntnis genommen und werde mich bei Rückfragen melden.\n\nViele Grüße", "formal", "general", 0, True),
        ("Schnelle Antwort", "", "Hallo,\n\ndanke für die Info!\n\nViele Grüße", "kurz", "general", 1, True),
        ("Terminbestätigung", "", "Hallo,\n\nder Termin ist bei mir eingetragen. Ich freue mich auf das Gespräch.\n\nViele Grüße", "freundlich", "calendar", 2, True),
        ("Nachfrage", "", "Hallo,\n\nich melde mich bezüglich {thema}. Könnten Sie mir noch folgende Informationen zukommen lassen?\n\nViele Grüße", "formal", "general", 3, True),
    ]
    conn.executemany(
        "INSERT INTO reply_templates (name, subject_template, body_template, tone, category, sort_order, is_builtin) VALUES (?, ?, ?, ?, ?, ?, ?)",
        defaults,
    )
    conn.commit()
```

## Detailed Question Analysis

### Q1: Template/Snippet Storage

**Current State:** `memory.py` has NO template/snippet table. The existing tables are: `conversations`, `user_facts`, `email_summaries`, `rag_queries`, `email_embeddings`, `email_tags`. There is a `rule_templates.json` file but it contains sorting-rule presets, not reply templates.

**Recommendation: New SQLite table in memory.py**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| New `reply_templates` table in SQLite | CRUD-friendly, indexed, migration-ready, consistent with existing patterns | Slightly more code than JSON file | ✅ **Recommended** |
| config.json section | Simple, no schema change | Not suitable for growing user content, no concurrent access safety | ❌ |
| Separate JSON file | Easy to edit manually | No indexing, no migration, concurrency issues | ❌ |
| localStorage only | Zero backend work | Lost on browser clear, not portable across devices | ❌ |

**Confidence:** HIGH — The existing memory.py pattern (table in SCHEMA + _ensure_tables + CRUD functions) is exactly right for this.

### Q2: AI Reply Generation — Current State & Thread Extension

**Current Quick Reply endpoint contract:**
```
POST /api/llm/quick-reply
Request:  { subject, from_addr, body, tone, language }
Response: { success, subject, reply }
```

**What needs to change for thread-context replies:**

1. **New endpoint** `POST /api/llm/thread-reply` that accepts `thread_context` as an additional parameter (list of prior messages with `from`, `subject`, `body_text`)
2. **Modified `llm_helper.draft_reply()`** to accept optional `thread_context: List[Dict]`
3. **Frontend change** — the `generateQuickReply()` function already has access to `this.selectedMail.thread` (populated by `imap_service.get_email_detail()`). Just needs to pass thread data in the POST body.

**Thread data already available:** When a user selects an email, the `selectMail()` function calls `GET /api/email/{account}/{folder}/{uid}`, which returns the full email detail including `thread: [...]` — an array of thread messages with `from`, `subject`, `date`, `uid`, `message_id`. However, thread items from `build_thread_timeline()` only have **headers** (no body content) because they're fetched via `BODY.PEEK[HEADER.FIELDS(...)]`.

**Key insight:** To get thread body content for the AI prompt, you have two options:
- **Option A (Recommended):** Fetch full bodies only for the last 2-3 thread messages. This keeps the prompt manageable.
- **Option B:** Use the already-available email summaries from `email_summaries` table as a lightweight proxy for thread context. Less accurate but faster.

**Confidence:** HIGH — The architecture already supports this; it's an extension, not a rewrite.

### Q3: Template + AI Adaptation

**Recommendation: Option B — User picks template → AI rewrites to match email context**

| Option | Description | Pros | Cons | Verdict |
|--------|-------------|------|------|---------|
| A | Template with variable slots → AI fills slots | Structured, predictable | Requires defining slot schema, inflexible | ❌ |
| B | Template text + email context → AI rewrites | Natural, flexible, handles edge cases | Less predictable output, may drift from template | ✅ **Recommended** |
| C | Template + email → AI merges | Combines both approaches | Over-complex for v1 | ❌ |

**Why B:** This is the most natural UX. The user picks "Bestätigung" template, the AI sees the template text + the email they're replying to + thread context, and produces a draft that follows the template's intent but is adapted to the specific email. The prompt should instruct the LLM to use the template as a style/structure guide, not as literal text to fill in.

**Implementation:** New `adapt_template()` method in `llm_helper.py` + new `/api/llm/adapt-template` route. The template body is sent as context to the LLM along with the email being replied to.

**Fallback when Ollama is down:** Show the raw template text with basic variable substitution (e.g., replace `{name}` with sender name extracted from the from field). This gives the user something even without AI.

**Confidence:** HIGH — This pattern is straightforward and follows existing prompt engineering in the codebase.

### Q4: Draft Persistence

**Recommendation: localStorage with debounce (v1) + SQLite drafts table (future)**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| localStorage only | Zero backend work, instant, survives page refresh | Lost on browser clear, not portable | ✅ **v1 — simplest approach** |
| SQLite drafts table | Robust, survives browser changes, queryable | More endpoints, migration | Future enhancement |
| Nowhere (ephemeral) | Simplest | User loses work on any navigation | ❌ Bad UX |

**v1 implementation:**
- On every keystroke in the compose textarea (debounced 2s), save to `localStorage` keyed by `draft:{account}:{folder}:{uid}`
- On compose open, check localStorage for existing draft
- On successful send, clear the localStorage draft
- On navigating to a different email, check for unsaved draft and warn

**Confidence:** HIGH — localStorage is the right v1 choice. A drafts table can be added later when the Tauri migration happens and drafts need to survive across web/desktop.

### Q5: Composer Architecture — Inline vs Modal

**Current State:** The compose UI is a full-screen modal overlay (inbox.html lines 433-470) with backdrop. It's triggered by `openReply()` or `useQuickReply()`.

**Recommendation: Inline panel in the detail pane with option to expand**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Keep full-screen modal only | No UI change needed | Hides the email you're replying to, high friction | ❌ Doesn't meet RPLY-01 |
| Inline panel in detail pane | Can see email while composing, fast, Superhuman-like | Needs HTML restructuring, less screen space | ✅ **Primary** |
| Split pane (email top / compose bottom) | Can see email, natural scroll | Requires scrolling on small screens | ✅ **Layout approach** |
| Slide-up panel (like mobile) | Doesn't fully hide email | Unusual for desktop | ❌ |

**Recommended layout:**
```
Detail Pane (when composing):
┌─────────────────────────────────────────┐
│ Email Header (collapsed, subject + from)│  ← Collapsible
│ [Reply] [Forward] [Close Composer]      │
├─────────────────────────────────────────┤
│ To: _______                             │
│ Subject: _______                        │
│ ┌─────────────────────────────────────┐ │
│ │ Composer textarea                   │ │
│ │                                     │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
│ [Template ▼] [AI Draft] [Send]         │
└─────────────────────────────────────────┘
```

**Implementation approach:**
1. Add a `showComposer` Alpine.js state flag
2. When `showComposer` is true, replace the email content area with the inline composer
3. Show email header collapsed at top (subject, from, date)
4. Add a "Show Original" toggle to expand the email body for reference
5. Keep the sidebar (analysis + quick reply) visible in the right column
6. Keyboard shortcut `r` to open reply, `Escape` to close, `Cmd+Enter` to send

**Confidence:** MEDIUM — The HTML restructuring is straightforward but needs careful responsive testing. The current grid layout `grid lg:grid-cols-[1fr_320px]` can accommodate this without structural changes.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full-screen compose modal only | Inline reply panels (Superhuman, Gmail, HEY) | 2019+ | Users expect to see the email while replying |
| Hardcoded reply tones | Configurable tone profiles | 2023+ | LLM makes tone customization trivial |
| Static email templates | AI-adapted templates | 2024+ | LLM can merge template intent with email context |

**Deprecated/outdated:**
- Pure template-variable substitution (like `{name}` → "John"): AI adaptation makes this unnecessary for most cases, though it remains useful as a fallback

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Thread messages from `build_thread_timeline()` don't include body content | Q2 Analysis | If thread items do include bodies, the thread-reply endpoint is simpler |
| A2 | The LLM model (llama3.1:8b) can handle 5 thread messages + template adaptation within its context window | Architecture Patterns | If context window is too small, reduce thread message count or body truncation |
| A3 | Users will want German as default language for templates and drafts | Template Seeds | If user expects English or other languages, seed templates need localization |
| A4 | The current Alpine.js frontend can support an inline composer without framework migration | Q5 Analysis | If Alpine.js can't handle the complexity, a React migration might be needed (unlikely) |

**Note on A1:** This is partially verified — `build_thread_timeline()` in imap_service.py uses `BODY.PEEK[HEADER.FIELDS(FROM TO CC SUBJECT DATE MESSAGE-ID IN-REPLY-TO REFERENCES)]` for thread items, which returns headers only, not bodies. However, the currently selected message's full body IS available from `get_email_detail()`. To get thread message bodies, you'd need to fetch them separately or extend the thread timeline fetch. `[VERIFIED: imap_service.py lines 129-131]`

## Open Questions

1. **Thread body fetching strategy**
   - What we know: Thread timeline returns headers only. The selected message has full body.
   - What's unclear: Should we fetch full bodies for the last N thread messages on demand? Or rely on summaries from `email_summaries` table?
   - Recommendation: For v1, fetch full body of the last 2-3 thread messages on demand. This adds 2-3 IMAP fetches but gives the LLM enough context for a good reply.

2. **Template variable syntax**
   - What we know: Templates need some way to indicate placeholders.
   - What's unclear: Should we use `{name}` syntax, `{{name}}` Jinja-style, or let the AI infer what to fill in?
   - Recommendation: Use `{variable}` syntax for the simple fallback. The AI adaptation prompt doesn't need to know about the syntax — it sees the template text and adapts naturally.

3. **Keyboard shortcuts scope**
   - What we know: The app already has `/` for search and `?` for AI panel.
   - What's unclear: What keyboard shortcuts should the reply workflow support?
   - Recommendation: `r` to reply (open inline composer), `Escape` to close, `Cmd+Enter` or `Ctrl+Enter` to send. These are standard mail client conventions.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Backend | ✓ | 3.14.4 | — |
| SQLite | Database | ✓ | 3.51.0 | — |
| Ollama | LLM runtime | ✓ | 0.20.7 | — |
| Flask | API framework | ✓ | 3.0+ | — |
| Node.js | Frontend tooling | ✓ | 25.8.2 | — |
| Alpine.js | Frontend reactivity | ✓ | (CDN) | — |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | None — see Wave 0 |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RPLY-01 | Inline composer opens in detail pane | manual-only | — | ❌ (frontend, no test infra) |
| RPLY-02 | AI generates reply with thread context | unit | `python -m pytest tests/test_reply_workflow.py::test_thread_reply -x` | ❌ Wave 0 |
| RPLY-03 | Template CRUD operations work | unit | `python -m pytest tests/test_reply_workflow.py::test_template_crud -x` | ❌ Wave 0 |
| RPLY-04 | Template + AI adaptation produces valid draft | unit | `python -m pytest tests/test_reply_workflow.py::test_adapt_template -x` | ❌ Wave 0 |
| LOCL-02 | All AI calls go through Ollama localhost | unit | `python -m pytest tests/test_reply_workflow.py::test_local_llm_only -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_reply_workflow.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before verify

### Wave 0 Gaps
- [ ] `tests/test_reply_workflow.py` — covers RPLY-02, RPLY-03, RPLY-04, LOCL-02
- [ ] `tests/conftest.py` — shared fixtures (mock Ollama, test DB)
- [ ] pytest install: `pip install pytest` — if not already installed

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | App is local-first, single-user, no auth |
| V3 Session Management | no | No sessions in local app |
| V4 Access Control | no | Single-user local app |
| V5 Input Validation | yes | Pydantic/Flask request validation for template CRUD and LLM endpoints |
| V6 Cryptography | no | No encryption needed beyond SMTP TLS |

### Known Threat Patterns for Local Flask App + LLM

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS in email body displayed in composer | Tampering | DOMPurify already used for email display (inbox.html line 1357). Ensure template text is also sanitized. |
| IMAP injection via crafted UID | Tampering | UIDs are integers, validated by `parse_uid()` |
| Prompt injection via email body | Spoofing | LLM prompts include email content — attacker could craft emails that influence AI replies. Mitigate by clearly separating "context" from "instructions" in prompts. |

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `templates/inbox.html`, `routes/llm_routes.py`, `services/llm_service.py`, `llm_helper.py`, `smtp_client.py`, `memory.py`, `routes/inbox_routes.py`, `config_service.py`, `services/inbox_service.py`, `services/imap_service.py` — all read and verified in this session
- `rule_templates.json` — confirmed to be sorting-rule presets, not reply templates
- `.planning/REQUIREMENTS.md` — phase requirements verified

### Secondary (MEDIUM confidence)
- Project stack recommendations from `.planning/research/STACK.md` — referenced for consistency
- Alpine.js patterns observed in existing codebase

### Tertiary (LOW confidence)
- None — all claims verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies needed, all infrastructure exists
- Architecture: HIGH — follows existing patterns in codebase
- Pitfalls: HIGH — based on analysis of actual code behavior

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (stable codebase, no fast-moving dependencies)
