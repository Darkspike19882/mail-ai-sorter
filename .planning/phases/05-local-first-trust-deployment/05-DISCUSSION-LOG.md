# Phase 05: Local-First Trust & Deployment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 05-local-first-trust-deployment
**Areas discussed:** Credential Security, DSGVO Documentation, Network Hardening, Tauri Packaging Scope

---

## Credential Security

| Option | Description | Selected |
|--------|-------------|----------|
| OS Keyring/Keychain | `keyring` library for OS-native storage (macOS Keychain, Windows Credential Manager) | ✓ |
| Encrypted file (Fernet) | Encrypted file with master password, user enters at start | |
| Status quo + file perms | Keep secrets.env with chmod 600 | |

**User's choice:** OS Keyring/Keychain
**Notes:** Standard approach, no user interaction needed after setup

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-Migration | Detect secrets.env on first start, migrate to keyring, clear plaintext | ✓ |
| Fallback-Kompatibilität | New setup with keyring, read secrets.env as fallback | |

**User's choice:** Auto-Migration
**Notes:** Seamless transition from existing setup

---

## DSGVO Documentation

| Option | Description | Selected |
|--------|-------------|----------|
| Comprehensive PRIVACY.md | Full data inventory, processing docs, network flow, retention, user rights | ✓ |
| Minimal notice | Short README section: "all local, no cloud" | |
| Full + README summary | Both comprehensive PRIVACY.md and README summary | |

**User's choice:** Comprehensive PRIVACY.md

| Option | Description | Selected |
|--------|-------------|----------|
| Ja, Export + Delete API | /api/data/export and /api/data/delete endpoints for DSGVO rights | ✓ |
| Nur Anleitung | Documentation how to manually delete data | |
| Defer | Later. Documentation suffices for now | |

**User's choice:** Export + Delete API

---

## Network Hardening

| Option | Description | Selected |
|--------|-------------|----------|
| Automated test | pytest scan of all fetch/requests, allow only localhost + Ollama | ✓ |
| Manual review + docs | Code review + network flow diagram in PRIVACY.md | |
| Both (test + docs) | Test as safety net + docs for transparency | |

**User's choice:** Automated test

| Option | Description | Selected |
|--------|-------------|----------|
| CSP mit CDN-Allowlist | CSP header allowing only required CDNs, block everything else | ✓ |
| Nein, kein CSP | No CSP — CDN scripts are essential, complexity not worth it for local app | |

**User's choice:** CSP mit CDN-Allowlist

---

## Tauri Packaging Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to later phase | Focus on trust/hardening only. Tauri is a separate complex step. | ✓ |
| Minimal PoC | Brownfield mode + localhost plugin, proof of concept only | |
| Full packaging | Complete Tauri setup with PyInstaller sidecar, installers | |

**User's choice:** Defer to later phase

---

## OpenCode's Discretion

- PRIVACY.md structure and format
- Keyring service name and username format
- CSP header format and middleware placement
- Export format details
- Delete API granularity

## Deferred Ideas

- Tauri desktop packaging — deferred to dedicated phase
