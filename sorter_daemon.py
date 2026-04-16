#!/usr/bin/env python3
"""
Mail AI Sorter Daemon — runs sorting on a schedule.
Controlled via state.json (created by web UI).
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "mail_sorter.log"
PID_FILE = BASE_DIR / "sorter_daemon.pid"
CONFIG_FILE = BASE_DIR / "config.json"

DEFAULT_STATE = {
    "running": False,
    "paused": False,
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "poll_interval_minutes": 5,
    "last_run": None,
    "last_run_status": None,
    "total_runs": 0,
    "pid": None,
}


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            for k, v in DEFAULT_STATE.items():
                state.setdefault(k, v)
            return state
    except Exception:
        return dict(DEFAULT_STATE)


def save_state(state):
    tmp = str(STATE_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(STATE_FILE))


def is_quiet_hours(state):
    if not state.get("quiet_hours_enabled"):
        return False
    start = state.get("quiet_hours_start", "22:00")
    end = state.get("quiet_hours_end", "07:00")
    now = datetime.now().strftime("%H:%M")
    if start <= end:
        return start <= now < end
    else:
        return now >= start or now < end


def run_sorter(state):
    cmd = [
        sys.executable,
        str(BASE_DIR / "sorter.py"),
        "--config",
        str(BASE_DIR / "config.json"),
        "--max-per-account",
        "50",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600, cwd=str(BASE_DIR)
        )
        state["last_run"] = datetime.now().isoformat()
        state["last_run_status"] = "success" if result.returncode == 0 else "error"
        state["total_runs"] = state.get("total_runs", 0) + 1

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(
                f"Run {state['total_runs']} at {state['last_run']} — {state['last_run_status']}\n"
            )
            f.write(f"{'=' * 60}\n")
            if result.stdout:
                f.write(result.stdout)
            if result.stderr:
                f.write(f"\nSTDERR:\n{result.stderr}\n")

        if state["last_run_status"] == "success":
            _send_digest_if_due(state)

    except subprocess.TimeoutExpired:
        state["last_run"] = datetime.now().isoformat()
        state["last_run_status"] = "timeout"
    except Exception as e:
        state["last_run"] = datetime.now().isoformat()
        state["last_run_status"] = f"error: {e}"

    save_state(state)


def _send_digest_if_due(state):
    try:
        import json as _json

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = _json.load(f)
        tg = cfg.get("telegram", {})
        mode = tg.get("notify_mode", "off")
        if mode == "off" or not tg.get("chat_id") or not tg.get("bot_token"):
            return

        last_digest = state.get("last_digest_sent", "")
        now_str = datetime.now().strftime("%Y-%m-%d")
        if last_digest == now_str:
            return

        sys.path.insert(0, str(BASE_DIR))
        from llm_helper import LLMHelper

        ollama_url = cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434")
        model = cfg.get("global", {}).get("model", "llama3.1:8b")
        llm = LLMHelper(ollama_url=ollama_url, model=model)

        rows = llm.db.execute(
            "SELECT subject, from_addr, category, importance, summary FROM email_summaries WHERE created_at >= date('now', '-1 day') ORDER BY created_at DESC LIMIT 30"
        ).fetchall()

        if not rows:
            return

        emails = [
            {
                "subject": r[0],
                "from_addr": r[1],
                "category": r[2],
                "importance": r[3],
                "summary": r[4],
            }
            for r in rows
        ]
        digest = llm.smart_digest(emails)
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
        for _ in range(interval):
            s = load_state()
            if not s.get("running") or s.get("paused"):
                break
            time.sleep(1)

    state = load_state()
    state["running"] = False
    state["pid"] = None
    save_state(state)
    if PID_FILE.exists():
        PID_FILE.unlink()


if __name__ == "__main__":
    main()
