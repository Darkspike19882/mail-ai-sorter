#!/usr/bin/env python3
"""
Sorter state and process control helpers.
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "mail_sorter.log"

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


def load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            for key, value in DEFAULT_STATE.items():
                state.setdefault(key, value)
            return state
    except Exception:
        return dict(DEFAULT_STATE)


def save_state(state: Dict[str, Any]) -> None:
    tmp = str(STATE_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(STATE_FILE))


def is_quiet_hours(state: Dict[str, Any]) -> bool:
    if not state.get("quiet_hours_enabled"):
        return False
    start = state.get("quiet_hours_start", "22:00")
    end = state.get("quiet_hours_end", "07:00")
    now = datetime.now().strftime("%H:%M")
    if start <= end:
        return start <= now < end
    return now >= start or now < end


def daemon_running() -> bool:
    state = load_state()
    pid = state.get("pid")
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, TypeError):
        state["running"] = False
        state["pid"] = None
        save_state(state)
        return False


def start_daemon() -> Dict[str, Any]:
    state = load_state()
    if daemon_running():
        state["running"] = True
        state["paused"] = False
        save_state(state)
        return {"success": True, "message": "Daemon läuft bereits, Pause aufgehoben"}

    save_state({**state, "running": True, "paused": False})
    daemon_script = str(BASE_DIR / "sorter_daemon.py")
    try:
        subprocess.Popen(
            [sys.executable, daemon_script],
            cwd=str(BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        time.sleep(1)
        if daemon_running():
            return {"success": True, "message": "Sortier-Daemon gestartet"}
        return {"success": False, "error": "Daemon konnte nicht gestartet werden"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def pause_daemon() -> Dict[str, Any]:
    state = load_state()
    state["paused"] = True
    save_state(state)
    return {"success": True, "message": "Sortierung pausiert"}


def resume_daemon() -> Dict[str, Any]:
    state = load_state()
    state["paused"] = False
    save_state(state)
    return {"success": True, "message": "Sortierung fortgesetzt"}


def stop_daemon() -> Dict[str, Any]:
    state = load_state()
    pid = state.get("pid")
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        except (ProcessLookupError, PermissionError):
            pass
    state["running"] = False
    state["paused"] = False
    state["pid"] = None
    save_state(state)
    return {"success": True, "message": "Sortier-Daemon gestoppt"}


def update_quiet_hours(data: Dict[str, Any]) -> Dict[str, Any]:
    state = load_state()
    state["quiet_hours_enabled"] = data.get("enabled", False)
    if "start" in data:
        state["quiet_hours_start"] = data["start"]
    if "end" in data:
        state["quiet_hours_end"] = data["end"]
    if "poll_interval" in data:
        state["poll_interval_minutes"] = max(1, int(data["poll_interval"]))
    save_state(state)
    return {"success": True, "state": state}


def get_status() -> Dict[str, Any]:
    state = load_state()
    state["daemon_alive"] = daemon_running()
    state["quiet_active"] = is_quiet_hours(state)
    return state


def run_sorter_once(dry_run: bool = False, max_mails: int = 10) -> Dict[str, Any]:
    try:
        cmd = ["./run.sh", "--max-per-account", str(max_mails)]
        if dry_run:
            cmd.append("--dry-run")
        result = subprocess.run(
            cmd, cwd=BASE_DIR, capture_output=True, text=True, timeout=300
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
        }
    except Exception as e:
        return {"success": False, "errors": str(e)}


def get_logs(limit: int = 50) -> List[str]:
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return f.readlines()[-limit:]
        return []
    except Exception:
        return []


def clear_logs() -> Dict[str, Any]:
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_scheduled_sorter(state: Dict[str, Any]) -> Dict[str, Any]:
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
    except subprocess.TimeoutExpired:
        state["last_run"] = datetime.now().isoformat()
        state["last_run_status"] = "timeout"
    except Exception as e:
        state["last_run"] = datetime.now().isoformat()
        state["last_run_status"] = f"error: {e}"

    save_state(state)
    return state
