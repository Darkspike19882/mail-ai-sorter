#!/usr/bin/env python3
"""
Telegram Bot for Mail AI Sorter.
Lightweight bot using direct HTTP API calls (no extra dependencies).
"""

import json
import os
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"

_poller_thread: Optional[threading.Thread] = None
_poller_running = False


def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg):
    tmp = str(CONFIG_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(CONFIG_FILE))


def _tg_api(token: str, method: str, payload: Optional[dict] = None) -> Optional[dict]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        data = json.dumps(payload).encode() if payload else None
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[Telegram] API error ({method}): {e}")
        return None


def validate_token(token: str) -> dict:
    result = _tg_api(token, "getMe")
    if result and result.get("ok"):
        info = result.get("result", {})
        return {
            "valid": True,
            "name": info.get("first_name", ""),
            "username": info.get("username", ""),
        }
    return {"valid": False, "error": "Ungültiger Token"}


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    result = _tg_api(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        },
    )
    return result is not None and result.get("ok", False)


def send_email_notification(
    subject: str, from_addr: str, summary: str, importance: str, category: str
):
    cfg = _load_config()
    tg = cfg.get("telegram", {})
    token = tg.get("bot_token", "")
    chat_id = tg.get("chat_id", "")
    if not token or not chat_id:
        return False

    importance_emoji = {"hoch": "🔴", "mittel": "🟡", "niedrig": "🟢"}.get(
        importance, "⚪"
    )

    text = (
        f"{importance_emoji} <b>Neue wichtige Email</b>\n\n"
        f"📧 <b>{_escape(subject or '(Kein Betreff)')}</b>\n"
        f"👤 Von: {_escape(from_addr)}\n"
        f"📁 Kategorie: {_escape(category)}\n"
        f"⭐ Wichtigkeit: {importance}\n\n"
        f"📝 {_escape(summary or 'Keine Zusammenfassung verfügbar')}\n\n"
        f"<i>Mail AI Sorter</i>"
    )
    return send_message(token, chat_id, text)


def send_daily_digest(digest_text: str):
    cfg = _load_config()
    tg = cfg.get("telegram", {})
    token = tg.get("bot_token", "")
    chat_id = tg.get("chat_id", "")
    if not token or not chat_id:
        return False

    text = f"📊 <b>Täglicher Email-Bericht</b>\n\n{_escape(digest_text)}\n\n<i>Mail AI Sorter</i>"
    return send_message(token, chat_id, text)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _verification_poller():
    global _poller_running
    cfg = _load_config()
    token = cfg.get("telegram", {}).get("bot_token", "")
    if not token:
        return

    _poller_running = True
    last_update_id = 0

    while _poller_running:
        cfg = _load_config()
        stored_code = cfg.get("telegram", {}).get("verify_code", "")
        if not stored_code:
            _poller_running = False
            break

        result = _tg_api(
            token,
            "getUpdates",
            {
                "offset": last_update_id + 1,
                "timeout": 10,
                "limit": 5,
            },
        )

        if result and result.get("ok"):
            for update in result.get("result", []):
                last_update_id = update.get("update_id", last_update_id)
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                text = message.get("text", "")

                if text == "/start":
                    cfg = _load_config()
                    cfg.setdefault("telegram", {})["pending_chat_id"] = str(chat_id)
                    _save_config(cfg)
                    send_message(
                        token,
                        str(chat_id),
                        "👋 Willkommen beim Mail AI Sorter Bot!\n\n"
                        "Gib den Bestätigungscode aus der Web-Oberfläche ein, um die Verbindung herzustellen.\n\n"
                        f"Dein Code lautet: <code>{stored_code}</code>\n\n"
                        "Oder gib den Code einfach in der Web-Oberfläche ein.",
                    )
                elif text.strip() == stored_code:
                    cfg = _load_config()
                    cfg.setdefault("telegram", {})["chat_id"] = str(chat_id)
                    cfg["telegram"].pop("verify_code", None)
                    cfg["telegram"].pop("pending_chat_id", None)
                    _save_config(cfg)
                    send_message(
                        token,
                        str(chat_id),
                        "✅ Verifizierung erfolgreich!\n\nDu erhältst jetzt Benachrichtigungen für wichtige Emails.",
                    )
                    _poller_running = False
                    return

        time.sleep(2)

    _poller_running = False


def start_verification_poller():
    global _poller_thread, _poller_running
    if _poller_running and _poller_thread and _poller_thread.is_alive():
        return
    _poller_thread = threading.Thread(target=_verification_poller, daemon=True)
    _poller_thread.start()


def notify_if_important(
    subject: str, from_addr: str, category: str, importance: str, summary: str = ""
):
    cfg = _load_config()
    tg = cfg.get("telegram", {})
    mode = tg.get("notify_mode", "off")
    if mode == "off":
        return
    if mode == "important" and importance not in ("hoch",):
        return

    notify_cats = tg.get("notify_categories", [])
    if notify_cats and category.lower() not in [c.lower() for c in notify_cats]:
        return

    send_email_notification(subject, from_addr, summary, importance, category)
