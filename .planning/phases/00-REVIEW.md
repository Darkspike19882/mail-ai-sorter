# Code Review: mail-ai-sorter

**Datum:** 2026-04-17  
**Scope:** Alle Python-Dateien (38 Dateien)  
**Typ:** Standard Review

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 2 |
| Warning  | 12 |
| Info     | 8 |

---

## Critical Findings

### C1: Hardcoded Credentials
**Dateien:** `sorter.py:714`, `services/imap_service.py:51`, `config_service.py:70-78`

```python
# sorter.py:714
pw = cfg.get("password") or os.getenv(cfg.get("password_env", ""))
```

**Problem:** Passwörter werden teils aus Config, teils aus Environment geladen. Keine klare Strategie. `password_env` wird dynamisch generiert (`ACCOUNT_1_PASSWORD`), aber das Secret landet später in `secrets.env`.

**Empfehlung:** Klares Security-Modell:
1. NUR Environment-Variablen für Secrets
2. `secrets.env` nur für Telegram-Bot-Token (nicht IMAP-Passwörter)
3. Oder: Keyring-Integration für IMAP-Passwörter

### C2: Silent Exception Handling
**Dateien:** Fast alle Dateien (81 Stellen)

```python
# Beispiel: sorter.py:821
except Exception:
    pass
```

**Problem:** Exceptions werden geschluckt ohne Logging. Debugging unmöglich. Kritische Fehler (IMAP-Verbindung, Ollama) werden ignoriert.

**Empfehlung:**
```python
# Statt:
except Exception:
    pass

# Besser:
except ValueError as e:
    log(f"[{name}] Config-Fehler: {e}")
except ConnectionError as e:
    log(f"[{name}] Verbindungsfehler: {e}")
except Exception as e:
    log(f"[{name}] Unerwarteter Fehler: {e}", exc_info=True)
```

---

## Warning Findings

### W1: Missing Type Hints
**Dateien:** `services/imap_service.py`, `services/stats_service.py`, `llm_helper.py`

Viele Funktionen ohne Type Hints. Ab ~500 Zeilen Code wird das kritisch.

### W2: Connection Pool Leak
**Datei:** `services/imap_service.py:36-61`

```python
try:
    conn = _imap_pool.get(account)
    if conn is not None:
        return conn
except Exception:
    pass  # Fallback
```

Pooled Connections werden nie zurückgegeben. Nach ein paar Requests -> Connection-Limit erreicht.

### W3: Missing TTL for Cache
**Datei:** `services/cache_service.py:245`

```python
# Kein TTL gesetzt = Default 300s
@cached()
def get_stats():
    ...
```

Stats ändern sich selten - TTL könnte 60s oder 5min sein.

### W4: Hardcoded Model Names
**Datei:** `sorter.py:330-380`

```python
_MODEL_PROMPTS = {
    "llama3.1:8b": {...},
    "gemma4:e4b": {...},
```

Prompts sind hardcoded. Neue Modelle erfordern Code-Änderung.

### W5: No Input Validation
**Dateien:** `routes/inbox_routes.py`, `routes/llm_routes.py`

User-Input (JSON-Bodies) wird nicht validiert. Potentielle Injection-Risiken.

### W6: Race Condition in Sender Cache
**Datei:** `sorter.py:65-70`

```python
with lock:
    with open(tmp, "w") as f:
        json.dump(cache, f, ...)
    os.replace(tmp, cache_path)
```

Atomic write ist gut, aber bei Parallel-Accounts könnte es trotzdem Race Conditions geben.

### W7: No Rate Limiting
**Dateien:** `routes/llm_routes.py:14-31`

LLM-Endpoints haben kein Rate Limiting. DoS-Risiko bei öffentlichem Zugriff.

### W8: Missing Error Handling in Async
**Datei:** `sorter_daemon.py:44`

```python
def _send_digest_if_due(state):
    try:
        ...
    except Exception:
        pass  # Silent fail
```

### W9: Unused Variables
**Datei:** `index.py:402`

```python
except Exception:  # 'e' never used
    pass
```

### W10: Inconsistent Error Responses
**Dateien:** Alle `routes/*.py`

Manche geben JSON zurück, manche HTML, manche HTTP-Codes.

### W11: No Request Timeout
**Dateien:** `routes/inbox_routes.py:215-220`

IMAP-Requests haben kein explizites Timeout. Bei langsamen Servern -> Hang.

### W12: Memory Leak in RAG
**Datei:** `rag_engine.py:215`

```python
except Exception:
    pass  # Vector DB Fehler wird ignoriert
```

---

## Info Findings

### I1: Missing `__all__` Exports
**Dateien:** Alle Module

Keine expliziten Public APIs definiert.

### I2: Docstrings Incomplete
Viele Funktionen ohne oder mit minimalen Docstrings.

### I3: Flask vs FastAPI Hybrid
Das Projekt nutzt Flask (Web-UI) aber die AGENTS.md empfiehlt FastAPI. Migration nötig.

### I4: Test Coverage Unknown
Nur 1 Test-Datei: `tests/test_inbox_phase1.py`

### I5: Config Validation Missing
`config_service.py:24` - Config wird nicht schema-validiert.

### I6: Logging Inconsistent
Manche Funktionen nutzen `print()`, andere `logging`.

### I7: Missing `__init__.py` in Tests
`tests/__init__.py` fehlt.

### I8: No Health Check for Ollama
`routes/health_routes.py` prüft Flask, aber nicht Ollama-Zustand.

---

## Auto-Fixable Issues

| Finding | Fix Typ | Complexity |
|---------|--------|------------|
| Silent `pass` Exceptions | Ersetzen durchlogging | Niedrig |
| Missing Type Hints | Typen hinzufügen | Mittel |
| No Rate Limiting | Add slowapi | Niedrig |
| Inconsistent Error Responses | Standardisieren | Mittel |
| Missing `__all__` | hinzufügen | Niedrig |

---

## next_steps

1. **Critical Fixes zuerst:**
   - [ ] C2: Exception-Logging in allen Routes
   - [ ] C1: Security-Audit für Credentials

2. **Architecture:**
   - [ ] Flask → FastAPI Migration (laut AGENTS.md)
   - [ ] Connection Pool Refactoring

3. **Testing:**
   - [ ] Test-Coverage erhöhen
   - [ ] Integration-Tests für IMAP/Ollama