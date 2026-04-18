"""Data portability and deletion endpoints for DSGVO compliance (LOCL-03)."""

import io
import json
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from config_service import load_config, BASE_DIR, SERVICE_NAME

router = APIRouter(prefix="/api/data", tags=["data"])

INDEX_DB = BASE_DIR / "mail_index.db"
MEMORY_DB = BASE_DIR / "llm_memory.db"
CONFIG_FILE = BASE_DIR / "config.json"
PRIVACY_FILE = BASE_DIR / "PRIVACY.md"


def _dump_sqlite_to_zip(zf: zipfile.ZipFile, db_path: Path, arcname: str):
    """Dump SQLite database as SQL text into the ZIP."""
    conn = sqlite3.connect(str(db_path))
    lines = list(conn.iterdump())
    conn.close()
    zf.writestr(arcname, "\n".join(lines))


def _strip_passwords(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Remove password fields from config for safe export."""
    safe = json.loads(json.dumps(cfg))
    for account in safe.get("accounts", []):
        account.pop("password", None)
        account.pop("password_env", None)
    tg = safe.get("telegram", {})
    tg.pop("bot_token", None)
    return safe


@router.get("/export")
async def export_user_data():
    """Export all user data as ZIP (DSGVO Art. 15, Art. 20)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. SQLite dump — mail_index.db
        if INDEX_DB.exists():
            _dump_sqlite_to_zip(zf, INDEX_DB, "mail_index_dump.sql")

        # 2. SQLite dump — llm_memory.db
        if MEMORY_DB.exists():
            _dump_sqlite_to_zip(zf, MEMORY_DB, "llm_memory_dump.sql")

        # 3. Config (without passwords)
        cfg = load_config()
        safe_cfg = _strip_passwords(cfg)
        zf.writestr("config.json", json.dumps(safe_cfg, indent=2, ensure_ascii=False))

        # 4. Privacy documentation
        if PRIVACY_FILE.exists():
            zf.write(str(PRIVACY_FILE), "PRIVACY.md")

        # 5. Export metadata
        zf.writestr("export_info.json", json.dumps({
            "app": "Superhero Mail",
            "export_date": datetime.now().isoformat(),
            "databases_included": [
                "mail_index_dump.sql" if INDEX_DB.exists() else None,
                "llm_memory_dump.sql" if MEMORY_DB.exists() else None,
            ],
            "note": "Passwörter sind nicht im Export enthalten (nur im OS-Schlüsselbund).",
        }, indent=2))

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=superhero-mail-export.zip"},
    )


@router.delete("/delete")
async def delete_user_data():
    """Delete all user data (DSGVO Art. 17). IRREVERSIBLE."""
    results = {}

    # 1. Clear mail_index.db tables
    if INDEX_DB.exists():
        conn = sqlite3.connect(str(INDEX_DB))
        try:
            conn.execute("DELETE FROM emails")
            conn.commit()
            results["mail_index_cleared"] = True
        except sqlite3.OperationalError:
            results["mail_index_cleared"] = False
        finally:
            conn.close()

    # 2. Clear llm_memory.db tables
    if MEMORY_DB.exists():
        conn = sqlite3.connect(str(MEMORY_DB))
        for table in ["conversations", "email_summaries", "user_facts", "sort_actions", "rag_queries", "email_embeddings", "email_tags", "reply_templates"]:
            try:
                conn.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                pass  # table may not exist
        conn.commit()
        conn.close()
        results["llm_memory_cleared"] = True

    # 3. Remove keyring entries for all accounts
    try:
        import keyring
        cfg = load_config()
        for account in cfg.get("accounts", []):
            env_key = account.get("password_env", "")
            if env_key:
                try:
                    keyring.delete_password(SERVICE_NAME, env_key.lower())
                except keyring.errors.PasswordDeleteError:
                    pass
        # Also clear Telegram token from keyring if present
        try:
            keyring.delete_password(SERVICE_NAME, "telegram_bot_token")
        except keyring.errors.PasswordDeleteError:
            pass
        results["keyring_cleared"] = True
    except Exception as e:
        results["keyring_cleared"] = f"Error: {str(e)[:100]}"

    return {
        "success": True,
        "message": "Alle Nutzerdaten wurden gelöscht. Dies ist irreversibel.",
        "details": results,
    }
