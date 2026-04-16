#!/usr/bin/env python3
"""
Mail AI Sorter - Web UI + Email Client
"""
import io
import os
import json
import queue as _queue
import subprocess
import threading
import time
from datetime import datetime
from typing import Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, send_file
from pathlib import Path

import imap_client as _imap
import ai_features as _ai
import smtp_client as _smtp
import rag_service as _rag
from concurrent.futures import ThreadPoolExecutor

_ai_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai")

app = Flask(__name__)
SORTER_DIR = Path(__file__).parent
CONFIG_FILE = SORTER_DIR / "config.json"
SECRETS_FILE = SORTER_DIR / "secrets.env"
INDEX_DB = SORTER_DIR / "mail_index.db"

# ─── Echtzeit-Event-Queue (SSE) ───────────────────────────────────────────────
_event_queue: _queue.Queue = _queue.Queue()

# Letzter bekannter UID pro Account/Ordner für Polling
_last_uid: dict = {}

# ─── Pool-Initialisierung ────────────────────────────────────────────────────

def _init_pool() -> None:
    """Liest Config und registriert alle Accounts im IMAP-Pool."""
    try:
        cfg = load_config()
        accounts = cfg.get("accounts", [])
        _imap.pool.init_from_config(accounts)
    except Exception as e:
        print(f"[pool] WARN: Konnte Accounts nicht laden: {e}", flush=True)


def _polling_loop() -> None:
    """Daemon-Thread: prüft alle 30s auf neue Mails und schreibt in Event-Queue."""
    while True:
        try:
            cfg = load_config()
            for acc in cfg.get("accounts", []):
                name = acc.get("name", "")
                folder = acc.get("source_folder", "INBOX")
                key = f"{name}/{folder}"
                try:
                    session = _imap.pool.get(name)
                    new_uids = session.poll_new_messages(folder, _last_uid.get(key))
                    if new_uids:
                        _last_uid[key] = new_uids[-1]
                        _event_queue.put({
                            "type":    "new_mail",
                            "account": name,
                            "folder":  folder,
                            "count":   len(new_uids),
                        })
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(30)

# ─── Helper Functions ─────────────────────────────────────────────────────

def load_config():
    """Lädt die Konfiguration"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def save_config(config):
    """Speichert die Konfiguration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[save_config] ERROR: {e}", flush=True)
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

        # Count entries in the learned-senders cache (if it exists)
        learned_senders = 0
        cache_file = SORTER_DIR / "learned_senders.json"
        if cache_file.exists():
            try:
                import json as _json
                with open(cache_file, "r", encoding="utf-8") as f:
                    learned_senders = len(_json.load(f))
            except Exception:
                pass

        return {
            "total": total,
            "categories": dict(categories),
            "accounts": dict(accounts),
            "learned_senders": learned_senders,
        }
    except Exception as e:
        return {"error": str(e)}

def run_sorter(dry_run=False, max_mails=10):
    """Startet den Mail-Sorter"""
    try:
        max_mails = max(1, min(int(max_mails), 1000))
        cmd = ["./run.sh", "--max-per-account", str(max_mails)]
        if dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(
            cmd,
            cwd=SORTER_DIR,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Write output to log file so the /logs page shows real entries
        log_file = SORTER_DIR / "mail_sorter.log"
        try:
            with open(log_file, "a", encoding="utf-8") as lf:
                if result.stdout:
                    lf.write(result.stdout)
                if result.stderr:
                    lf.write(result.stderr)
        except OSError:
            pass

        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "errors": str(e)
        }

def get_logs():
    """Lädt die letzten Logs"""
    try:
        log_file = SORTER_DIR / "mail_sorter.log"
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                return lines[-50:]  # Letzte 50 Zeilen
        return []
    except Exception as e:
        return []

# ─── Routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Dashboard (Hauptseite)"""
    stats = get_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/config')
def config_page():
    """Konfigurationsseite"""
    config = load_config()
    return render_template('configuration.html', config=config)

@app.route('/logs')
def logs_page():
    """Log-Seite"""
    return render_template('logs.html')

@app.route('/setup')
def setup_page():
    """Setup-Assistent"""
    return render_template('setup.html')

@app.route('/rules')
def rules_page():
    """Regeln-Verwaltung"""
    return render_template('rules.html')

@app.route('/api/stats')
def api_stats():
    """Statistiken API"""
    return jsonify(get_stats())


# ─── Regeln-API ───────────────────────────────────────────────────────────────

def _rule_valid(rule: dict) -> Optional[str]:
    """Gibt Fehlermeldung zurück wenn Regel ungültig, sonst None."""
    if not isinstance(rule, dict):
        return "Regel muss ein Objekt sein"
    if not rule.get("if_from_contains") and not rule.get("if_subject_contains"):
        return "Mindestens if_from_contains oder if_subject_contains erforderlich"
    if not rule.get("then_category"):
        return "then_category ist erforderlich"
    for field in ("if_from_contains", "if_subject_contains"):
        val = rule.get(field)
        if val is not None and not isinstance(val, list):
            return f"{field} muss eine Liste von Strings sein"
    return None


@app.route('/api/rules/global', methods=['GET'])
def api_rules_global_get():
    """Globale Regeln abrufen (gelten für alle Konten)."""
    cfg = load_config()
    return jsonify(cfg.get("global", {}).get("global_rules", []))


@app.route('/api/rules/global', methods=['POST'])
def api_rules_global_add():
    """Neue globale Regel hinzufügen."""
    rule = request.json or {}
    err = _rule_valid(rule)
    if err:
        return jsonify({"error": err}), 400
    cfg = load_config()
    cfg.setdefault("global", {}).setdefault("global_rules", []).append(rule)
    if not save_config(cfg):
        return jsonify({"error": "Speichern fehlgeschlagen"}), 500
    return jsonify({"success": True})


@app.route('/api/rules/global/<int:idx>', methods=['PUT'])
def api_rules_global_update(idx):
    """Globale Regel aktualisieren."""
    rule = request.json or {}
    err = _rule_valid(rule)
    if err:
        return jsonify({"error": err}), 400
    cfg = load_config()
    rules = cfg.get("global", {}).get("global_rules", [])
    if idx < 0 or idx >= len(rules):
        return jsonify({"error": "Index außerhalb des Bereichs"}), 404
    rules[idx] = rule
    cfg.setdefault("global", {})["global_rules"] = rules
    if not save_config(cfg):
        return jsonify({"error": "Speichern fehlgeschlagen"}), 500
    return jsonify({"success": True})


@app.route('/api/rules/global/<int:idx>', methods=['DELETE'])
def api_rules_global_delete(idx):
    """Globale Regel löschen."""
    cfg = load_config()
    rules = cfg.get("global", {}).get("global_rules", [])
    if idx < 0 or idx >= len(rules):
        return jsonify({"error": "Index außerhalb des Bereichs"}), 404
    rules.pop(idx)
    cfg.setdefault("global", {})["global_rules"] = rules
    if not save_config(cfg):
        return jsonify({"error": "Speichern fehlgeschlagen"}), 500
    return jsonify({"success": True})


@app.route('/api/rules/accounts/<name>', methods=['GET'])
def api_rules_account_get(name):
    """Konto-spezifische Regeln abrufen."""
    cfg = load_config()
    acc = next((a for a in cfg.get("accounts", []) if a.get("name") == name), None)
    if acc is None:
        return jsonify({"error": "Konto nicht gefunden"}), 404
    return jsonify(acc.get("rules", []))


@app.route('/api/rules/accounts/<name>', methods=['POST'])
def api_rules_account_add(name):
    """Neue konto-spezifische Regel hinzufügen."""
    rule = request.json or {}
    err = _rule_valid(rule)
    if err:
        return jsonify({"error": err}), 400
    cfg = load_config()
    acc = next((a for a in cfg.get("accounts", []) if a.get("name") == name), None)
    if acc is None:
        return jsonify({"error": "Konto nicht gefunden"}), 404
    acc.setdefault("rules", []).append(rule)
    if not save_config(cfg):
        return jsonify({"error": "Speichern fehlgeschlagen"}), 500
    return jsonify({"success": True})


@app.route('/api/rules/accounts/<name>/<int:idx>', methods=['PUT'])
def api_rules_account_update(name, idx):
    """Konto-spezifische Regel aktualisieren."""
    rule = request.json or {}
    err = _rule_valid(rule)
    if err:
        return jsonify({"error": err}), 400
    cfg = load_config()
    acc = next((a for a in cfg.get("accounts", []) if a.get("name") == name), None)
    if acc is None:
        return jsonify({"error": "Konto nicht gefunden"}), 404
    rules = acc.get("rules", [])
    if idx < 0 or idx >= len(rules):
        return jsonify({"error": "Index außerhalb des Bereichs"}), 404
    rules[idx] = rule
    acc["rules"] = rules
    if not save_config(cfg):
        return jsonify({"error": "Speichern fehlgeschlagen"}), 500
    return jsonify({"success": True})


@app.route('/api/rules/accounts/<name>/<int:idx>', methods=['DELETE'])
def api_rules_account_delete(name, idx):
    """Konto-spezifische Regel löschen."""
    cfg = load_config()
    acc = next((a for a in cfg.get("accounts", []) if a.get("name") == name), None)
    if acc is None:
        return jsonify({"error": "Konto nicht gefunden"}), 404
    rules = acc.get("rules", [])
    if idx < 0 or idx >= len(rules):
        return jsonify({"error": "Index außerhalb des Bereichs"}), 404
    rules.pop(idx)
    acc["rules"] = rules
    if not save_config(cfg):
        return jsonify({"error": "Speichern fehlgeschlagen"}), 500
    return jsonify({"success": True})

def _validate_config(cfg) -> Optional[str]:
    """Gibt eine Fehlermeldung zurück wenn die Konfiguration ungültig ist, sonst None."""
    if not isinstance(cfg, dict):
        return "Konfiguration muss ein JSON-Objekt sein"
    global_section = cfg.get("global")
    if global_section is not None and not isinstance(global_section, dict):
        return "'global' muss ein Objekt sein"
    accounts = cfg.get("accounts")
    if accounts is not None and not isinstance(accounts, list):
        return "'accounts' muss eine Liste sein"
    return None


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Konfigurations API"""
    if request.method == 'POST':
        new_config = request.json
        if new_config is None:
            return jsonify({"success": False, "error": "Kein gültiges JSON erhalten"})
        error = _validate_config(new_config)
        if error:
            return jsonify({"success": False, "error": error})
        if save_config(new_config):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Konnte Konfiguration nicht speichern"})
    return jsonify(load_config())

@app.route('/api/rule-templates')
def api_rule_templates():
    """Rule Templates API"""
    try:
        templates_file = SORTER_DIR / "rule_templates.json"
        with open(templates_file, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/run', methods=['POST'])
def api_run():
    """Sortierung starten"""
    data = request.json or {}
    dry_run = bool(data.get('dry_run', False))
    max_mails = data.get('max_mails', 10)

    result = run_sorter(dry_run=dry_run, max_mails=max_mails)
    return jsonify(result)

@app.route('/api/logs')
def api_logs():
    """Logs API"""
    logs = get_logs()
    return jsonify(logs)

@app.route('/api/search')
def api_search():
    """Mails suchen"""
    query = request.args.get('q', '')
    category = request.args.get('category', '')

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
        columns = ['id', 'account', 'folder', 'from_addr', 'subject',
                  'date_iso', 'category', 'keywords']
        emails = [dict(zip(columns, row)) for row in results]

        conn.close()
        return jsonify({"emails": emails})

    except Exception as e:
        return jsonify({"error": str(e), "emails": []})

# ─── Inbox-Seite ──────────────────────────────────────────────────────────────

@app.route('/inbox')
def inbox_page():
    """Email-Client Hauptseite."""
    return render_template('inbox.html')


# ─── Inbox API ────────────────────────────────────────────────────────────────

@app.route('/api/accounts')
def api_accounts():
    """Alle konfigurierten Accounts."""
    cfg = load_config()
    accounts = [
        {"name": a.get("name"), "host": a.get("imap_host"),
         "username": a.get("username")}
        for a in cfg.get("accounts", [])
    ]
    return jsonify(accounts)


@app.route('/api/accounts/<name>/folders')
def api_folders(name):
    """Ordner-Liste mit Unread-Count für einen Account."""
    try:
        session = _imap.pool.get(name)
        folders = session.list_folders()
        return jsonify({"folders": folders})
    except KeyError:
        return jsonify({"error": f"Account '{name}' nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages')
def api_messages(name, folder):
    """Paginierte Mail-Header-Liste mit optionalen Filtern."""
    try:
        limit  = max(1, min(int(request.args.get("limit",  50)), 200))
        offset = max(0, int(request.args.get("offset", 0)))

        # Status-Filter whitelisten (verhindert IMAP-Injection)
        status = request.args.get("search", "ALL")
        allowed = {"ALL", "UNSEEN", "SEEN", "FLAGGED", "UNFLAGGED"}
        if status not in allowed:
            status = "ALL"

        # Erweiterte Filter — werden serverseitig sicher zusammengebaut
        from_filter    = request.args.get("from_filter", "").strip()[:100]
        subject_filter = request.args.get("subject_filter", "").strip()[:100]
        since_days     = max(0, min(int(request.args.get("since_days", 0) or 0), 3650))

        search_criteria = _imap.build_search_criteria(
            status=status,
            from_filter=from_filter,
            subject_filter=subject_filter,
            since_days=since_days,
        )

        session = _imap.pool.get(name)
        mails, total = session.fetch_headers(folder, limit=limit, offset=offset,
                                             search_criteria=search_criteria)
        return jsonify({"messages": mails, "total": total,
                        "limit": limit, "offset": offset})
    except KeyError:
        return jsonify({"error": f"Account '{name}' nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages/<uid>')
def api_message(name, folder, uid):
    """Vollständige Mail (HTML sanitized, Anhang-Metadaten)."""
    if not uid.isdigit():
        return jsonify({"error": "Ungültige UID"}), 400
    try:
        session = _imap.pool.get(name)
        msg = session.fetch_message(folder, uid)
        return jsonify(msg)
    except KeyError:
        return jsonify({"error": f"Account '{name}' nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages/<uid>', methods=['PATCH'])
def api_message_flag(name, folder, uid):
    """Setzt Flags (seen, flagged) für eine Mail."""
    if not uid.isdigit():
        return jsonify({"error": "Ungültige UID"}), 400
    data = request.json or {}
    try:
        session = _imap.pool.get(name)
        results = {}
        if "seen" in data:
            results["seen"] = session.set_flag(folder, uid, "\\Seen", bool(data["seen"]))
        if "flagged" in data:
            results["flagged"] = session.set_flag(folder, uid, "\\Flagged", bool(data["flagged"]))
        return jsonify({"success": True, **results})
    except KeyError:
        return jsonify({"error": f"Account '{name}' nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages/<uid>', methods=['DELETE'])
def api_message_delete(name, folder, uid):
    """Löscht eine Mail (\\Deleted + Expunge)."""
    if not uid.isdigit():
        return jsonify({"error": "Ungültige UID"}), 400
    try:
        session = _imap.pool.get(name)
        ok = session.delete_message(folder, uid)
        return jsonify({"success": ok})
    except KeyError:
        return jsonify({"error": f"Account '{name}' nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages/<uid>/move', methods=['POST'])
def api_message_move(name, folder, uid):
    """Verschiebt eine Mail in einen anderen Ordner."""
    if not uid.isdigit():
        return jsonify({"error": "Ungültige UID"}), 400
    data = request.json or {}
    target = data.get("target_folder", "").strip()
    if not target:
        return jsonify({"error": "target_folder fehlt"}), 400
    try:
        session = _imap.pool.get(name)
        ok = session.move_message(folder, uid, target)
        return jsonify({"success": ok})
    except KeyError:
        return jsonify({"error": f"Account '{name}' nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages/<uid>/attachments/<int:part_id>')
def api_attachment(name, folder, uid, part_id):
    """Streamt einen Anhang direkt aus IMAP (kein Temp-File)."""
    if not uid.isdigit():
        return jsonify({"error": "Ungültige UID"}), 400
    try:
        session = _imap.pool.get(name)
        data, filename, content_type = session.get_attachment(folder, uid, part_id)
        return send_file(
            io.BytesIO(data),
            mimetype=content_type,
            as_attachment=True,
            download_name=filename,
        )
    except KeyError:
        return jsonify({"error": f"Account '{name}' nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── AI-Features API ──────────────────────────────────────────────────────────

def _get_ollama_cfg():
    cfg = load_config()
    g = cfg.get("global", {})
    return g.get("ollama_url", "http://127.0.0.1:11434"), g.get("model", "llama3.1:8b")


def _load_mail_for_ai(data: dict) -> dict:
    """Lädt eine Mail aus IMAP anhand von {account, folder, uid}."""
    account = data.get("account", "")
    folder  = data.get("folder", "")
    uid     = data.get("uid", "")
    if not account or not folder or not uid:
        raise ValueError("account, folder und uid sind erforderlich")
    session = _imap.pool.get(account)
    return session.fetch_message(folder, uid)


@app.route('/api/ai/summarize', methods=['POST'])
def api_ai_summarize():
    """Zusammenfassung einer Mail via LLM."""
    data = request.json or {}
    try:
        mail = _load_mail_for_ai(data)
        ollama_url, model = _get_ollama_cfg()
        future = _ai_executor.submit(
            _ai.summarize,
            mail["subject"], mail["body_text"], mail["from_addr"],
            ollama_url, model,
        )
        summary = future.result(timeout=90)
        return jsonify({"summary": summary})
    except KeyError:
        return jsonify({"error": "Account nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ai/suggest-replies', methods=['POST'])
def api_ai_suggest_replies():
    """Reply-Vorschläge für eine Mail via LLM."""
    data = request.json or {}
    try:
        mail = _load_mail_for_ai(data)
        ollama_url, model = _get_ollama_cfg()
        future = _ai_executor.submit(
            _ai.suggest_replies,
            mail["subject"], mail["body_text"], mail["from_addr"],
            ollama_url, model,
        )
        replies = future.result(timeout=120)
        return jsonify({"replies": replies})
    except KeyError:
        return jsonify({"error": "Account nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ai/check-phishing', methods=['POST'])
def api_ai_check_phishing():
    """Phishing-Analyse einer Mail (regelbasiert + LLM)."""
    data = request.json or {}
    try:
        mail = _load_mail_for_ai(data)
        ollama_url, model = _get_ollama_cfg()
        future = _ai_executor.submit(
            _ai.check_phishing,
            mail["from_addr"], mail["subject"], mail["body_text"],
            ollama_url, model,
        )
        result = future.result(timeout=90)
        return jsonify(result)
    except KeyError:
        return jsonify({"error": "Account nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages/bulk', methods=['POST'])
def api_bulk_action(name, folder):
    """
    Massen-Aktion auf mehrere Mails gleichzeitig.

    Body: {
      "action": "delete" | "mark_read" | "mark_unread" | "flag" | "unflag" | "move",
      "uids":   ["123", "456", ...],
      "target": "INBOX/Archiv"   # nur für "move"
    }
    """
    data = request.json or {}
    action = data.get("action", "").strip()
    uids   = [str(u) for u in data.get("uids", []) if str(u).isdigit()]

    if not action:
        return jsonify({"error": "action erforderlich"}), 400
    if not uids:
        return jsonify({"error": "uids erforderlich"}), 400
    if len(uids) > 200:
        return jsonify({"error": "Maximal 200 UIDs pro Anfrage"}), 400

    try:
        session = _imap.pool.get(name)
        if action == "delete":
            count = session.bulk_delete(folder, uids)
        elif action == "mark_read":
            count = session.bulk_set_flag(folder, uids, "\\Seen", True)
        elif action == "mark_unread":
            count = session.bulk_set_flag(folder, uids, "\\Seen", False)
        elif action == "flag":
            count = session.bulk_set_flag(folder, uids, "\\Flagged", True)
        elif action == "unflag":
            count = session.bulk_set_flag(folder, uids, "\\Flagged", False)
        elif action == "move":
            target = data.get("target", "").strip()
            if not target:
                return jsonify({"error": "target für move erforderlich"}), 400
            count = session.bulk_move(folder, uids, target)
        else:
            return jsonify({"error": f"Unbekannte Aktion: {action}"}), 400
        return jsonify({"success": True, "processed": count})
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats/timeline', methods=['GET'])
def api_stats_timeline():
    """Mails pro Tag für die letzten N Tage aus dem SQLite-Index."""
    days = min(int(request.args.get("days", 30)), 90)
    try:
        import sqlite3
        conn = sqlite3.connect(str(INDEX_DB), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT substr(date_iso, 1, 10) AS day, COUNT(*) AS count
            FROM emails
            WHERE date_iso >= date('now', ? || ' days')
            GROUP BY day
            ORDER BY day ASC
            """,
            (f"-{days}",),
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ai/extract-events', methods=['POST'])
def api_ai_extract_events():
    """Erkennt Termine, Meetings und Aufgaben in einer Mail via LLM."""
    data = request.json or {}
    try:
        mail = _load_mail_for_ai(data)
        ollama_url, model = _get_ollama_cfg()
        future = _ai_executor.submit(
            _ai.extract_events,
            mail["subject"], mail["body_text"], mail["from_addr"],
            ollama_url, model,
        )
        events = future.result(timeout=90)
        return jsonify({"events": events})
    except KeyError:
        return jsonify({"error": "Account nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── RAG API ──────────────────────────────────────────────────────────────────

@app.route('/api/rag/query', methods=['POST'])
def api_rag_query():
    """
    RAG-Anfrage über den Mail-Index.

    Body: {"question": "Wann kommt mein Paket von DHL?"}
    Returns: {"answer": str, "sources": [...], "filters": {...}, "found": int}
    """
    data = request.json or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "question ist erforderlich"}), 400

    limit = min(int(data.get("limit", 8)), 20)

    try:
        import sqlite3
        conn = sqlite3.connect(str(INDEX_DB), check_same_thread=False)
        ollama_url, model = _get_ollama_cfg()
        result = _rag.answer(question, conn, ollama_url, model, limit=limit)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rag/senders', methods=['GET'])
def api_rag_senders():
    """Listet die häufigsten Absender aus dem Mail-Index."""
    try:
        import sqlite3
        conn = sqlite3.connect(str(INDEX_DB), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT from_addr, COUNT(*) as count, MAX(date_iso) as latest
            FROM emails
            GROUP BY from_addr
            ORDER BY count DESC
            LIMIT 50
            """
        ).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rag/categories', methods=['GET'])
def api_rag_categories():
    """Gibt Kategorie-Statistiken aus dem Mail-Index zurück."""
    try:
        import sqlite3
        conn = sqlite3.connect(str(INDEX_DB), check_same_thread=False)
        result = _rag.category_summary(conn)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rag/sender/<path:from_filter>', methods=['GET'])
def api_rag_sender(from_filter):
    """Mails von einem bestimmten Absender."""
    limit = min(int(request.args.get("limit", 20)), 100)
    try:
        import sqlite3
        conn = sqlite3.connect(str(INDEX_DB), check_same_thread=False)
        result = _rag.sender_stats(conn, from_filter, limit=limit)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/rag/topic', methods=['GET'])
def api_rag_topic():
    """FTS5-Suche nach Thema."""
    topic = request.args.get("q", "").strip()
    if not topic:
        return jsonify({"error": "q ist erforderlich"}), 400
    limit = min(int(request.args.get("limit", 20)), 100)
    try:
        import sqlite3
        conn = sqlite3.connect(str(INDEX_DB), check_same_thread=False)
        result = _rag.topic_stats(conn, topic, limit=limit)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── SMTP API ──────────────────────────────────────────────────────────────────

def _get_smtp_client(account_name: str) -> "_smtp.SMTPClient":
    cfg = load_config()
    acc = next((a for a in cfg.get("accounts", []) if a.get("name") == account_name), None)
    if not acc:
        raise KeyError(f"Account '{account_name}' nicht gefunden")
    return _smtp.SMTPClient(acc)


@app.route('/api/accounts/<name>/send', methods=['POST'])
def api_send(name):
    """Neue Mail senden."""
    data = request.json or {}
    to      = data.get("to", [])
    subject = data.get("subject", "")
    body    = data.get("body_text", "")
    if not to or not subject or not body:
        return jsonify({"error": "to, subject und body_text sind erforderlich"}), 400
    if not isinstance(to, list):
        to = [to]
    try:
        client = _get_smtp_client(name)
        msg_id = client.send(
            to=to,
            subject=subject,
            body_text=body,
            body_html=data.get("body_html"),
            cc=data.get("cc"),
            in_reply_to=data.get("in_reply_to"),
            references=data.get("references"),
        )
        return jsonify({"success": True, "message_id": msg_id})
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages/<uid>/reply', methods=['POST'])
def api_reply(name, folder, uid):
    """Antwortet auf eine Mail."""
    if not uid.isdigit():
        return jsonify({"error": "Ungültige UID"}), 400
    data = request.json or {}
    reply_text = data.get("body_text", "")
    if not reply_text:
        return jsonify({"error": "body_text ist erforderlich"}), 400
    try:
        session = _imap.pool.get(name)
        original = session.fetch_message(folder, uid)
        client   = _get_smtp_client(name)
        params   = client.build_reply(
            original, reply_text,
            reply_all=bool(data.get("reply_all", False)),
        )
        msg_id = client.send(**params)
        return jsonify({"success": True, "message_id": msg_id})
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/accounts/<name>/folders/<path:folder>/messages/<uid>/forward', methods=['POST'])
def api_forward(name, folder, uid):
    """Leitet eine Mail weiter."""
    if not uid.isdigit():
        return jsonify({"error": "Ungültige UID"}), 400
    data = request.json or {}
    to = data.get("to", [])
    if not to:
        return jsonify({"error": "to ist erforderlich"}), 400
    if not isinstance(to, list):
        to = [to]
    try:
        session = _imap.pool.get(name)
        original = session.fetch_message(folder, uid)
        client   = _get_smtp_client(name)
        params   = client.build_forward(original, to, data.get("body_prefix", ""))
        msg_id   = client.send(**params)
        return jsonify({"success": True, "message_id": msg_id})
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Server-Sent Events (Echtzeit-Updates) ────────────────────────────────────

@app.route('/api/events')
def api_events():
    """SSE-Stream für neue Mails und andere Echtzeit-Events."""
    def generate():
        while True:
            try:
                event = _event_queue.get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
            except _queue.Empty:
                yield ": heartbeat\n\n"   # Verbindung aufrechterhalten
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Main ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("Mail AI Sorter — Email Client")
    print("=" * 50)
    print("http://localhost:5001")
    print("=" * 50)

    _init_pool()
    threading.Thread(target=_polling_loop, daemon=True).start()

    app.run(debug=False, host='127.0.0.1', port=5001, threaded=True)
