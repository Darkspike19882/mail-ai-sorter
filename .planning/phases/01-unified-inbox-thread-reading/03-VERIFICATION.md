---
phase: 1
slug: unified-inbox-thread-reading
status: verified
created: 2026-04-17
updated: 2026-04-17
---

# Phase 1 - Verification

## Automated Checks

- `python3 -m compileall routes services web_ui.py`
- `python3 -m unittest discover -s tests -v`

## Covered Behaviors

- Shared mail item contract normalizes inbox and search results onto the same keys.
- Unified inbox aggregation keeps deterministic ordering and surfaces per-account failures.

## Manual UI Checklist

- Open `/inbox` and confirm the default view loads the unified inbox.
- Refresh the page and verify account, folder, search query, selected mail, and priority filter are restored.
- Open a threaded mail and verify the thread timeline shows the current message in context.
- Click another item in the thread timeline and verify the detail pane switches without losing inbox context.
- Trigger a partial account failure and verify the UI shows the degraded unified inbox warning instead of silently hiding the account.
- Check desktop width and a narrow/mobile width to confirm list/detail navigation remains usable.
