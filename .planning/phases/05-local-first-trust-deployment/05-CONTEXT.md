# Phase 05: Local-First Trust & Deployment - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Ensure Superhero Mail operates as a fully local, privacy-conscious application with secure credential storage, DSGVO-compliant documentation, automated network verification, and data portability APIs. No cloud dependencies for any core workflow.

</domain>

<decisions>
## Implementation Decisions

### Credential Security
- **D-01:** Use OS-native keyring/keychain for IMAP password storage via Python `keyring` library. Replace current plaintext `secrets.env` approach.
- **D-02:** Auto-migrate existing `secrets.env` passwords to OS keyring on first app start. After successful migration, clear plaintext passwords from `secrets.env`.

### DSGVO Documentation
- **D-03:** Create comprehensive `PRIVACY.md` with: data inventory (what is stored where), processing documentation, network flow diagram, retention periods, and user rights (deletion/export).
- **D-04:** Implement data export API (`/api/data/export`) and data deletion API (`/api/data/delete`) to support DSGVO right to erasure and portability.

### Network Hardening
- **D-05:** Create automated pytest test (`tests/test_no_cloud_deps.py`) that scans all codebase `fetch`/`requests` calls and verifies only localhost and Ollama URLs are used. Blocks any accidental cloud integration.
- **D-06:** Add Content Security Policy (CSP) headers with allowlist for required CDNs (Tailwind CDN, Alpine.js, Lucide, DOMPurify) and block all other external script/image sources.

### Tauri Packaging
- **D-07:** Defer Tauri desktop packaging to a later phase. This phase focuses on trust, hardening, and documentation only.

### OpenCode's Discretion
- Exact structure and format of PRIVACY.md sections
- Implementation details of keyring integration (service name, username format)
- CSP header format and middleware placement
- Export format (ZIP with SQLite dump + config + templates?)
- Delete API granularity (per-account vs full wipe)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Constraints
- `.planning/PROJECT.md` — Local-first, DSGVO-compliant, open-source positioning
- `.planning/REQUIREMENTS.md` — LOCL-01, LOCL-03 requirements
- `.planning/ROADMAP.md` — Phase 5 definition and success criteria
- `.planning/phases/05-local-first-trust-deployment/05-RESEARCH.md` — Technical research with standard stack recommendations

### Existing Code
- `config_service.py` — Current config/secrets loading (reads secrets.env)
- `secrets.env` — Current plaintext credential storage
- `config.json` — Account configuration structure
- `smtp_client.py` — SMTP connection (needs credentials from keyring)
- `app/__init__.py` — FastAPI app setup (CSP middleware goes here)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config_service.py`: `load_config()`, `get_account()`, `inject_account_secret()` — these read from secrets.env currently and need keyring integration
- `app/__init__.py`: FastAPI app setup — CSP middleware can be added here
- Existing test infrastructure in `tests/` directory

### Established Patterns
- Config loading via `config_service.py` with secret injection
- FastAPI routers pattern for new API endpoints
- SQLite for local data storage

### Integration Points
- `config_service.py:inject_account_secret()` — primary point where keyring replaces secrets.env reading
- `app/__init__.py` — CSP middleware registration
- `smtp_client.py` — credential consumer that benefits from keyring

</code_context>

<specifics>
## Specific Ideas

- `keyring` library (v25.7.0) for OS-native credential storage, as identified in research
- Auto-migration flow: detect secrets.env → read passwords → store in keyring → wipe secrets.env
- CSP allowlist: cdn.tailwindcss.com, cdn.jsdelivr.net (Alpine, DOMPurify), unpkg.com (Lucide)
- Data export: ZIP file containing SQLite DB dump, config.json (without passwords), templates, tags
- Data delete: drop SQLite tables, clear config, remove keyring entries

</specifics>

<deferred>
## Deferred Ideas

- Tauri desktop packaging (brownfield mode + PyInstaller sidecar) — deferred to dedicated packaging phase
- Attachment/text extraction libraries for search indexing (SRCH-03) — still deferred
- Per-account max emails per automation run (AUTO-05) — v2 requirement

</deferred>

---

*Phase: 05-local-first-trust-deployment*
*Context gathered: 2026-04-18*
