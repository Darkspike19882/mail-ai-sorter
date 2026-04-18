from fastapi import APIRouter

from config_service import load_config, load_secrets, save_config, save_secrets

router = APIRouter(tags=["config"])


@router.get("/api/config")
async def api_config():
    cfg = load_config()
    secrets = load_secrets()
    return {"config": cfg, "secrets": {"telegram_configured": bool(secrets.get("TELEGRAM_BOT_TOKEN"))}, "accounts": cfg.get("accounts", []), "global": cfg.get("global", {}), "telegram": cfg.get("telegram", {}), "extensions": cfg.get("extensions", {})}


@router.get("/api/rule-templates")
async def api_rule_templates():
    return {
        "templates": [
            {"name": "Newsletter", "if_from_contains": ["newsletter", "noreply", "no-reply"], "move_to": "newsletter"},
            {"name": "Rechnungen", "if_from_contains": ["rechnung", "invoice", "billing"], "move_to": "finanzen"},
            {"name": "Social Media", "if_from_contains": ["facebook", "instagram", "linkedin", "twitter"], "move_to": "newsletter"},
            {"name": "Einkaufen", "if_from_contains": ["amazon", "ebay", "shop"], "move_to": "einkauf"},
        ]
    }
