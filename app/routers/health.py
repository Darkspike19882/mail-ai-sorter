import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter

from config_service import load_config, load_secrets
from services import imap_service, sorter_service

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
INDEX_DB = BASE_DIR / "mail_index.db"
MEMORY_DB = BASE_DIR / "llm_memory.db"

_health_state = {
    "last_check": None,
    "status": "unknown",
    "checks": {},
    "uptime_start": datetime.now().isoformat(),
    "total_requests": 0,
    "errors_last_hour": 0,
    "last_error": None,
}


@router.get("/api/health")
async def api_health():
    checks = {}
    overall = "healthy"
    cfg = load_config()
    checks["config"] = {
        "ok": "global" in cfg,
        "detail": "Config geladen" if "global" in cfg else "Config fehlt/fehlerhaft",
    }
    try:
        import urllib.request

        ollama_url = cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434")
        r = urllib.request.urlopen(ollama_url + "/api/version", timeout=5)
        d = json.loads(r.read().decode())
        checks["ollama"] = {"ok": True, "detail": f"v{d.get('version', '?')}"}
    except Exception as e:
        checks["ollama"] = {"ok": False, "detail": str(e)[:80]}
        overall = "degraded"
    accs = cfg.get("accounts", [])
    if accs:
        acc = dict(accs[0])
        try:
            conn = imap_service.connect(acc)
            conn.select("INBOX", readonly=True)
            conn.logout()
            checks["imap"] = {"ok": True, "detail": f"{acc['name']} verbunden"}
        except Exception as e:
            checks["imap"] = {"ok": False, "detail": str(e)[:80]}
            overall = "degraded"
    else:
        checks["imap"] = {"ok": None, "detail": "Keine Konten konfiguriert"}
    secrets = load_secrets()
    tg_token = secrets.get("TELEGRAM_BOT_TOKEN", "")
    tg_chat = cfg.get("telegram", {}).get("chat_id", "")
    if tg_token:
        checks["telegram"] = {
            "ok": bool(tg_chat),
            "detail": "Verbunden" if tg_chat else "Token da, keine Chat-ID",
        }
    else:
        checks["telegram"] = {"ok": None, "detail": "Nicht konfiguriert"}
    try:
        import sqlite3

        conn = sqlite3.connect(str(INDEX_DB))
        count = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        conn.close()
        checks["database"] = {"ok": True, "detail": f"{count} Emails indiziert"}
    except Exception as e:
        checks["database"] = {"ok": False, "detail": str(e)[:80]}
        overall = "degraded"
    daemon_state = sorter_service.load_state()
    checks["daemon"] = {
        "ok": daemon_state.get("running", False),
        "detail": f"Runs: {daemon_state.get('total_runs', 0)}, Last: {daemon_state.get('last_run_status', 'none')}",
    }
    try:
        import sqlite3

        if MEMORY_DB.exists():
            c = sqlite3.connect(str(MEMORY_DB))
            convos = c.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            c.close()
            checks["llm_memory"] = {
                "ok": True,
                "detail": f"{convos} Nachrichten gespeichert",
            }
        else:
            checks["llm_memory"] = {"ok": None, "detail": "Noch keine Daten"}
    except Exception:
        checks["llm_memory"] = {"ok": None, "detail": "DB nicht initialisiert"}
    _health_state["last_check"] = datetime.now().isoformat()
    _health_state["checks"] = checks
    _health_state["status"] = overall
    return _health_state
