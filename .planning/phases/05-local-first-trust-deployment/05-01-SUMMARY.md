---
phase: 05-local-first-trust-deployment
plan: 01
subsystem: security
tags: [credentials, keyring, CSP, network-audit, local-first]
dependency_graph:
  requires: []
  provides: [keyring-credential-storage, cloud-dep-audit-test, CSP-middleware]
  affects: [config_service.py, smtp_client.py, sorter.py, app/__init__.py]
tech_stack:
  added: [keyring>=25.7.0, pytest>=9.0.3]
  patterns: [OS-native-credential-storage, CSP-middleware, automated-network-audit]
key_files:
  created:
    - tests/test_credential_security.py
    - tests/test_no_cloud_deps.py
  modified:
    - config_service.py
    - smtp_client.py
    - sorter.py
    - app/__init__.py
decisions:
  - Keyring-first priority chain: OS keychain → env var → secrets.env fallback
  - SERVICE_NAME = "com.superhero-mail" for keyring namespace
  - CSP allows Tailwind CDN, jsdelivr, unpkg; blocks all other external sources
  - Network audit blocks cloud domains explicitly (openai, anthropic, googleapis, etc.)
  - Auto-migration verifies read-back before clearing secrets.env plaintext
metrics:
  duration: 12m
  completed: 2026-04-18
  tasks: 3
  files: 6
---

# Phase 05 Plan 01: Credential Security + Network Hardening + CSP Summary

OS-native keyring credential storage with auto-migration from plaintext secrets.env, automated cloud-dependency detection, and CSP middleware blocking all external requests.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Integrate keyring for credential storage with auto-migration | ddb00b1 | config_service.py, smtp_client.py, sorter.py, tests/test_credential_security.py |
| 2 | Create automated no-cloud-dependency test | f62089a | tests/test_no_cloud_deps.py |
| 3 | Add CSP middleware to FastAPI app | c97a07a | app/__init__.py |

## Key Changes

### Credential Security (config_service.py)
- Added `keyring` integration with `SERVICE_NAME = "com.superhero-mail"`
- New helpers: `store_account_password()`, `get_account_password()`, `check_keyring_backend()`
- `inject_account_secret()` now checks keyring first, then env var, then secrets.env
- `migrate_from_secrets_env()` performs one-time migration with read-back verification
- `save_config()` stores passwords in keyring when saving new accounts
- Backend detection warns if keyring falls back to plaintext storage (Linux headless)

### Network Audit (tests/test_no_cloud_deps.py)
- Scans all `.py` files for `requests.get/post`, `urlopen`, `http.client` patterns
- Scans `.js`/`.html` files for `fetch()` calls to non-localhost URLs
- Allows localhost, configurable IMAP/SMTP/Ollama hosts, api.telegram.org
- Blocks hardcoded cloud API domains (openai, anthropic, googleapis, aws, firebase, etc.)
- Detects potential hardcoded secrets (api_key, password, token assignments)

### CSP Middleware (app/__init__.py)
- `CSPMiddleware` class adds `Content-Security-Policy` header to all responses
- `default-src 'self'` — only local resources by default
- `connect-src 'self' http://localhost:* http://127.0.0.1:*` — backend + Ollama
- `script-src` allows Tailwind CDN, jsdelivr, unpkg (current frontend dependencies)
- `frame-ancestors 'none'` — prevents clickjacking
- `form-action 'self'` — forms only submit locally

## Verification Results

```
13 tests passed in 0.09s
- test_credential_security.py: 10/10 passed
- test_no_cloud_deps.py: 3/3 passed
```

## Decisions Made

1. **Keyring-first priority:** OS keychain → env var → secrets.env file. Ensures migration is gradual and backward-compatible.
2. **Read-back verification:** `migrate_from_secrets_env()` verifies each password was stored correctly before clearing plaintext.
3. **Linux fallback awareness:** `check_keyring_backend()` warns if the backend is plaintext, so users know their credentials aren't encrypted at rest.
4. **CSP `unsafe-inline` + `unsafe-eval`:** Required for Tailwind CDN and Alpine.js to function. Can be tightened when migrating to bundled assets.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

No new threat surface introduced beyond what the threat model covers. All changes reduce existing threat surface (plaintext → keyring, no CSP → restrictive CSP).

## Self-Check: PASSED

All 6 files verified present. All 3 commits verified in git log.
