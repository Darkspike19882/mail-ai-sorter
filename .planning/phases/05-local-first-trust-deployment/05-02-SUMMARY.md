---
phase: 05-local-first-trust-deployment
plan: 02
subsystem: privacy-compliance
tags: [DSGVO, data-export, data-deletion, privacy-documentation, LOCL-03]
dependency_graph:
  requires: [05-01]
  provides: [PRIVACY.md, data-export-api, data-delete-api]
  affects: [app/__init__.py]
tech_stack:
  added: []
  patterns: [sqlite-dump-to-zip, password-stripping, DSGVO-data-portability]
key_files:
  created:
    - PRIVACY.md
    - app/routers/data.py
    - tests/test_data_api.py
  modified:
    - app/__init__.py
decisions:
  - PRIVACY.md written in German with English technical terms per project convention
  - sort_actions table is in llm_memory.db (not mail_index.db as plan assumed) — corrected in implementation
  - Export includes export_info.json metadata with password-stripping notice
  - Delete clears all tables in both databases (not just emails/conversations)
metrics:
  duration: 10m
  completed: 2026-04-18
  tasks: 2
  files: 4
---

# Phase 05 Plan 02: Privacy Documentation + Data Export/Delete APIs Summary

Comprehensive DSGVO-conscious PRIVACY.md with data inventory, network flows, and user rights documentation; plus data export (ZIP) and deletion API endpoints supporting DSGVO Art. 15, 17, 20.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create comprehensive PRIVACY.md documentation | dc497c2 | PRIVACY.md |
| 2 | Implement data export and deletion APIs | c2d6e0b | app/routers/data.py, app/__init__.py, tests/test_data_api.py |

## Key Changes

### PRIVACY.md (Task 1)
- 172-line comprehensive DSGVO-conscious privacy document
- 10 sections: Übersicht, Dateninventar, Netzwerkflüsse, Data That Never Leaves, Keine Cloud-Dienste, Aufbewahrungsfristen, Nutzerrechte, Sicherheitsmassnahmen, Automatisierte Verifikation, Kontakt
- Data inventory table with all storage locations, retention, encryption status, and purposes
- Network flow table documenting all outbound connections (IMAP, SMTP, Ollama, Paperless, Telegram)
- DSGVO user rights table mapping Art. 15/17/20 to API endpoints
- References automated verification tests (test_no_cloud_deps.py, test_credential_security.py)

### Data Export/Delete APIs (Task 2)
- `GET /api/data/export` — ZIP export containing SQLite dumps (mail_index.db, llm_memory.db), config.json (passwords stripped), PRIVACY.md, export_info.json
- `DELETE /api/data/delete` — Clears all database tables (emails, conversations, summaries, user_facts, sort_actions, etc.) and removes keyring entries
- `_strip_passwords()` removes password, password_env, and bot_token fields from exports (mitigates T-05-06)
- Router registered in FastAPI app at `app/__init__.py`
- TDD: 8 tests, all passing

## Verification Results

```
8 tests passed in 0.36s (data API tests)
23 tests passed in 0.43s (full suite)
```

Verification commands all pass:
- `grep -rn "export_user_data" app/routers/data.py` ✓
- `grep -rn "delete_user_data" app/routers/data.py` ✓
- `grep -n "data.router" app/__init__.py` ✓
- `wc -l PRIVACY.md` → 172 lines ✓
- `grep "Dateninventar" PRIVACY.md` ✓

## Decisions Made

1. **sort_actions in llm_memory.db:** The plan assumed sort_actions was in mail_index.db, but actual schema shows it's in llm_memory.db. Corrected in delete endpoint to clear all tables in both databases regardless.
2. **Comprehensive table clearing:** Delete clears all tables (emails, conversations, email_summaries, user_facts, sort_actions, rag_queries, email_embeddings, email_tags, reply_templates), not just the minimum listed in the plan.
3. **Export metadata:** Added export_info.json to the ZIP with export date, app name, and explicit password-stripping notice in German.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected sort_actions table location**
- **Found during:** Task 2 implementation
- **Issue:** Plan stated sort_actions is in mail_index.db, but actual schema shows it's in llm_memory.db
- **Fix:** Delete endpoint clears sort_actions from llm_memory.db and clears all other tables in both databases
- **Files modified:** app/routers/data.py
- **Commit:** c2d6e0b

## Known Stubs

None.

## Threat Flags

No new threat surface beyond what the threat model covers. The `_strip_passwords()` function mitigates T-05-06 (passwords in export ZIP). T-05-07 (accidental deletion) and T-05-08 (ZIP interception) are accepted per the threat model.

## Self-Check: PASSED

All 4 files verified present (PRIVACY.md, app/routers/data.py, tests/test_data_api.py, 05-02-SUMMARY.md).
All 3 commits verified in git log (dc497c2, b6a2b6a, c2d6e0b).
