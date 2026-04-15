#!/usr/bin/env python3
"""
Mail AI Sorter - Web UI
Einfache Web-Oberfläche für den AI Email Sorter
"""
import os
import json
import subprocess
import threading
import time
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
            "accounts": dict(accounts)
        }
    except Exception as e:
        return {"error": str(e)}

def run_sorter(dry_run=False, max_mails=10):
    """Startet den Mail-Sorter"""
    try:
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

@app.route('/api/stats')
def api_stats():
    """Statistiken API"""
    return jsonify(get_stats())

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Konfigurations API"""
    if request.method == 'POST':
        new_config = request.json
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
    data = request.json
    dry_run = data.get('dry_run', False)
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

# ─── Main ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("🌐 Mail AI Sorter Web UI")
    print("=" * 50)
    print("Starte Web-Server auf http://localhost:5001")
    print("Drücke STRG+C zum Beenden")
    print("=" * 50)

    app.run(debug=False, host='127.0.0.1', port=5001)
