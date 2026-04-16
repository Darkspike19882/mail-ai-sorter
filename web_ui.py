#!/usr/bin/env python3
"""
Mail AI Sorter - Web UI
Einfache Web-Oberfläche für den AI Email Sorter
"""

import os
import json
import signal
import subprocess
import sys
import threading
import time
import base64
import concurrent.futures
import email as email_lib
import email.header
import email.utils
import imaplib
import re
import ssl
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from pathlib import Path

app = Flask(__name__)
SORTER_DIR = Path(__file__).parent
CONFIG_FILE = SORTER_DIR / "config.json"
SECRETS_FILE = SORTER_DIR / "secrets.env"
INDEX_DB = SORTER_DIR / "mail_index.db"

# ─── Helper Functions ─────────────────────────────────────────────────────


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def _load_secrets():
    secrets = {}
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


def _save_secrets(secrets: dict):
    lines = ["# Mail AI Sorter - Secrets\n"]
    for k, v in secrets.items():
        lines.append(f"{k}={v}\n")
    with open(SECRETS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)


def save_config(config):
    try:
        secrets = _load_secrets()
        tg = config.get("telegram", {})
        if tg.get("bot_token"):
            secrets["TELEGRAM_BOT_TOKEN"] = tg.pop("bot_token")
        for acc in config.get("accounts", []):
            pw = acc.pop("password", None)
            env_key = acc.get("password_env", "")
            if pw and not env_key:
                env_key = acc["name"].upper().replace(" ", "_") + "_PASSWORD"
                acc["password_env"] = env_key
            if pw and env_key:
                secrets[env_key] = pw
        _save_secrets(secrets)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        return False


def get_stats():
    """Holt Statistiken vom Index"""
    try:
        import sqlite3

        conn = sqlite3.connect(INDEX_DB)
        cursor = conn.cursor()

        total = cursor.execute("SELECT COUNT(*) FROM emails").fetchone()[0]

        categories = cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM emails
            GROUP BY category
            ORDER BY count DESC
        """).fetchall()

        accounts = cursor.execute("""
            SELECT account, COUNT(*) as count
            FROM emails
            GROUP BY account
            ORDER BY count DESC
        """).fetchall()

        conn.close()

        return {
            "total": total,
            "categories": dict(categories),
            "accounts": dict(accounts),
        }
    except Exception as e:
        return {"error": str(e)}


def get_detailed_stats(days="30"):
    try:
        import sqlite3

        conn = sqlite3.connect(INDEX_DB)
        cursor = conn.cursor()

        where_date = ""
        if days and days != "all":
            try:
                d = int(days)
                where_date = f" AND date_iso >= date('now', '-{d} days')"
            except ValueError:
                pass

        total = cursor.execute("SELECT COUNT(*) FROM emails").fetchone()[0]

        categories = cursor.execute(f"""
            SELECT category, COUNT(*) as count
            FROM emails
            WHERE 1=1{where_date}
            GROUP BY category
            ORDER BY count DESC
        """).fetchall()

        accounts = cursor.execute(f"""
            SELECT account, COUNT(*) as count
            FROM emails
            WHERE 1=1{where_date}
            GROUP BY account
            ORDER BY count DESC
        """).fetchall()

        top_senders = cursor.execute(f"""
            SELECT from_addr, COUNT(*) as count
            FROM emails
            WHERE 1=1{where_date}
            GROUP BY from_addr
            ORDER BY count DESC
            LIMIT 20
        """).fetchall()

        daily_volume = cursor.execute(f"""
            SELECT SUBSTR(date_iso, 1, 10) as day, COUNT(*) as count
            FROM emails
            WHERE date_iso IS NOT NULL{where_date}
            GROUP BY day
            ORDER BY day DESC
            LIMIT 30
        """).fetchall()

        monthly_volume = cursor.execute("""
            SELECT SUBSTR(date_iso, 1, 7) as month, COUNT(*) as count
            FROM emails
            WHERE date_iso IS NOT NULL
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """).fetchall()

        category_by_account = cursor.execute(f"""
            SELECT account, category, COUNT(*) as count
            FROM emails
            WHERE 1=1{where_date}
            GROUP BY account, category
            ORDER BY account, count DESC
        """).fetchall()

        sender_by_category = cursor.execute(f"""
            SELECT category, from_addr, COUNT(*) as count
            FROM emails
            WHERE 1=1{where_date}
            GROUP BY category, from_addr
            ORDER BY category, count DESC
        """).fetchall()

        weekday_dist = cursor.execute(f"""
            SELECT CAST(STRFTIME('%w', date_iso) AS INTEGER) as dow, COUNT(*) as count
            FROM emails
            WHERE date_iso IS NOT NULL{where_date}
            GROUP BY dow
            ORDER BY dow
        """).fetchall()

        hour_dist = cursor.execute(f"""
            SELECT CAST(STRFTIME('%H', date_iso) AS INTEGER) as hour, COUNT(*) as count
            FROM emails
            WHERE date_iso IS NOT NULL{where_date}
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        date_range = cursor.execute("""
            SELECT MIN(date_iso), MAX(date_iso) FROM emails
        """).fetchone()

        conn.close()

        return {
            "total": total,
            "categories": dict(categories),
            "accounts": dict(accounts),
            "top_senders": [{"sender": r[0], "count": r[1]} for r in top_senders],
            "daily_volume": [
                {"date": r[0], "count": r[1]} for r in reversed(daily_volume)
            ],
            "monthly_volume": [
                {"month": r[0], "count": r[1]} for r in reversed(monthly_volume)
            ],
            "category_by_account": [
                {"account": r[0], "category": r[1], "count": r[2]}
                for r in category_by_account
            ],
            "sender_by_category": [
                {"category": r[0], "sender": r[1], "count": r[2]}
                for r in sender_by_category
            ],
            "weekday_dist": [{"day": r[0], "count": r[1]} for r in weekday_dist],
            "hour_dist": [{"hour": r[0], "count": r[1]} for r in hour_dist],
            "date_range": {"oldest": date_range[0], "newest": date_range[1]},
        }
    except Exception as e:
        return {
            "error": str(e),
            "total": 0,
            "categories": {},
            "accounts": {},
            "top_senders": [],
            "daily_volume": [],
            "monthly_volume": [],
            "category_by_account": [],
            "sender_by_category": [],
            "weekday_dist": [],
            "hour_dist": [],
            "date_range": {},
        }


def run_sorter(dry_run=False, max_mails=10):
    """Startet den Mail-Sorter"""
    try:
        cmd = ["./run.sh", "--max-per-account", str(max_mails)]
        if dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(
            cmd, cwd=SORTER_DIR, capture_output=True, text=True, timeout=300
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr,
        }
    except Exception as e:
        return {"success": False, "errors": str(e)}


def get_logs():
    """Lädt die letzten Logs"""
    try:
        log_file = SORTER_DIR / "mail_sorter.log"
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                return lines[-50:]  # Letzte 50 Zeilen
        return []
    except Exception as e:
        return []


# ─── Routes ───────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Dashboard (Hauptseite)"""
    stats = get_stats()
    return render_template("dashboard.html", stats=stats)


@app.route("/config")
def config_page():
    """Konfigurationsseite"""
    config = load_config()
    return render_template("configuration.html", config=config)


@app.route("/inbox")
def inbox_page():
    """Inbox — Email Client"""
    config = load_config()
    return render_template("inbox.html", config=config)


@app.route("/logs")
def logs_page():
    """Log-Seite"""
    return render_template("logs.html")


@app.route("/stats")
def stats_page():
    """Statistik-Seite"""
    stats = get_detailed_stats()
    return render_template("stats.html", stats=stats)


@app.route("/setup")
def setup_page():
    """Setup-Assistent"""
    return render_template("setup.html")


@app.route("/api/stats")
def api_stats():
    """Statistiken API"""
    return jsonify(get_stats())


@app.route("/api/ollama-check")
def api_ollama_check():
    """Prüft Ollama-Verbindung serverseitig (kein CORS-Problem)"""
    import urllib.request

    cfg = load_config()
    ollama_url = cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434")
    result = {"installed": False, "version": None, "models": [], "url": ollama_url}

    try:
        r = urllib.request.urlopen(ollama_url + "/api/version", timeout=5)
        data = json.loads(r.read().decode())
        result["installed"] = True
        result["version"] = data.get("version", "?")
    except Exception:
        return jsonify(result)

    try:
        r = urllib.request.urlopen(ollama_url + "/api/tags", timeout=5)
        data = json.loads(r.read().decode())
        for m in data.get("models", []):
            result["models"].append(
                {"name": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 1)}
            )
    except Exception:
        pass

    return jsonify(result)


@app.route("/api/stats/detailed")
def api_stats_detailed():
    days = request.args.get("days", "30")
    return jsonify(get_detailed_stats(days))


STATE_FILE = SORTER_DIR / "state.json"


def _load_state():
    default = {
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
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            s = json.load(f)
            for k, v in default.items():
                s.setdefault(k, v)
            return s
    except Exception:
        return dict(default)


def _save_state(state):
    tmp = str(STATE_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    os.replace(tmp, str(STATE_FILE))


def _daemon_running():
    state = _load_state()
    pid = state.get("pid")
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, TypeError):
        state["running"] = False
        state["pid"] = None
        _save_state(state)
        return False


@app.route("/api/sorter/status")
def api_sorter_status():
    state = _load_state()
    state["daemon_alive"] = _daemon_running()
    state["quiet_active"] = False
    if state.get("quiet_hours_enabled"):
        start = state.get("quiet_hours_start", "22:00")
        end = state.get("quiet_hours_end", "07:00")
        now = datetime.now().strftime("%H:%M")
        if start <= end:
            state["quiet_active"] = start <= now < end
        else:
            state["quiet_active"] = now >= start or now < end
    return jsonify(state)


@app.route("/api/sorter/start", methods=["POST"])
def api_sorter_start():
    state = _load_state()
    if _daemon_running():
        state["running"] = True
        state["paused"] = False
        _save_state(state)
        return jsonify(
            {"success": True, "message": "Daemon läuft bereits, Pause aufgehoben"}
        )

    _save_state({**state, "running": True, "paused": False})

    daemon_script = str(SORTER_DIR / "sorter_daemon.py")
    try:
        devnull_out = open(os.devnull, "w")
        devnull_err = open(os.devnull, "w")
        subprocess.Popen(
            [sys.executable, daemon_script],
            cwd=str(SORTER_DIR),
            stdout=devnull_out,
            stderr=devnull_err,
            start_new_session=True,
        )
        time.sleep(1)
        if _daemon_running():
            return jsonify({"success": True, "message": "Sortier-Daemon gestartet"})
        return jsonify(
            {"success": False, "error": "Daemon konnte nicht gestartet werden"}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/sorter/pause", methods=["POST"])
def api_sorter_pause():
    state = _load_state()
    state["paused"] = True
    _save_state(state)
    return jsonify({"success": True, "message": "Sortierung pausiert"})


@app.route("/api/sorter/resume", methods=["POST"])
def api_sorter_resume():
    state = _load_state()
    state["paused"] = False
    _save_state(state)
    return jsonify({"success": True, "message": "Sortierung fortgesetzt"})


@app.route("/api/sorter/stop", methods=["POST"])
def api_sorter_stop():
    state = _load_state()
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
    _save_state(state)
    return jsonify({"success": True, "message": "Sortier-Daemon gestoppt"})


@app.route("/api/sorter/quiet-hours", methods=["POST"])
def api_sorter_quiet_hours():
    data = request.json or {}
    state = _load_state()
    state["quiet_hours_enabled"] = data.get("enabled", False)
    if "start" in data:
        state["quiet_hours_start"] = data["start"]
    if "end" in data:
        state["quiet_hours_end"] = data["end"]
    if "poll_interval" in data:
        state["poll_interval_minutes"] = int(data["poll_interval"])
    _save_state(state)
    return jsonify({"success": True, "state": state})


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    """Konfigurations API"""
    if request.method == "POST":
        new_config = request.json
        if save_config(new_config):
            return jsonify({"success": True})
        else:
            return jsonify(
                {"success": False, "error": "Konnte Konfiguration nicht speichern"}
            )
    return jsonify(load_config())


@app.route("/api/rule-templates")
def api_rule_templates():
    """Rule Templates API"""
    try:
        templates_file = SORTER_DIR / "rule_templates.json"
        with open(templates_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/run", methods=["POST"])
def api_run():
    """Sortierung starten"""
    data = request.json
    dry_run = data.get("dry_run", False)
    max_mails = data.get("max_mails", 10)

    result = run_sorter(dry_run=dry_run, max_mails=max_mails)
    return jsonify(result)


@app.route("/api/logs")
def api_logs():
    logs = get_logs()
    return jsonify(logs)


@app.route("/api/logs/clear", methods=["POST"])
def api_logs_clear():
    try:
        log_file = SORTER_DIR / "mail_sorter.log"
        if log_file.exists():
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/search")
def api_search():
    """Mails suchen"""
    query = request.args.get("q", "")
    category = request.args.get("category", "")

    try:
        import sqlite3

        conn = sqlite3.connect(INDEX_DB)
        cursor = conn.cursor()

        if query:
            # FTS5 Suche
            sql = """
                SELECT e.id, e.account, e.folder, e.from_addr, e.subject,
                       e.date_iso, e.category, e.keywords
                FROM emails_fts
                JOIN emails e ON e.id = emails_fts.rowid
                WHERE emails_fts MATCH ?
                ORDER BY e.date_iso DESC
                LIMIT 20
            """
            params = [query]
        else:
            sql = """
                SELECT id, account, folder, from_addr, subject,
                       date_iso, category, keywords
                FROM emails
                WHERE 1=1
            """
            params = []

            if category:
                sql += " AND category = ?"
                params.append(category)

            sql += " ORDER BY date_iso DESC LIMIT 20"

        cursor.execute(sql, params)
        results = cursor.fetchall()

        # Konvertiere zu Liste von Dicts
        columns = [
            "id",
            "account",
            "folder",
            "from_addr",
            "subject",
            "date_iso",
            "category",
            "keywords",
        ]
        emails = [dict(zip(columns, row)) for row in results]

        conn.close()
        return jsonify({"emails": emails})

    except Exception as e:
        return jsonify({"error": str(e), "emails": []})


# ─── Email Client APIs ────────────────────────────────────────────────────


def _get_account(account_name: str):
    cfg = load_config()
    for acc in cfg.get("accounts", []):
        if acc["name"] == account_name:
            env_key = acc.get("password_env", "")
            if env_key and not acc.get("password"):
                secrets = _load_secrets()
                acc["password"] = secrets.get(env_key, os.getenv(env_key, ""))
            return acc
    return None


def _imap_connect(account):
    host = account["imap_host"]
    port = int(account.get("imap_port", 993))
    username = account["username"]
    pw = account.get("password") or os.getenv(account.get("password_env", ""), "")
    encryption = str(account.get("imap_encryption", "ssl")).lower()
    timeout = int(account.get("imap_timeout_sec", 25))
    if encryption == "starttls":
        conn = imaplib.IMAP4(host, port, timeout=timeout)
        conn.starttls(ssl_context=ssl.create_default_context())
    else:
        conn = imaplib.IMAP4_SSL(
            host, port, timeout=timeout, ssl_context=ssl.create_default_context()
        )
    conn.login(username, pw)
    return conn


def _decode_hdr(value):
    if not value:
        return ""
    parts = email_lib.header.decode_header(value)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(str(chunk))
    return "".join(out)


def _parse_uid(data):
    for item in data:
        if isinstance(item, tuple) and isinstance(item[0], bytes):
            m = re.search(rb"UID\s+(\d+)", item[0])
            if m:
                return m.group(1).decode()
    return None


def _extract_envelope(raw_header: bytes) -> dict:
    msg = email_lib.message_from_bytes(raw_header)
    return {
        "subject": _decode_hdr(msg.get("Subject", "")),
        "from": _decode_hdr(msg.get("From", "")),
        "to": _decode_hdr(msg.get("To", "")),
        "cc": _decode_hdr(msg.get("Cc", "")),
        "date": msg.get("Date", ""),
        "message_id": msg.get("Message-ID", ""),
        "in_reply_to": msg.get("In-Reply-To", ""),
        "list_unsubscribe": msg.get("List-Unsubscribe", ""),
    }


@app.route("/api/folders")
def api_folders():
    account_name = request.args.get("account", "")
    acc = _get_account(account_name)
    if not acc:
        return jsonify({"error": "Account nicht gefunden", "folders": []})
    try:
        conn = _imap_connect(acc)
        typ, data = conn.list()
        folders = []
        if typ == "OK" and data:
            for item in data:
                if not item:
                    continue
                flags, delim, name = item.decode(errors="replace").partition(' "/" ')
                name = name.strip('"').strip()
                if not name:
                    continue
                folders.append({"name": name, "flags": flags.strip()})
        conn.logout()
        return jsonify({"folders": folders})
    except Exception as e:
        return jsonify({"error": str(e), "folders": []})


@app.route("/api/inbox")
def api_inbox():
    account_name = request.args.get("account", "")
    folder = request.args.get("folder", "INBOX")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))

    acc = _get_account(account_name)
    if not acc:
        return jsonify({"error": "Account nicht gefunden", "emails": [], "total": 0})

    try:
        conn = _imap_connect(acc)
        typ, _ = conn.select(folder, readonly=True)
        if typ != "OK":
            conn.logout()
            return jsonify(
                {"error": f"Ordner {folder} nicht gefunden", "emails": [], "total": 0}
            )

        typ, data = conn.search(None, "ALL")
        if typ != "OK" or not data or not data[0]:
            conn.logout()
            return jsonify(
                {"emails": [], "total": 0, "page": page, "per_page": per_page}
            )

        all_ids = data[0].split()
        total = len(all_ids)
        start = max(0, total - page * per_page)
        end = total - (page - 1) * per_page
        page_ids = list(reversed(all_ids))[start:end]
        if not page_ids:
            conn.logout()
            return jsonify(
                {"emails": [], "total": total, "page": page, "per_page": per_page}
            )

        id_str = b",".join(page_ids)
        typ, fetched = conn.fetch(
            id_str,
            "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE MESSAGE-ID IN-REPLY-TO LIST-UNSUBSCRIBE)])",
        )
        emails = []
        if typ == "OK" and fetched:
            for item in fetched:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                header_bytes = (
                    item[1] if isinstance(item[1], bytes) else item[1].encode()
                )
                uid = _parse_uid([item])
                envelope = _extract_envelope(header_bytes)

                flags_str = (
                    item[0].decode(errors="replace")
                    if isinstance(item[0], bytes)
                    else str(item[0])
                )
                is_seen = "\\Seen" in flags_str
                is_flagged = "\\Flagged" in flags_str

                emails.append(
                    {
                        "uid": uid,
                        "seen": is_seen,
                        "flagged": is_flagged,
                        "folder": folder,
                        "account": account_name,
                        **envelope,
                    }
                )

        conn.logout()
        return jsonify(
            {"emails": emails, "total": total, "page": page, "per_page": per_page}
        )
    except Exception as e:
        return jsonify({"error": str(e), "emails": [], "total": 0})


def _fetch_account_inbox(acc, per_page, page):
    emails = []
    try:
        conn = _imap_connect(acc)
        typ, _ = conn.select("INBOX", readonly=True)
        if typ != "OK":
            conn.logout()
            return emails

        typ, data = conn.search(None, "ALL")
        if typ != "OK" or not data or not data[0]:
            conn.logout()
            return emails

        all_ids = data[0].split()
        page_ids = list(reversed(all_ids))[: per_page * page]
        if not page_ids:
            conn.logout()
            return emails

        id_str = b",".join(page_ids)
        typ, fetched = conn.fetch(
            id_str,
            "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE MESSAGE-ID IN-REPLY-TO LIST-UNSUBSCRIBE)])",
        )
        if typ == "OK" and fetched:
            for item in fetched:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                header_bytes = (
                    item[1] if isinstance(item[1], bytes) else item[1].encode()
                )
                uid = _parse_uid([item])
                envelope = _extract_envelope(header_bytes)
                flags_str = (
                    item[0].decode(errors="replace")
                    if isinstance(item[0], bytes)
                    else str(item[0])
                )
                is_seen = "\\Seen" in flags_str
                is_flagged = "\\Flagged" in flags_str
                emails.append(
                    {
                        "uid": uid,
                        "seen": is_seen,
                        "flagged": is_flagged,
                        "folder": "INBOX",
                        "account": acc["name"],
                        **envelope,
                    }
                )
        conn.logout()
    except Exception:
        pass
    return emails


@app.route("/api/unified-inbox")
def api_unified_inbox():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    cfg = load_config()
    all_emails = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(_fetch_account_inbox, acc, per_page, page): acc
            for acc in cfg.get("accounts", [])
        }
        for future in concurrent.futures.as_completed(futures):
            all_emails.extend(future.result())

    all_emails.sort(
        key=lambda e: email_lib.utils.parsedate_to_datetime(e.get("date", ""))
        if email_lib.utils.parsedate(e.get("date", ""))
        else datetime.min,
        reverse=True,
    )
    total = len(all_emails)
    start = (page - 1) * per_page
    paged = all_emails[start : start + per_page]

    return jsonify(
        {"emails": paged, "total": total, "page": page, "per_page": per_page}
    )


@app.route("/api/email/<account_name>/<folder>/<uid>")
def api_email_detail(account_name, folder, uid):
    acc = _get_account(account_name)
    if not acc:
        return jsonify({"error": "Account nicht gefunden"})

    try:
        conn = _imap_connect(acc)
        typ, _ = conn.select(folder, readonly=True)
        if typ != "OK":
            conn.logout()
            return jsonify({"error": f"Ordner {folder} nicht gefunden"})

        typ, data = conn.uid("fetch", uid, "(FLAGS BODY.PEEK[])")
        if typ != "OK" or not data:
            conn.logout()
            return jsonify({"error": "Email nicht gefunden"})

        raw_bytes = None
        flags_str = ""
        for item in data:
            if isinstance(item, tuple) and len(item) >= 2:
                flags_str = (
                    item[0].decode(errors="replace")
                    if isinstance(item[0], bytes)
                    else str(item[0])
                )
                raw_bytes = item[1] if isinstance(item[1], bytes) else item[1].encode()

        if not raw_bytes:
            conn.logout()
            return jsonify({"error": "Email-Inhalt leer"})

        msg = email_lib.message_from_bytes(raw_bytes)
        envelope = _extract_envelope(raw_bytes)

        body_text = ""
        body_html = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get("Content-Disposition") or "").lower()
                filename = part.get_filename()
                payload = part.get_payload(decode=True)

                if not payload:
                    continue

                if "attachment" in disp or (
                    filename and ctype != "text/plain" and ctype != "text/html"
                ):
                    decoded_name = _decode_hdr(filename) if filename else "attachment"
                    size = len(payload)
                    attachments.append(
                        {
                            "filename": decoded_name,
                            "size": size,
                            "content_type": ctype,
                            "data_b64": base64.b64encode(payload).decode("ascii"),
                        }
                    )
                elif ctype == "text/plain":
                    charset = part.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")
                elif ctype == "text/html":
                    charset = part.get_content_charset() or "utf-8"
                    body_html = payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                content = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    body_html = content
                else:
                    body_text = content

        is_seen = "\\Seen" in flags_str
        is_flagged = "\\Flagged" in flags_str

        if not is_seen:
            try:
                conn.uid("store", uid, "+FLAGS", "\\Seen")
            except Exception:
                pass

        thread_emails = []
        refs_header = envelope.get("references", "") or envelope.get("in_reply_to", "")
        if refs_header:
            try:
                ref_ids = [
                    r.strip().strip("<>")
                    for r in refs_header.split()
                    if r.strip().startswith("<")
                ]
                if ref_ids:
                    search_criteria = f'(OR HEADER Message-ID "<{ref_ids[-1]}>" HEADER References "{ref_ids[-1]}")'
                    typ_s, data_s = conn.search("UTF-8", search_criteria)
                    if typ_s == "OK" and data_s and data_s[0]:
                        thread_ids = data_s[0].split()
                        if len(thread_ids) > 1:
                            id_str_t = b",".join(thread_ids[:10])
                            typ_f, fetched_t = conn.fetch(
                                id_str_t,
                                "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])",
                            )
                            if typ_f == "OK" and fetched_t:
                                for item_t in fetched_t:
                                    if not isinstance(item_t, tuple) or len(item_t) < 2:
                                        continue
                                    hdr = (
                                        item_t[1]
                                        if isinstance(item_t[1], bytes)
                                        else item_t[1].encode()
                                    )
                                    env_t = _extract_envelope(hdr)
                                    mid = env_t.get("message_id", "")
                                    if mid != envelope.get("message_id", ""):
                                        thread_emails.append(env_t)
            except Exception:
                pass

        conn.logout()

        result = {
            "uid": uid,
            "folder": folder,
            "account": account_name,
            "seen": True,
            "flagged": is_flagged,
            **envelope,
            "body_text": body_text,
            "body_html": body_html,
            "attachments": [
                {
                    "filename": a["filename"],
                    "size": a["size"],
                    "content_type": a["content_type"],
                }
                for a in attachments
            ],
        }
        if thread_emails:
            result["thread"] = thread_emails
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/email/<account_name>/<folder>/<uid>/attachment/<int:att_index>")
def api_email_attachment(account_name, folder, uid, att_index):
    acc = _get_account(account_name)
    if not acc:
        return jsonify({"error": "Account nicht gefunden"}), 404

    try:
        conn = _imap_connect(acc)
        typ, _ = conn.select(folder, readonly=True)
        typ, data = conn.uid("fetch", uid, "(BODY.PEEK[])")
        conn.logout()

        raw_bytes = None
        for item in data:
            if (
                isinstance(item, tuple)
                and len(item) >= 2
                and isinstance(item[1], bytes)
            ):
                raw_bytes = item[1]

        if not raw_bytes:
            return jsonify({"error": "Nicht gefunden"}), 404

        msg = email_lib.message_from_bytes(raw_bytes)
        att_list = []
        for part in msg.walk():
            disp = str(part.get("Content-Disposition") or "").lower()
            filename = part.get_filename()
            if "attachment" in disp or filename:
                payload = part.get_payload(decode=True)
                if payload:
                    att_list.append(
                        {
                            "filename": _decode_hdr(filename or "attachment"),
                            "data": payload,
                            "content_type": part.get_content_type(),
                        }
                    )

        if att_index >= len(att_list):
            return jsonify({"error": "Anhang nicht gefunden"}), 404

        att = att_list[att_index]
        from flask import Response

        return Response(
            att["data"],
            mimetype=att["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{att["filename"]}"'
            },
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/email/<account_name>/<folder>/<uid>/flag", methods=["POST"])
def api_email_flag(account_name, folder, uid):
    acc = _get_account(account_name)
    if not acc:
        return jsonify({"error": "Account nicht gefunden"})

    data = request.json or {}
    action = data.get("action", "flag")

    try:
        conn = _imap_connect(acc)
        conn.select(folder)
        if action == "flag":
            conn.uid("store", uid, "+FLAGS", "\\Flagged")
        elif action == "unflag":
            conn.uid("store", uid, "-FLAGS", "\\Flagged")
        elif action == "read":
            conn.uid("store", uid, "+FLAGS", "\\Seen")
        elif action == "unread":
            conn.uid("store", uid, "-FLAGS", "\\Seen")
        elif action == "delete":
            conn.uid("store", uid, "+FLAGS", "\\Deleted")
            conn.expunge()
        conn.logout()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.json
    account_name = data.get("account", "")
    acc = _get_account(account_name)
    if not acc:
        return jsonify({"success": False, "error": "Account nicht gefunden"})

    try:
        from smtp_client import send_email

        attachments_raw = []
        for att in data.get("attachments", []):
            attachments_raw.append(
                {
                    "filename": att.get("filename", "attachment"),
                    "data": base64.b64decode(att.get("data_b64", "")),
                }
            )

        result = send_email(
            account=acc,
            to=data.get("to", []),
            cc=data.get("cc", []),
            bcc=data.get("bcc", []),
            subject=data.get("subject", "(Kein Betreff)"),
            body_text=data.get("body_text", ""),
            body_html=data.get("body_html"),
            reply_to=data.get("reply_to"),
            in_reply_to=data.get("in_reply_to"),
            references=data.get("references"),
            attachments=attachments_raw if attachments_raw else None,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/smtp-test", methods=["POST"])
def api_smtp_test():
    data = request.json
    account_name = data.get("account", "")
    acc = _get_account(account_name)
    if not acc:
        return jsonify({"success": False, "error": "Account nicht gefunden"})

    from smtp_client import test_smtp_connection

    return jsonify(test_smtp_connection(acc))


@app.route("/api/smtp-presets")
def api_smtp_presets():
    from smtp_client import SMTP_PRESETS

    return jsonify({"presets": list(SMTP_PRESETS.keys())})


# ─── LLM Helper APIs ─────────────────────────────────────────────────────


def _get_llm():
    cfg = load_config()
    ollama_url = cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434")
    model = cfg.get("global", {}).get("model", "llama3.1:8b")
    from llm_helper import LLMHelper

    return LLMHelper(ollama_url=ollama_url, model=model)


@app.route("/api/llm/summarize", methods=["POST"])
def api_llm_summarize():
    data = request.json or {}
    subject = data.get("subject", "")
    from_addr = data.get("from_addr", "")
    body = data.get("body", "")
    category = data.get("category", "privat")
    llm = _get_llm()
    result = llm.summarize_email(subject, from_addr, body, category)
    if result:
        uid = data.get("uid")
        account = data.get("account", "")
        folder = data.get("folder", "")
        if uid:
            try:
                llm.db.execute(
                    "INSERT OR REPLACE INTO email_summaries (msg_uid, account, folder, subject, from_addr, category, summary, importance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        uid,
                        account,
                        folder,
                        subject,
                        from_addr,
                        category,
                        result.get("summary", ""),
                        result.get("importance", "mittel"),
                    ),
                )
                llm.db.commit()
            except Exception:
                pass
        return jsonify({"success": True, **result})
    return jsonify({"success": False, "error": "LLM nicht erreichbar"})


@app.route("/api/llm/digest")
def api_llm_digest():
    llm = _get_llm()
    try:
        rows = llm.db.execute(
            "SELECT subject, from_addr, category, importance, summary FROM email_summaries WHERE created_at >= date('now', '-1 day') ORDER BY created_at DESC LIMIT 30"
        ).fetchall()
        if not rows:
            return jsonify(
                {
                    "success": True,
                    "digest": "Keine neuen Emails in den letzten 24 Stunden.",
                }
            )
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
        return jsonify({"success": True, "digest": digest, "count": len(emails)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/llm/chat", methods=["POST"])
def api_llm_chat():
    data = request.json or {}
    session_id = data.get("session_id", "default")
    message = data.get("message", "")
    if not message:
        return jsonify({"success": False, "error": "Keine Nachricht"})
    llm = _get_llm()
    llm.save_message(session_id, "user", message)
    history = llm.get_history(session_id, limit=10)
    system = (
        "Du bist ein hilfreicher Email-Assistent. Antworte auf Deutsch. "
        "Du hilfst bei Fragen zu Emails, Kategorien und Einstellungen. "
        "Sei kurz und präzise."
    )
    reply = llm.chat(history, system=system, temperature=0.7, max_tokens=300)
    if reply:
        llm.save_message(session_id, "assistant", reply)
        return jsonify({"success": True, "reply": reply})
    return jsonify({"success": False, "error": "LLM nicht erreichbar"})


@app.route("/api/llm/email-summary/<account_name>/<folder>/<uid>")
def api_llm_email_summary(account_name, folder, uid):
    acc = _get_account(account_name)
    if not acc:
        return jsonify({"error": "Account nicht gefunden"})
    try:
        conn = _imap_connect(acc)
        conn.select(folder, readonly=True)
        typ, data = conn.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
        subject = ""
        from_addr = ""
        if typ == "OK" and data:
            for item in data:
                if isinstance(item, tuple) and len(item) >= 2:
                    hdr = (
                        item[1].decode("utf-8", errors="replace")
                        if isinstance(item[1], bytes)
                        else str(item[1])
                    )
                    for line in hdr.split("\n"):
                        if line.lower().startswith("subject:"):
                            subject = line.split(":", 1)[1].strip()
                        elif line.lower().startswith("from:"):
                            from_addr = line.split(":", 1)[1].strip()
        typ2, data2 = conn.uid("fetch", uid, "(BODY.PEEK[TEXT])")
        conn.logout()
        body_text = ""
        if typ2 == "OK" and data2:
            for item in data2:
                if isinstance(item, tuple) and len(item) >= 2:
                    body_text = (
                        item[1].decode("utf-8", errors="replace")
                        if isinstance(item[1], bytes)
                        else str(item[1])
                    )
        llm = _get_llm()
        result = llm.summarize_email(subject, from_addr, body_text[:3000], "auto")
        if result:
            return jsonify({"success": True, **result})
        return jsonify({"success": False, "error": "LLM nicht erreichbar"})
    except Exception as e:
        return jsonify({"error": str(e)})


# ─── Telegram Bot APIs ────────────────────────────────────────────────────


@app.route("/api/telegram/config", methods=["GET", "POST"])
def api_telegram_config():
    cfg = load_config()
    if request.method == "POST":
        data = request.json or {}
        if "telegram" not in cfg:
            cfg["telegram"] = {}
        if "bot_token" in data:
            secrets = _load_secrets()
            secrets["TELEGRAM_BOT_TOKEN"] = data["bot_token"]
            _save_secrets(secrets)
        if "chat_id" in data:
            cfg["telegram"]["chat_id"] = data["chat_id"]
        if "notify_mode" in data:
            cfg["telegram"]["notify_mode"] = data["notify_mode"]
        if "notify_categories" in data:
            cfg["telegram"]["notify_categories"] = data["notify_categories"]
        save_config(cfg)
        return jsonify({"success": True})
    secrets = _load_secrets()
    result = dict(cfg.get("telegram", {}))
    result["bot_token"] = secrets.get("TELEGRAM_BOT_TOKEN", "")
    return jsonify(result)


@app.route("/api/telegram/generate-code", methods=["POST"])
def api_telegram_generate_code():
    import random

    code = str(random.randint(100000, 999999))
    cfg = load_config()
    if "telegram" not in cfg:
        cfg["telegram"] = {}
    cfg["telegram"]["verify_code"] = code
    cfg["telegram"]["verify_code_created"] = datetime.now().isoformat()
    cfg["telegram"].pop("chat_id", None)
    save_config(cfg)
    from telegram_bot import start_verification_poller

    start_verification_poller()
    return jsonify({"success": True, "code": code})


@app.route("/api/telegram/verify", methods=["POST"])
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

        secrets = _load_secrets()
        token = secrets.get("TELEGRAM_BOT_TOKEN", "")
        msg = "✅ Verifizierung erfolgreich! Du erhältst jetzt Benachrichtigungen für wichtige Emails."
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}",
            timeout=10,
        )
    except Exception:
        pass
    return jsonify({"success": True, "chat_id": chat_id})


@app.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    secrets = _load_secrets()
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


@app.route("/api/telegram/send-test", methods=["POST"])
def api_telegram_send_test():
    cfg = load_config()
    secrets = _load_secrets()
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


if __name__ == "__main__":
    print("🌐 Mail AI Sorter Web UI")
    print("=" * 50)
    print("Starte Web-Server auf http://0.0.0.0:5001")
    print("🔗 Tailscale: http://100.97.63.41:5001")
    print("🔗 Lokal: http://localhost:5001")
    print("Drücke STRG+C zum Beenden")
    print("=" * 50)

    app.run(debug=False, host="0.0.0.0", port=5001)
