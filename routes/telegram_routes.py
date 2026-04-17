import json
from datetime import datetime

from flask import Blueprint, jsonify, request

from config_service import load_config, load_secrets, save_config, save_secrets


telegram_bp = Blueprint("telegram_routes", __name__)


@telegram_bp.route("/api/telegram/config", methods=["GET", "POST"])
def api_telegram_config():
    cfg = load_config()
    if request.method == "POST":
        data = request.json or {}
        if "telegram" not in cfg:
            cfg["telegram"] = {}
        if "bot_token" in data:
            secrets = load_secrets()
            secrets["TELEGRAM_BOT_TOKEN"] = data["bot_token"]
            save_secrets(secrets)
        if "chat_id" in data:
            cfg["telegram"]["chat_id"] = data["chat_id"]
        if "notify_mode" in data:
            cfg["telegram"]["notify_mode"] = data["notify_mode"]
        if "notify_categories" in data:
            cfg["telegram"]["notify_categories"] = data["notify_categories"]
        save_config(cfg)
        return jsonify({"success": True})
    secrets = load_secrets()
    result = dict(cfg.get("telegram", {}))
    result["bot_token"] = secrets.get("TELEGRAM_BOT_TOKEN", "")
    return jsonify(result)


@telegram_bp.route("/api/telegram/generate-code", methods=["POST"])
def api_telegram_generate_code():
    import random
    from telegram_bot import start_verification_poller

    code = str(random.randint(100000, 999999))
    cfg = load_config()
    if "telegram" not in cfg:
        cfg["telegram"] = {}
    cfg["telegram"]["verify_code"] = code
    cfg["telegram"]["verify_code_created"] = datetime.now().isoformat()
    cfg["telegram"].pop("chat_id", None)
    save_config(cfg)
    start_verification_poller()
    return jsonify({"success": True, "code": code})


@telegram_bp.route("/api/telegram/verify", methods=["POST"])
def api_telegram_verify():
    data = request.json or {}
    user_code = str(data.get("code", ""))
    cfg = load_config()
    stored_code = cfg.get("telegram", {}).get("verify_code", "")
    if not stored_code or user_code != stored_code:
        return jsonify({"success": False, "error": "Falscher Code"})
    chat_id = cfg.get("telegram", {}).get("pending_chat_id")
    if not chat_id:
        return jsonify(
            {
                "success": False,
                "error": "Noch keine Chat-ID empfangen. Sende /start an den Bot.",
            }
        )
    cfg["telegram"]["chat_id"] = chat_id
    cfg["telegram"].pop("verify_code", None)
    cfg["telegram"].pop("pending_chat_id", None)
    cfg["telegram"].pop("verify_code_created", None)
    save_config(cfg)
    try:
        import urllib.request

        secrets = load_secrets()
        token = secrets.get("TELEGRAM_BOT_TOKEN", "")
        msg = "✅ Verifizierung erfolgreich! Du erhältst jetzt Benachrichtigungen für wichtige Emails."
        payload = json.dumps({"chat_id": chat_id, "text": msg}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
    return jsonify({"success": True, "chat_id": chat_id})


@telegram_bp.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    secrets = load_secrets()
    token = secrets.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return jsonify({"success": False, "error": "Kein Bot-Token konfiguriert"})
    try:
        import urllib.request

        r = urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getMe", timeout=10
        )
        data = json.loads(r.read().decode())
        if data.get("ok"):
            bot_info = data.get("result", {})
            return jsonify(
                {
                    "success": True,
                    "bot_name": bot_info.get("first_name", ""),
                    "bot_username": bot_info.get("username", ""),
                }
            )
        return jsonify({"success": False, "error": "Ungültiger Token"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@telegram_bp.route("/api/telegram/send-test", methods=["POST"])
def api_telegram_send_test():
    cfg = load_config()
    secrets = load_secrets()
    token = secrets.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = cfg.get("telegram", {}).get("chat_id", "")
    if not token or not chat_id:
        return jsonify({"success": False, "error": "Bot-Token oder Chat-ID fehlt"})
    try:
        import urllib.request

        post_data = request.json or {}
        msg = post_data.get(
            "message",
            "🔔 Test-Benachrichtigung vom Mail AI Sorter!\n\nAlles funktioniert korrekt.",
        )
        payload = json.dumps(
            {"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}
        ).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
