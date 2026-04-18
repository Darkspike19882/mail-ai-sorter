from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from config_service import load_config, load_secrets, save_secrets

router = APIRouter(tags=["telegram"])


@router.get("/api/telegram/config")
async def api_telegram_config():
    cfg = load_config()
    secrets = load_secrets()
    return {
        "enabled": cfg.get("telegram", {}).get("enabled", False),
        "chat_id": cfg.get("telegram", {}).get("chat_id", ""),
        "mode": cfg.get("telegram", {}).get("mode", "off"),
        "bot_token_set": bool(secrets.get("TELEGRAM_BOT_TOKEN")),
    }


@router.post("/api/telegram/generate-code")
async def api_telegram_generate_code():
    import secrets as sec
    code = sec.token_hex(4).upper()
    return {"success": True, "code": code}


@router.post("/api/telegram/verify")
async def api_telegram_verify():
    return {"success": False, "error": "Not migrated yet"}


@router.post("/api/telegram/test")
async def api_telegram_test():
    return {"success": False, "error": "Not migrated yet"}


@router.post("/api/telegram/send-test")
async def api_telegram_send_test():
    return {"success": False, "error": "Not migrated yet"}
