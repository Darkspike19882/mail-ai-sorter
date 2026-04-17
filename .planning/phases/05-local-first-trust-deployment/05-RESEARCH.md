# Phase 5: Local-First Trust & Deployment - Research

**Researched:** 2026-04-17
**Domain:** Local-first security, credential management, privacy compliance, desktop packaging
**Confidence:** HIGH

## Summary

Phase 5 focuses on **verifying and hardening** the app's local-first claims, not building new features. The codebase already runs entirely locally — FastAPI backend on localhost, SQLite + FTS5 for storage, Ollama for LLM, IMAPClient for mail access. No cloud dependencies exist in the current code. The gaps are in **trustworthiness**: IMAP passwords are stored in plaintext (`secrets.env`), there's no formal proof that no data leaves the machine, and the DSGVO-conscious positioning lacks documented evidence.

The primary implementation work is credential security (migrate from plaintext to OS keychain), network hardening (audit outbound calls, configure CSP to block external requests), and privacy documentation (data inventory, processing documentation). Tauri desktop packaging is researched here as the recommended deployment path but is scoped as a future integration unless the planner includes it in this phase.

**Primary recommendation:** Secure credentials first (keyring library), audit all network calls, add CSP, then document everything. Tauri packaging is the recommended path for a "daily driver" desktop experience but is additive, not blocking.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOCL-01 | User can use the app without any required cloud service for core mail, search, and AI workflows. | Network audit methodology (Section: Architecture Patterns → Network Audit), CSP configuration (Section: Code Examples), Ollama offline resilience (Section: Common Pitfalls) |
| LOCL-03 | User can operate the app in a way that supports a local, DSGVO-conscious deployment model. | Credential security migration (Section: Architecture Patterns → Credential Migration), Privacy documentation framework (Section: Architecture Patterns → Privacy Documentation), Data inventory template (Section: Code Examples) |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| keyring | 25.7.x | OS-native credential storage (macOS Keychain, Linux Secret Service, Windows Credential Manager) | The standard Python library for secure credential storage. Replaces plaintext secrets.env with platform-native encrypted storage. Cross-platform, maintained by jaraco. [VERIFIED: pip registry] |
| PyInstaller | 6.19.x | Bundle Python FastAPI app as standalone executable for Tauri sidecar | The standard tool for packaging Python apps as single binaries. Required when moving to Tauri desktop packaging. Handles data files, templates, and implicit imports. [VERIFIED: pip registry] |

### Supporting (Tauri Desktop — Future Integration)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tauri-apps/cli | 2.10.x | Tauri build tooling and dev server | Desktop packaging. Brownfield mode loads existing localhost FastAPI. [VERIFIED: npm registry] |
| @tauri-apps/api | 2.10.x | Tauri JavaScript/TypeScript API bridge | Desktop packaging. Window management, events, sidecar control. [VERIFIED: npm registry] |
| tauri-plugin-keyring | 2.3.x | Tauri-native keychain integration | Desktop packaging. Frontend-side credential management via OS keychain. [VERIFIED: npm registry, Context7] |
| @tauri-apps/plugin-shell | 2.x | Sidecar binary management from Tauri | Desktop packaging. Starts/stops the FastAPI sidecar binary. [VERIFIED: npm registry] |
| tauri-plugin-localhost | latest | Serve localhost content in Tauri webview | Desktop packaging. Brownfield pattern for loading http://localhost:PORT. [CITED: v2.tauri.app/plugin/localhost] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| keyring (Python) | cryptography.fernet encrypted file | keyring uses OS-native stores (Keychain/SecretService/Credential Manager) which is more secure and what users expect. Fernet would still need a master password or stored key. Use keyring. |
| PyInstaller | Nuitka, cx_Freeze | PyInstaller is the most widely used, has the best ecosystem support for FastAPI/Pydantic, and is explicitly recommended in Tauri sidecar docs. [CITED: v2.tauri.app/develop/sidecar] |
| tauri-plugin-keyring | Custom Rust keyring crate | The plugin provides a complete JS/TS API and wraps platform keychains. Use the plugin rather than building custom Rust keyring code. [VERIFIED: Context7] |

**Installation:**
```bash
# Credential security (required this phase)
pip install keyring>=25.7.0

# Desktop packaging (future phase)
pip install pyinstaller>=6.19.0
npm install --save-dev @tauri-apps/cli@^2.10.0
npm install @tauri-apps/api@^2.10.0 @tauri-apps/plugin-shell@^2.0.0 tauri-plugin-keyring@^2.3.0
```

**Version verification:**
```
keyring: 25.7.0 (verified 2026-04-17 via pip registry)
pyinstaller: 6.19.0 (verified 2026-04-17 via pip registry)
@tauri-apps/cli: 2.10.1 (verified 2026-04-17 via npm registry)
tauri-plugin-keyring: 2.3.5 (verified 2026-04-17 via npm registry)
```

## Architecture Patterns

### Recommended Project Structure (for Desktop Packaging)

```
mail-ai-sorter/
├── src-tauri/           # Tauri shell (future)
│   ├── binaries/        # PyInstaller output goes here
│   │   └── superhero-mail-backend-{target-triple}  # sidecar binary
│   ├── capabilities/    # Tauri security capabilities
│   ├── tauri.conf.json  # CSP, sidecar config, security
│   └── src/
│       └── main.rs      # Tauri app entry (brownfield + localhost plugin)
├── app/                 # FastAPI application (current)
│   ├── routers/         # API routes
│   └── models/          # Pydantic models
├── services/            # Business logic (current)
├── config_service.py    # Config + secret loading (MIGRATE to keyring)
├── templates/           # Jinja2 templates
├── static/              # Frontend assets
└── PRIVACY.md           # DSGVO documentation (NEW)
```

### Pattern 1: Credential Migration (secrets.env → OS Keychain)

**What:** Replace plaintext `secrets.env` file with OS-native credential storage via Python `keyring` library.

**When to use:** All IMAP password storage and retrieval.

**Why:** Plaintext files containing passwords are the #1 trust gap in a DSGVO-conscious local app. Even with `chmod 600`, the passwords are readable by any process running as the same user. OS keychain stores them encrypted and requires user authentication.

**Migration strategy:**
```python
# Source: keyring library documentation [VERIFIED: pip registry]
import keyring

SERVICE_NAME = "com.superhero-mail"

def store_account_password(account_name: str, password: str) -> None:
    """Store password in OS keychain."""
    keyring.set_password(SERVICE_NAME, account_name, password)

def get_account_password(account_name: str) -> str:
    """Retrieve password from OS keychain."""
    return keyring.get_password(SERVICE_NAME, account_name) or ""

def migrate_from_secrets_env() -> dict:
    """One-time migration: read secrets.env, store in keychain, return results."""
    from config_service import load_secrets
    secrets = load_secrets()
    migrated = {}
    for key, value in secrets.items():
        if "_PASSWORD" in key:
            account_name = key.replace("_PASSWORD", "").lower()
            keyring.set_password(SERVICE_NAME, account_name, value)
            migrated[key] = account_name
    return migrated
```

**Key insight:** The existing `config_service.py` already has `inject_account_secret()` which reads from `secrets.env` or environment variables. The migration modifies this function to check keyring first, then fall back to env vars for backward compatibility.

### Pattern 2: Network Audit — Proving No Cloud Dependency

**What:** Systematic scan of all outbound network requests to verify no cloud API calls exist.

**When to use:** LOCL-01 verification. One-time audit plus ongoing CI check.

**Methodology:**
1. Grep for all `urllib.request.urlopen`, `requests.get/post`, `fetch(`, `http://`, `https://` in Python and JS code
2. Classify each match: local (localhost/127.0.0.1) vs external
3. Verify all external calls are to IMAP/SMTP servers (user-configured, not hardcoded cloud APIs)
4. Document the findings in a network-audit section of PRIVACY.md

**Automated verification script pattern:**
```python
# Pattern for ongoing CI verification
import subprocess, re

def audit_network_calls():
    """Scan codebase for external network calls. Returns list of findings."""
    result = subprocess.run(
        ["grep", "-rn", "urlopen\\|requests\\.get\\|requests\\.post\\|fetch(",
         "--include=*.py", "--include=*.js", "--include=*.ts", "."],
        capture_output=True, text=True
    )
    findings = []
    for line in result.stdout.splitlines():
        # Filter: allow localhost, 127.0.0.1, configurable IMAP hosts
        if not any(s in line for s in ["localhost", "127.0.0.1", "ollama_url"]):
            findings.append(line)
    return findings
```

### Pattern 3: CSP Configuration for Local-First Webview

**What:** Content Security Policy that allows localhost API communication but blocks all external requests.

**When to use:** Tauri webview configuration, and as a documentation pattern for the current browser-based usage.

**Example (tauri.conf.json):**
```json
// Source: Tauri v2 CSP docs [VERIFIED: Context7 / v2.tauri.app/security/csp]
{
  "app": {
    "security": {
      "csp": {
        "default-src": "'self' customprotocol: asset:",
        "connect-src": "ipc: http://ipc.localhost http://localhost:5001 http://127.0.0.1:5001",
        "img-src": "'self' asset: http://asset.localhost blob: data:",
        "style-src": "'unsafe-inline' 'self'",
        "script-src": "'self' 'unsafe-inline'"
      },
      "pattern": {
        "use": "brownfield"
      }
    }
  }
}
```

**Critical:** The `connect-src` must include the FastAPI sidecar port (5001 or chosen port). Only localhost addresses are allowed. No `https://` external origins.

### Pattern 4: Tauri Brownfield + Sidecar Architecture

**What:** Package the existing FastAPI app as a Tauri sidecar binary and load it via the localhost plugin in brownfield mode.

**When to use:** Desktop packaging phase (future, but documented here for planning).

**Architecture:**
```
[Tauri Shell (Rust)]
  ├── Starts sidecar binary (FastAPI via PyInstaller)
  ├── Loads http://localhost:5001 in webview via localhost plugin
  ├── CSP blocks all external requests
  └── Manages app lifecycle (start/stop sidecar)

[FastAPI Sidecar (Python)]
  ├── Serves Jinja2 templates + static files
  ├── Handles IMAP, SQLite, Ollama communication
  ├── Runs on localhost only (bind to 127.0.0.1)
  └── Reports health via /api/health endpoint
```

**Sidecar registration (tauri.conf.json):**
```json
// Source: Tauri sidecar docs [VERIFIED: Context7 / v2.tauri.app/develop/sidecar]
{
  "bundle": {
    "externalBin": ["binaries/superhero-mail-backend"]
  }
}
```

**Sidecar naming convention:** Binary must include target triple:
- macOS ARM: `superhero-mail-backend-aarch64-apple-darwin`
- macOS Intel: `superhero-mail-backend-x86_64-apple-darwin`
- Linux: `superhero-mail-backend-x86_64-unknown-linux-gnu`

**Sidecar startup from Tauri (TypeScript):**
```typescript
// Source: Tauri sidecar docs [VERIFIED: Context7]
import { Command } from '@tauri-apps/plugin-shell';

const command = Command.sidecar('binaries/superhero-mail-backend');
const child = await command.spawn();

// Wait for FastAPI to be ready
await waitForHealthCheck('http://localhost:5001/api/health');
```

### Pattern 5: Ollama Resilience in Desktop Context

**What:** Robust handling of Ollama startup, health checks, and graceful degradation.

**When to use:** All LLM-dependent features (summary, reply drafting, classification).

**Pattern:**
```python
import urllib.request
import json
import time

OLLAMA_STARTUP_TIMEOUT = 60  # seconds
OLLAMA_HEALTH_RETRIES = 5

def check_ollama_health(ollama_url: str) -> dict:
    """Check if Ollama is running and model is available."""
    try:
        r = urllib.request.urlopen(f"{ollama_url}/api/version", timeout=5)
        version = json.loads(r.read().decode()).get("version", "unknown")
        return {"running": True, "version": version}
    except Exception:
        return {"running": False, "version": None}

def ensure_ollama_ready(ollama_url: str, model: str) -> bool:
    """Wait for Ollama to be ready, with timeout."""
    for attempt in range(OLLAMA_HEALTH_RETRIES):
        health = check_ollama_health(ollama_url)
        if health["running"]:
            return True
        time.sleep(OLLAMA_STARTUP_TIMEOUT / OLLAMA_HEALTH_RETRIES)
    return False
```

**UI degradation:** When Ollama is unavailable, AI-powered features show a clear status message ("KI nicht verfügbar — Ollama läuft nicht") and fall back to manual workflows. Never block the entire app.

### Pattern 6: Privacy Documentation Framework

**What:** Structured documentation that enables users to evaluate DSGVO compliance.

**When to use:** LOCL-03 fulfillment.

**Required documents:**
1. **Data Inventory** (in PRIVACY.md): What data is stored, where, for how long
2. **Processing Documentation**: What processing happens on each data type
3. **Network Flow Diagram**: All inbound/outbound connections with justification
4. **Data Subject Rights**: How users can access, export, delete their data

### Anti-Patterns to Avoid

- **Storing passwords in config.json or plaintext files:** Even with chmod 600, this is the #1 trust gap. Use OS keychain. [ASSUMED based on security best practices]
- **Broad CSP allowing all localhost ports:** Only allow the specific FastAPI port. Broad localhost access weakens the security boundary.
- **Silent failure when Ollama is down:** The app must clearly communicate LLM unavailability rather than hanging or showing generic errors.
- **Hardcoded model names in health checks:** The configured model might not be the default. Always read from config.
- **Bundling Ollama itself in the app:** Ollama should remain a separate install. Bundling a 4.7GB model binary is impractical and users need to manage models themselves.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OS credential storage | Custom encrypted file, AES encryption of secrets.env | `keyring` Python library | Platform-native stores handle encryption, access control, key rotation, and biometric unlock. You will get the edge cases wrong (keychain locked, Secret Service unavailable, Credential Manager behavior). [VERIFIED: pip registry] |
| CSP headers | Manual header injection | Tauri's built-in CSP configuration | Tauri injects CSP automatically and handles nonces/hashes for bundled code. Manual injection fights the framework. [VERIFIED: Context7] |
| Python binary packaging | Custom build scripts, zipapp | PyInstaller | Handles implicit imports (FastAPI/Pydantic use dynamic imports), data files, platform-specific extensions, and produces a single binary. [VERIFIED: pip registry, Context7] |
| SSL/TLS contexts | Custom certificate handling | `ssl.create_default_context()` | Already used correctly in imap_service.py. Don't change this. |
| IMAP connection pooling | Custom pool implementation | Existing `cache_service._imap_pool` | Already implemented. Don't rebuild. |

**Key insight:** The trust and security value comes from using proven, audited libraries — not from building custom security code. Custom crypto and credential management is a red flag in a privacy-focused app.

## Common Pitfalls

### Pitfall 1: Keyring Backend Unavailability on Linux
**What goes wrong:** `keyring` falls back to a plaintext backend on Linux if no Secret Service daemon is running (common on minimal/headless installs).
**Why it happens:** Linux doesn't have a universal keychain. `keyring` depends on `secretstorage` which requires a D-Bus Secret Service (like gnome-keyring or KDE Wallet).
**How to avoid:** Check `keyring.get_keyring()` backend name at startup. If it's `plaintext.Keyring`, warn the user and fall back to environment variables with a clear warning message.
**Warning signs:** `keyring.get_password()` works but data is stored in `~/.local/share/python_keyring/` (plaintext).

### Pitfall 2: PyInstaller Missing Implicit Imports
**What goes wrong:** FastAPI and Pydantic use dynamic imports that PyInstaller's static analysis misses, causing `ModuleNotFoundError` at runtime.
**Why it happens:** PyInstaller can't detect imports hidden behind string-based module loading.
**How to avoid:** Use `--hidden-import` flags or a spec file with explicit `hiddenimports`:
```bash
pyinstaller --hidden-import=uvicorn.logging --hidden-import=uvicorn.loops \
  --hidden-import=uvicorn.loops.auto --hidden-import=uvicorn.protocols \
  --hidden-import=uvicorn.protocols.http --hidden-import=uvicorn.protocols.http.auto \
  --hidden-import=uvicorn.protocols.websockets --hidden-import=uvicorn.protocols.websockets.auto \
  --hidden-import=uvicorn.lifespan --hidden-import=uvicorn.lifespan.on \
  --hidden-import=pydantic.deprecated.decorator run.py
```
**Warning signs:** App starts fine from source but crashes when run from PyInstaller bundle.

### Pitfall 3: CSP Blocks Sidecar Communication
**What goes wrong:** CSP is configured too restrictively and blocks the webview from making API calls to the FastAPI sidecar on localhost.
**Why it happens:** CSP `connect-src` must explicitly list the sidecar's URL. If only `'self'` is set, localhost API calls will fail.
**How to avoid:** Always include `http://localhost:PORT` and `http://127.0.0.1:PORT` in `connect-src`. Test CSP by making API calls from the webview before declaring it done.
**Warning signs:** Webview loads but API calls fail with CSP violation errors in console.

### Pitfall 4: Ollama First-Load Latency
**What goes wrong:** When Ollama starts for the first time or switches models, the first inference can take 30-60 seconds while the model loads into memory.
**Why it happens:** Ollama unloads models after `keep_alive` timeout (default 5 minutes). First request after timeout triggers a reload.
**How to avoid:** Set `keep_alive: "30m"` in Ollama API calls (already done in llm_helper.py). Show a loading state with progress indication during first inference. Consider a "warm-up" call on app start.
**Warning signs:** Users report "app is frozen" when actually the LLM is loading.

### Pitfall 5: secrets.env Migration Breaks Existing Users
**What goes wrong:** One-time migration from secrets.env to keychain fails silently, leaving users unable to connect to IMAP.
**Why it happens:** Migration runs once, writes to keyring, but doesn't verify the keyring write succeeded. If keyring fails, the env file might already be deleted or the code path changed.
**How to avoid:** Migration must be: (1) read from secrets.env, (2) write to keyring, (3) verify read-back from keyring, (4) only THEN stop reading secrets.env. Keep secrets.env as fallback for one version cycle.
**Warning signs:** After upgrade, IMAP connections fail with "authentication failed".

### Pitfall 6: Tauri Sidecar Port Conflict
**What goes wrong:** FastAPI sidecar can't start because port 5001 is already in use.
**Why it happens:** User runs another instance, or a previous instance didn't shut down cleanly.
**How to avoid:** Implement dynamic port selection: try the default port, if occupied try port+1, etc. Pass the selected port to the webview. Always clean up on app quit (kill sidecar process).
**Warning signs:** Sidecar starts but webview shows connection refused, or two instances run simultaneously.

## Code Examples

### Credential Migration (config_service.py modification)

```python
# Source: keyring library [VERIFIED: pip registry] + current config_service.py
import keyring
import os
from typing import Any, Dict, Optional
from pathlib import Path

SERVICE_NAME = "com.superhero-mail"

def inject_account_secret(account: Dict[str, Any]) -> Dict[str, Any]:
    """Inject password into account config. Checks keyring first, then env."""
    resolved = dict(account)
    env_key = resolved.get("password_env", "")
    if env_key and not resolved.get("password"):
        # Priority: 1) keyring, 2) env var, 3) secrets.env file
        password = keyring.get_password(SERVICE_NAME, env_key)
        if not password:
            password = os.getenv(env_key, "")
            if not password:
                secrets = load_secrets()
                password = secrets.get(env_key, "")
        resolved["password"] = password
    return resolved
```

### Ollama Health Check with Status Reporting

```python
# Source: current health_routes.py pattern + Ollama API docs [VERIFIED: Context7]
import urllib.request
import json

def check_ollama_status(ollama_url: str, expected_model: str) -> dict:
    """Full Ollama status check: running + model available."""
    try:
        # Check Ollama is running
        r = urllib.request.urlopen(f"{ollama_url}/api/version", timeout=5)
        version = json.loads(r.read().decode()).get("version", "?")

        # Check model is available
        r = urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5)
        models = json.loads(r.read().decode()).get("models", [])
        model_names = [m.get("name", "") for m in models]
        model_available = any(expected_model in name for name in model_names)

        return {
            "running": True,
            "version": version,
            "model_available": model_available,
            "model_name": expected_model,
            "status": "ready" if model_available else "model_missing"
        }
    except Exception as e:
        return {
            "running": False,
            "version": None,
            "model_available": False,
            "status": "unavailable",
            "error": str(e)[:100]
        }
```

### Privacy Data Inventory Template

```markdown
# Data Inventory — Superhero Mail

## Data Stored Locally

| Data Type | Location | Retention | Encryption | Purpose |
|-----------|----------|-----------|------------|---------|
| Email metadata (subject, from, date) | SQLite (mail_index.db) | Until user deletes | No (local only) | Search, thread view |
| Email body content | SQLite (mail_index.db) | Until user deletes | No (local only) | Search, AI processing |
| AI conversation history | SQLite (llm_memory.db) | Until user deletes | No (local only) | Context continuity |
| Email summaries | SQLite (llm_memory.db) | Until user deletes | No (local only) | Quick overview |
| Account configuration | config.json | Persistent | No | App configuration |
| IMAP passwords | OS Keychain | Persistent | Yes (OS-managed) | Mail server access |
| Sort actions log | SQLite (mail_index.db) | Until user deletes | No (local only) | Reviewability |

## Data That Leaves the Machine

| Destination | Data | Protocol | User Configurable |
|-------------|------|----------|-------------------|
| IMAP server | Login credentials, email reads/moves | IMAP over TLS | Yes (user-configured server) |
| SMTP server | Outbound emails | SMTP over TLS | Yes (user-configured server) |
| Ollama (localhost) | Email content for AI processing | HTTP (localhost only) | Yes (model, URL configurable) |

## Data That NEVER Leaves the Machine

- Email body content (except when sent via SMTP by user action)
- AI conversation history
- Search index
- Account passwords
- User facts and preferences
- Sort action logs

## No Cloud Services

This application does NOT use:
- Cloud storage or sync
- Cloud AI APIs (no OpenAI, Anthropic, Google AI)
- Analytics or telemetry services
- Crash reporting services
- Advertising networks
```

### Tauri Sidecar Lifecycle (Rust)

```rust
// Source: Tauri v2 docs [VERIFIED: Context7 / v2.tauri.app]
use tauri::{Manager, WebviewWindowBuilder, WebviewUrl};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_localhost::Builder as LocalhostBuilder;

fn main() {
    let port: u16 = 5001;

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_keyring::Builder::new("com.superhero-mail").build())
        .plugin(LocalhostBuilder::new(port).build())
        .setup(move |app| {
            // Start FastAPI sidecar
            let sidecar_command = app.shell().sidecar("binaries/superhero-mail-backend").unwrap();
            let (_rx, _child) = sidecar_command.spawn().unwrap();

            // Load localhost in webview
            let url = format!("http://localhost:{}", port).parse().unwrap();
            WebviewWindowBuilder::new(app, "main".to_string(), WebviewUrl::External(url))
                .title("Superhero Mail")
                .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plaintext secrets files | OS-native keychain storage via `keyring` | Standard practice since 2020+ | Passwords are encrypted at rest, tied to user login |
| Electron for desktop apps | Tauri 2 for local-first apps | Tauri 2 stable 2024 | 10-100x smaller binary, native webview, better security model |
| Broad CSP (`*`) | Restricted CSP with explicit localhost | CSP best practice since 2018 | Prevents accidental data exfiltration via XSS |
| Manual network audit | Automated grep + CI check | Standard practice | Continuous verification of no-cloud-dependency claim |

**Deprecated/outdated:**
- `keyring` `keyrings.alt` backends: Avoid the plaintext and encrypted file backends. Use only OS-native backends. [CITED: keyring docs]
- Tauri 1 sidecar patterns: Tauri 2 changed the plugin API significantly. Use v2 patterns only. [VERIFIED: Context7]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Linux Secret Service is available on most desktop Linux installs | Credential Migration | Users on headless/minimal Linux may need fallback; keyring handles this but code must detect it |
| A2 | Users accept Ollama as a separate install requirement | Ollama Resilience | If users expect bundled LLM, the install story is more complex; document clearly |
| A3 | DSGVO compliance for a local-only, no-cloud app primarily requires documentation rather than technical measures | Privacy Documentation | If DSGVO requires specific technical measures beyond what exists, scope may increase |
| A4 | The current FastAPI app can run as a PyInstaller one-file bundle without significant restructuring | Desktop Packaging | Some dynamic imports or data file loading patterns may need adjustment |
| A5 | macOS Keychain access from Python keyring does not require code signing | Credential Migration | On macOS, unsigned apps may trigger keychain access prompts; verify during implementation |

**Claims needing user confirmation:**
- A3 (DSGVO scope) — verify with user if they have specific compliance requirements beyond documentation
- A5 (code signing) — verify if they plan to code-sign the app for distribution

## Open Questions

1. **Is Tauri desktop packaging in scope for this phase or deferred?**
   - What we know: The phase description focuses on "local-first trust & deployment" but Tauri is listed as a key research area. The current app works as a web app on localhost.
   - What's unclear: Whether the planner should include actual Tauri integration tasks or just prepare the architecture.
   - Recommendation: **Defer Tauri integration to a separate phase.** This phase should focus on credential security, privacy documentation, and CSP. Tauri packaging is additive.

2. **What DSGVO documentation level is needed?**
   - What we know: The app is single-user, local-only, no cloud. DSGVO primarily applies to data controllers processing others' data.
   - What's unclear: Whether the user needs formal DSGVO compliance documentation or just a clear privacy statement.
   - Recommendation: Create a comprehensive `PRIVACY.md` with data inventory, processing documentation, and network flow diagram. This satisfies LOCL-03 without over-engineering.

3. **Should the network audit be automated in CI?**
   - What we know: A one-time grep audit is sufficient for verification. CI integration adds ongoing assurance.
   - What's unclear: Whether the project has CI set up.
   - Recommendation: Include the audit as a test file (`tests/test_no_cloud_deps.py`) that can be run manually and later integrated into CI.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | FastAPI backend | ✓ | 3.14.4 | — |
| Ollama | Local LLM | ✓ | 0.21.0 | — |
| SQLite | Data storage | ✓ | 3.53.0 | — |
| keyring (Python) | Credential storage | ✓ | 25.7.0 | env vars (with warning) |
| PyInstaller | Desktop packaging | ✓ | 6.19.0 | — |
| Node.js | Tauri tooling | ✓ | 25.8.2 | — |
| npm | Tauri tooling | ✓ | 11.11.1 | — |
| Rust/Cargo | Tauri compilation | ✗ | — | Install via rustup when Tauri phase starts |
| macOS security CLI | Keychain testing | ✓ | — | — |

**Missing dependencies with no fallback:**
- Rust/Cargo: Required only for Tauri compilation. Not needed for credential security and privacy documentation work in this phase. Can be installed via `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh` when Tauri phase begins.

**Missing dependencies with fallback:**
- None for the core phase work (credential security + privacy docs).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (Python stdlib) |
| Config file | none — tests in `tests/` directory |
| Quick run command | `python3 -m pytest tests/ -x -q` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOCL-01 | No external network calls to cloud services in codebase | unit | `python3 -m pytest tests/test_no_cloud_deps.py -x` | ❌ Wave 0 |
| LOCL-01 | App functions when Ollama is unavailable | unit | `python3 -m pytest tests/test_ollama_resilience.py -x` | ❌ Wave 0 |
| LOCL-03 | Credentials stored in OS keychain, not plaintext | unit | `python3 -m pytest tests/test_credential_security.py -x` | ❌ Wave 0 |
| LOCL-03 | Data inventory document exists and is complete | manual | verify PRIVACY.md exists and has all sections | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_no_cloud_deps.py tests/test_credential_security.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green + PRIVACY.md review complete

### Wave 0 Gaps
- [ ] `tests/test_no_cloud_deps.py` — covers LOCL-01 (network audit)
- [ ] `tests/test_credential_security.py` — covers LOCL-03 (keyring integration)
- [ ] `tests/test_ollama_resilience.py` — covers LOCL-01 (graceful degradation)
- [ ] Framework install: `pip install pytest` — if not already available

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (IMAP login) | OS keychain for credential storage, TLS for IMAP connections |
| V3 Session Management | no | Single-user local app, no sessions |
| V4 Access Control | no | Single-user local app |
| V5 Input Validation | yes | Pydantic models on all API endpoints, IMAP response parsing |
| V6 Cryptography | yes | TLS for IMAP/SMTP connections, OS-managed keychain encryption |

### Known Threat Patterns for Local Mail Client

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential theft from plaintext files | Information Disclosure | OS keychain storage (keyring library) |
| XSS leading to data exfiltration | Tampering, Information Disclosure | CSP blocking external connections |
| IMAP credential interception | Spoofing, Information Disclosure | TLS (`ssl.create_default_context()`) — already implemented |
| Local network eavesdropping | Information Disclosure | Bind FastAPI to 127.0.0.1 only (already done) |
| Model injection via Ollama prompts | Tampering | Input sanitization, bounded model outputs |

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/v2_tauri_app` — Tauri v2 sidecar, CSP, brownfield pattern, localhost plugin
- Context7 `/charlesportwoodii/tauri-plugin-keyring` — Keyring plugin API, TypeScript usage
- Context7 `/pyinstaller/pyinstaller` — PyInstaller one-file bundling, data files, hidden imports
- pip registry (2026-04-17) — keyring 25.7.0, pyinstaller 6.19.0, fastapi 0.136.0
- npm registry (2026-04-17) — @tauri-apps/cli 2.10.1, tauri-plugin-keyring 2.3.5
- Codebase analysis — config_service.py, app/__init__.py, services/llm_service.py, services/imap_service.py

### Secondary (MEDIUM confidence)
- Tauri v2 official docs: v2.tauri.app/security/csp — CSP configuration format
- Tauri v2 official docs: v2.tauri.app/develop/sidecar — sidecar pattern and naming
- Ollama API docs: localhost API, model management, keep_alive configuration

### Tertiary (LOW confidence)
- A3: DSGVO compliance scope for local-only single-user app — needs user confirmation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified against registries, APIs verified via Context7
- Architecture: HIGH — patterns derived from official Tauri and keyring documentation
- Pitfalls: HIGH — based on well-documented issues in PyInstaller, keyring, and Ollama ecosystems
- DSGVO scope: MEDIUM — assumption about documentation-level compliance, needs user confirmation

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (stable — these are mature libraries with infrequent breaking changes)
