#!/usr/bin/env python3
"""
Shared config and secrets helpers for Mail AI Sorter.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
SECRETS_FILE = BASE_DIR / "secrets.env"


def load_config() -> Dict[str, Any]:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def load_secrets() -> Dict[str, str]:
    secrets: Dict[str, str] = {}
    try:
        if SECRETS_FILE.exists():
            with open(SECRETS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        secrets[key.strip()] = val.strip()
    except Exception:
        pass
    return secrets


def save_secrets(secrets: Dict[str, str]) -> None:
    lines = ["# Mail AI Sorter - Secrets\n"]
    for key, value in secrets.items():
        lines.append(f"{key}={value}\n")
    with open(SECRETS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


def save_config(config: Dict[str, Any]) -> bool:
    try:
        secrets = load_secrets()
        config_copy = json.loads(json.dumps(config))

        telegram = config_copy.get("telegram", {})
        if telegram.get("bot_token"):
            secrets["TELEGRAM_BOT_TOKEN"] = telegram.pop("bot_token")

        for account in config_copy.get("accounts", []):
            password = account.pop("password", None)
            env_key = account.get("password_env", "")
            if password and not env_key:
                env_key = account["name"].upper().replace(" ", "_") + "_PASSWORD"
                account["password_env"] = env_key
            if password and env_key:
                secrets[env_key] = password

        save_secrets(secrets)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_copy, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def inject_account_secret(account: Dict[str, Any]) -> Dict[str, Any]:
    resolved = dict(account)
    env_key = resolved.get("password_env", "")
    if env_key and not resolved.get("password"):
        secrets = load_secrets()
        resolved["password"] = secrets.get(env_key, os.getenv(env_key, ""))
    return resolved


def get_account(
    account_name: str, config: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    cfg = config or load_config()
    for account in cfg.get("accounts", []):
        if account.get("name") == account_name:
            return inject_account_secret(account)
    return None
