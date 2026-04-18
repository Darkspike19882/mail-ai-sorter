#!/usr/bin/env python3
"""
Shared config and secrets helpers for Mail AI Sorter.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import keyring

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
SECRETS_FILE = BASE_DIR / "secrets.env"

SERVICE_NAME = "com.superhero-mail"


def store_account_password(account_name: str, password: str) -> None:
    """Store password in OS keychain via keyring."""
    keyring.set_password(SERVICE_NAME, account_name.lower(), password)


def get_account_password(account_name: str) -> str:
    """Retrieve password from OS keychain via keyring."""
    return keyring.get_password(SERVICE_NAME, account_name.lower()) or ""


def check_keyring_backend() -> str:
    """Check the active keyring backend and warn if insecure."""
    backend_name = keyring.get_keyring().name
    if "plaintext" in backend_name.lower() or "fail" in backend_name.lower():
        logger.warning(
            f"Insecure keyring backend detected: '{backend_name}'. "
            "Passwords may be stored in plaintext. Consider installing "
            "a Secret Service provider (e.g., gnome-keyring)."
        )
    return backend_name


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
                        key = key.strip()
                        val = val.strip()

                        # Entferne 'export' am Anfang wenn vorhanden
                        if key.startswith("export "):
                            key = key[7:].strip()

                        # Entferne Anführungszeichen wenn sie am Anfang und Ende stehen
                        if len(val) >= 2 and val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        elif len(val) >= 2 and val.startswith("'") and val.endswith("'"):
                            val = val[1:-1]

                        secrets[key] = val
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
                keyring.set_password(SERVICE_NAME, env_key.lower(), password)

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
        # Priority: 1) OS keyring, 2) env var, 3) secrets.env file
        password = keyring.get_password(SERVICE_NAME, env_key.lower()) or ""
        if not password:
            password = os.getenv(env_key, "")
        if not password:
            secrets = load_secrets()
            password = secrets.get(env_key, "")
        resolved["password"] = password
    return resolved


def get_account(
    account_name: str, config: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    cfg = config or load_config()
    for account in cfg.get("accounts", []):
        if account.get("name") == account_name:
            return inject_account_secret(account)
    return None


def migrate_from_secrets_env() -> dict:
    """One-time migration: read secrets.env passwords, store in OS keyring, clear plaintext."""
    secrets = load_secrets()
    migrated = {}
    remaining = {}
    for key, value in secrets.items():
        if "_PASSWORD" in key and value:
            account_name = key.replace("_PASSWORD", "").lower()
            keyring.set_password(SERVICE_NAME, account_name, value)
            # Verify write-back
            stored = keyring.get_password(SERVICE_NAME, account_name)
            if stored == value:
                migrated[key] = account_name
                remaining[key] = ""  # Clear plaintext
            else:
                remaining[key] = value  # Keep if migration failed
        else:
            remaining[key] = value  # Keep non-password secrets (e.g., TELEGRAM_BOT_TOKEN)
    if migrated:
        save_secrets(remaining)
        logger.info(f"Migrated {len(migrated)} passwords to OS keychain: {list(migrated.keys())}")
    return migrated
