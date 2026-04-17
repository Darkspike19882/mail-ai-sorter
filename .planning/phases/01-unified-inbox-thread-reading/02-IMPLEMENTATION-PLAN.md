---
phase: 1
slug: unified-inbox-thread-reading
status: completed
created: 2026-04-17
updated: 2026-04-17
plan_count: 3
---

# Phase 1 - Implementation Plan

## Goal

Close the gap between the current inbox prototype and the phase outcome: one reliable unified inbox, a genuinely thread-centered reading flow, and fast movement between list and detail without losing context.

## Current Baseline

- The app is a Flask server-rendered UI, not yet the future React/Tauri stack.
- `/inbox` already exists and is backed by `templates/inbox.html` plus `routes/inbox_routes.py`.
- Unified inbox loading already exists through `/api/unified-inbox`, but it currently merges per-account inbox pages in memory and treats failures as empty account results.
- Thread detail already exists through `services/imap_service.py:get_email_detail`, but it is still message-first with a lightweight related-message list rather than a full thread timeline.
- Search results, folder inbox results, and unified inbox results do not yet share one clearly hardened mail payload contract.

## Gap To Phase Success Criteria

### INBX-01 Unified inbox across accounts

- Present but not yet hardened for deterministic paging, partial account failures, or one consistent list item contract.

### INBX-02 Thread-centered reading

- Present only partially. The detail pane still centers the selected message and shows thread context as a secondary list.

### INBX-03 Fast navigation without losing context

- Present only partially. Selection, search state, and folder/unified context are handled in page memory only and are not explicitly preserved across refreshes or view transitions.

## Plans

### Plan 1 - Harden Unified Inbox Data Flow

**Why:** Phase 1 cannot be trusted if the multi-account inbox behaves differently from per-folder inboxes or silently drops problematic accounts.

**Scope:**

- Define one normalized mail list item contract shared by `/api/inbox`, `/api/unified-inbox`, and search-backed inbox results.
- Make unified inbox aggregation explicit about partial failures so one broken account does not masquerade as "no mail".
- Review paging and ordering behavior so the unified inbox is stable and predictable.
- Keep the implementation inside the current Flask and service structure rather than starting the React/FastAPI migration here.

**Primary files:**

- `routes/inbox_routes.py`
- `services/inbox_service.py`
- `services/imap_service.py`
- `templates/inbox.html`

**Acceptance:**

- Unified inbox returns one consistent item shape for all list sources.
- Account-level failures are surfaced to the UI as degradations, not silently ignored.
- Ordering and pagination behavior are documented and verified for mixed-account results.

### Plan 2 - Make Reading Truly Thread-Centered

**Why:** The phase promise is not "open a message with some related items"; it is a thread-first reading workflow.

**Scope:**

- Replace the lightweight related-message summary with a thread timeline that clearly shows the selected message in conversation context.
- Strengthen backend thread resolution using the headers already extracted in `imap_service.py`.
- Ensure the thread pane supports the UI contract already captured in `01-UI-SPEC.md`, with the reading pane as the visual focal point.
- Keep attachments, analysis, and reply entry points working from the thread-centered view.

**Primary files:**

- `services/imap_service.py`
- `routes/inbox_routes.py`
- `templates/inbox.html`

**Acceptance:**

- Opening a mail shows a conversation-oriented thread view, not just an isolated message.
- Thread ordering and membership are stable enough for common reply chains.
- Reply and analysis actions still operate on the currently selected message inside the thread.

### Plan 3 - Preserve Navigation Context And Verify Phase 1

**Why:** Fast reading falls apart if the user loses place while switching folders, searching, refreshing, or navigating on smaller screens.

**Scope:**

- Preserve account, folder, selected mail, and search state more explicitly so the list-detail workflow survives refresh and view changes.
- Tighten empty, error, and loading states around inbox, search, and detail loading.
- Add focused verification for inbox routes/services and document a manual UI checklist for desktop and mobile widths.
- Use this plan to close the remaining INBX-03 quality gaps rather than adding new phase scope.

**Primary files:**

- `templates/inbox.html`
- `routes/inbox_routes.py`
- `services/inbox_service.py`
- Tests or verification docs added during execution

**Acceptance:**

- User can move between unified inbox, folders, search, and thread detail without losing working context unexpectedly.
- Error and empty states are understandable and actionable.
- Phase 1 has a clear verification path before execution is marked complete.

## Sequencing

1. Plan 1 first, because thread and navigation work need a stable inbox contract.
2. Plan 2 second, because it delivers the core thread-reading value of the phase.
3. Plan 3 last, because it hardens context retention and verification after the main data and UI behavior settle.

## Out Of Scope For This Phase

- FastAPI migration
- React/Vite/Tauri shell work
- AI-grounded search workflows
- Compose/snippet workflow expansion beyond keeping existing reply entry points intact
- Delayed sorting and Paperless-aware automation

## Phase Exit Check

- [x] INBX-01 can be marked complete
- [x] INBX-02 can be marked complete
- [x] INBX-03 can be marked complete
- [x] The inbox flow is credible as the base for later search and reply phases

## Execution Notes

- Unified inbox, folder inbox, and search-backed list results now share one normalized mail item contract.
- Unified inbox responses now surface per-account failures explicitly so degraded account states are visible in the UI.
- Thread detail now builds a conversation timeline from `Message-ID`, `In-Reply-To`, and `References` headers instead of only showing a lightweight related-message list.
- Inbox context is persisted via URL parameters plus local storage so refreshes and view changes keep selection and location more reliably.
- Verification is documented in `03-VERIFICATION.md`.
