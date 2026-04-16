#!/usr/bin/env python3
"""
Background Health Monitor for Mail AI Sorter.
Runs periodic health checks and logs issues.
Sends Telegram alerts on critical failures.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
HEALTH_LOG = BASE_DIR / "health.log"
CONFIG_FILE = BASE_DIR / "secrets.env"
INTERVAL = 60


def _load_secrets():
    secrets = {}
    try:
        sf = BASE_DIR / "secrets.env"
        if sf.exists():
            for line in sf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    secrets[k.strip()] = v.strip()
    except Exception:
        pass
    return secrets


def _tg_send(token, chat_id, text):
    try:
        payload = json.dumps(
            {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        ).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}\n"
    with open(HEALTH_LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(line.rstrip())


def check_health():
    try:
        r = urllib.request.urlopen("http://127.0.0.1:5001/api/health", timeout=15)
        return json.loads(r.read().decode())
    except Exception as e:
        return {"status": "down", "error": str(e)}


def run_monitor():
    _log("=" * 50)
    _log("Health Monitor gestartet")
    _log(f"Intervall: {INTERVAL}s")
    _log("=" * 50)

    last_alert = {}
    alert_cooldown = 300
    consecutive_failures = 0

    while True:
        try:
            health = check_health()
            status = health.get("status", "unknown")
            checks = health.get("checks", {})
            ts = datetime.now().strftime("%H:%M:%S")

            if status == "down":
                consecutive_failures += 1
                _log(
                    f"SERVER DOWN (x{consecutive_failures}): {health.get('error', 'unknown')}",
                    "CRITICAL",
                )
                if consecutive_failures >= 3:
                    secrets = _load_secrets()
                    token = secrets.get("TELEGRAM_BOT_TOKEN", "")
                    cfg_path = BASE_DIR / "config.json"
                    chat_id = ""
                    try:
                        with open(cfg_path) as f:
                            chat_id = (
                                json.load(f).get("telegram", {}).get("chat_id", "")
                            )
                    except Exception:
                        pass
                    if token and chat_id:
                        key = "server_down"
                        if (
                            not last_alert.get(key)
                            or (time.time() - last_alert.get(key, 0)) > alert_cooldown
                        ):
                            _tg_send(
                                token,
                                chat_id,
                                f"🚨 <b>Mail AI Sorter DOWN</b>\n\n"
                                f"Server reagiert nicht!\n"
                                f"Fehler: {health.get('error', 'unknown')[:100]}\n"
                                f"Zeit: {datetime.now().strftime('%H:%M:%S')}",
                            )
                            last_alert[key] = time.time()
            else:
                if consecutive_failures > 0:
                    _log(
                        f"Server wieder erreichbar (war {consecutive_failures}x down)",
                        "RECOVERY",
                    )
                    consecutive_failures = 0

                failures = []
                for name, check in checks.items():
                    if check.get("ok") is False:
                        failures.append(f"{name}: {check.get('detail', '')}")

                if failures:
                    _log(f"[{ts}] DEGRADED — {', '.join(failures)}", "WARN")
                else:
                    ok_count = sum(1 for c in checks.values() if c.get("ok") is True)
                    total_req = health.get("total_requests", 0)
                    errors = health.get("errors_last_hour", 0)
                    _log(
                        f"[{ts}] OK — {ok_count}/{len(checks)} checks | Requests: {total_req} | Errors: {errors}"
                    )

                    if errors > 10:
                        secrets = _load_secrets()
                        token = secrets.get("TELEGRAM_BOT_TOKEN", "")
                        cfg_path = BASE_DIR / "config.json"
                        chat_id = ""
                        try:
                            with open(cfg_path) as f:
                                chat_id = (
                                    json.load(f).get("telegram", {}).get("chat_id", "")
                                )
                        except Exception:
                            pass
                        if token and chat_id:
                            key = "high_errors"
                            if (
                                not last_alert.get(key)
                                or (time.time() - last_alert.get(key, 0))
                                > alert_cooldown
                            ):
                                _tg_send(
                                    token,
                                    chat_id,
                                    f"⚠️ <b>Hohe Fehlerrate</b>\n\n{errors} Fehler in letzter Stunde\nLetzter: {health.get('last_error', {})}",
                                )
                                last_alert[key] = time.time()

        except Exception as e:
            _log(f"Monitor error: {e}", "ERROR")

        time.sleep(INTERVAL)


if __name__ == "__main__":
    run_monitor()
