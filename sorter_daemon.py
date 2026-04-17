#!/usr/bin/env python3
"""
Mail AI Sorter Daemon — runs sorting on a schedule.
Controlled via state.json (created by web UI).
"""

import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from config_service import load_config, load_secrets
from services import llm_service, sorter_service

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "mail_sorter.log"
PID_FILE = BASE_DIR / "sorter_daemon.pid"
CONFIG_FILE = BASE_DIR / "config.json"


def load_state():
    return sorter_service.load_state()


def save_state(state):
    sorter_service.save_state(state)


def is_quiet_hours(state):
    return sorter_service.is_quiet_hours(state)


def run_sorter(state):
    state = sorter_service.run_scheduled_sorter(state)
    if state.get("last_run_status") == "success":
        _send_digest_if_due(state)
    save_state(state)


def _send_digest_if_due(state):
    try:
        cfg = load_config()
        tg = cfg.get("telegram", {})
        mode = tg.get("notify_mode", "off")
        secrets = load_secrets()
        token = secrets.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = tg.get("chat_id", "")
        if mode == "off" or not chat_id or not token:
            return

        last_digest = state.get("last_digest_sent", "")
        now_str = datetime.now().strftime("%Y-%m-%d")
        if last_digest == now_str:
            return

        digest_result = llm_service.build_digest(days=1, limit=30)
        if not digest_result.get("success") or not digest_result.get("count"):
            return

        digest = digest_result.get("digest")
        if digest:
            from telegram_bot import send_daily_digest

            if send_daily_digest(digest):
                state["last_digest_sent"] = now_str
                save_state(state)
    except Exception as e:
        print(f"[Daemon] Digest error: {e}")


def main():
    state = load_state()
    state["running"] = True
    state["pid"] = os.getpid()
    save_state(state)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def shutdown(signum, frame):
        state = load_state()
        state["running"] = False
        state["pid"] = None
        save_state(state)
        if PID_FILE.exists():
            PID_FILE.unlink()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print(f"Mail Sorter Daemon gestartet (PID {os.getpid()})")
    print(f"Poll-Interval: {state.get('poll_interval_minutes', 5)} Minuten")
    print(
        f"Ruhezeiten: {state.get('quiet_hours_start', '22:00')} - {state.get('quiet_hours_end', '07:00')}"
    )

    while True:
        state = load_state()

        if not state.get("running"):
            print("Daemon gestoppt via state.json")
            break

        if state.get("paused"):
            time.sleep(10)
            continue

        if is_quiet_hours(state):
            time.sleep(30)
            continue

        run_sorter(state)

        interval = state.get("poll_interval_minutes", 5) * 60
        for _ in range(interval // 5):
            s = load_state()
            if not s.get("running") or s.get("paused"):
                break
            time.sleep(5)

    state = load_state()
    state["running"] = False
    state["pid"] = None
    save_state(state)
    if PID_FILE.exists():
        PID_FILE.unlink()


if __name__ == "__main__":
    main()
