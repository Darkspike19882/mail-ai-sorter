#!/usr/bin/env python3
"""
Telegram-Bot für den Mail AI Sorter.
Ermöglicht Ollama-Konversation über Emails direkt in Telegram.

Befehle:
  /start          — Willkommen + Hilfe
  /hilfe          — Alle Befehle anzeigen
  /mails          — Letzte ungelesene Mails
  /suche <text>   — Volltext-Suche im Mail-Index
  /absender <x>   — Alle Mails von einem Absender
  /thema <x>      — Mails zu einem bestimmten Thema
  /kategorie <x>  — Mails einer Kategorie
  /statistik      — Übersicht aller Kategorien
  /frage <text>   — RAG: freie Frage über alle Mails (Ollama antwortet)

Setup:
  pip install python-telegram-bot
  Setze TELEGRAM_BOT_TOKEN und TELEGRAM_ALLOWED_USERS in secrets.env
  python3 telegram_bot.py
"""

import json
import logging
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

# Pfad zum Projekt-Verzeichnis
_DIR = Path(__file__).parent
sys.path.insert(0, str(_DIR))

import rag_service as _rag

# Logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("telegram_bot")


# ── Konfiguration ───────────────────────────────────────────────────────────────

def _load_config() -> dict:
    cfg_path = _DIR / "config.json"
    if not cfg_path.exists():
        cfg_path = _DIR / "config.example.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_settings() -> dict:
    """Liest Bot-Einstellungen aus Config und Umgebungsvariablen."""
    # Secrets laden
    secrets_file = _DIR / "secrets.env"
    if secrets_file.exists():
        with open(secrets_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

    cfg = _load_config()
    telegram_cfg = cfg.get("global", {}).get("telegram", {})

    token = (
        telegram_cfg.get("bot_token")
        or os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    allowed_raw = (
        telegram_cfg.get("allowed_users")
        or os.getenv("TELEGRAM_ALLOWED_USERS", "")
    )
    if isinstance(allowed_raw, list):
        allowed = set(str(u) for u in allowed_raw)
    else:
        allowed = set(u.strip() for u in str(allowed_raw).split(",") if u.strip())

    return {
        "token":         token,
        "allowed_users": allowed,
        "ollama_url":    cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434"),
        "model":         cfg.get("global", {}).get("model", "llama3.1:8b"),
        "db_path":       str(_DIR / "mail_index.db"),
        "max_results":   telegram_cfg.get("max_results", 8),
    }


# ── Datenbank-Verbindung ────────────────────────────────────────────────────────

def _get_db(db_path: str) -> Optional[sqlite3.Connection]:
    if not Path(db_path).exists():
        return None
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ── Formatierungs-Helfer ────────────────────────────────────────────────────────

def _fmt_mail_list(mails: list, title: str = "") -> str:
    """Formatiert eine Mail-Liste für Telegram (Markdown)."""
    if not mails:
        return "Keine Mails gefunden."

    lines = []
    if title:
        lines.append(f"*{_esc(title)}*\n")

    for i, m in enumerate(mails[:10], 1):
        date  = (m.get("date_iso") or "")[:10]
        subj  = _esc(m.get("subject") or "(kein Betreff)")[:80]
        sender = _esc(_short_sender(m.get("from_addr") or ""))
        cat   = _esc(m.get("category") or "")
        snip  = _esc((m.get("match_snippet") or m.get("snippet") or "").strip()[:120])

        lines.append(f"*{i}\\. {subj}*")
        lines.append(f"   📧 {sender}")
        if date:
            lines.append(f"   📅 {date}")
        if cat:
            lines.append(f"   🏷 {cat}")
        if snip:
            lines.append(f"   _{snip}_")
        lines.append("")

    if len(mails) > 10:
        lines.append(f"_\\.\\.\\. und {len(mails) - 10} weitere_")

    return "\n".join(lines)


def _fmt_rag_answer(result: dict) -> str:
    """Formatiert eine RAG-Antwort für Telegram."""
    lines = []
    answer = _esc(result.get("answer", "Keine Antwort"))
    lines.append(f"🤖 *Antwort:*\n{answer}")

    sources = result.get("sources", [])
    found   = result.get("found", 0)
    if found > 0:
        lines.append(f"\n📚 *Quellen \\({found} Mails\\):*")
        for i, s in enumerate(sources[:5], 1):
            date   = (s.get("date_iso") or "")[:10]
            subj   = _esc(s.get("subject") or "")[:60]
            sender = _esc(_short_sender(s.get("from_addr") or ""))
            lines.append(f"  {i}\\. {subj} — {sender} \\({date}\\)")

    filters = result.get("filters", {})
    filter_parts = []
    if filters.get("from_filter"):
        filter_parts.append(f"Absender: {filters['from_filter']}")
    if filters.get("since_iso"):
        filter_parts.append(f"ab {filters['since_iso'][:10]}")
    if filters.get("search"):
        filter_parts.append(f"Suche: {filters['search']}")
    if filter_parts:
        lines.append(f"\n🔍 _Filter: {_esc(', '.join(filter_parts))}_")

    return "\n".join(lines)


def _fmt_category_stats(cats: list) -> str:
    """Formatiert Kategorie-Statistiken."""
    if not cats:
        return "Keine Daten im Index."
    total = sum(c.get("count", 0) for c in cats)
    lines = [f"📊 *Mail\\-Statistik \\({total:,} Mails\\)*\n"]
    for c in cats[:12]:
        name  = _esc(c.get("category") or "?")
        count = c.get("count", 0)
        pct   = round(count / max(total, 1) * 100)
        bar   = "█" * min(pct // 5, 20)
        latest = (c.get("latest") or "")[:10]
        lines.append(f"`{name:<12}` {count:>5}  {bar} {pct}%")
        if latest:
            lines.append(f"             _zuletzt: {latest}_")
    return "\n".join(lines)


def _short_sender(from_str: str) -> str:
    """Extrahiert den Anzeige-Namen oder die Kurz-Adresse."""
    m = re.match(r'"?([^"<]+)"?\s*<', from_str)
    if m:
        return m.group(1).strip()[:40]
    return from_str[:40]


def _esc(text: str) -> str:
    """Escaped Sonderzeichen für Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


# ── Bot-Handlers ────────────────────────────────────────────────────────────────

async def _check_auth(update, settings: dict) -> bool:
    """Prüft ob der Nutzer zugelassen ist."""
    if not settings["allowed_users"]:
        return True   # Kein Filter konfiguriert → alle erlaubt
    user_id = str(update.effective_user.id)
    username = str(update.effective_user.username or "")
    if user_id in settings["allowed_users"] or username in settings["allowed_users"]:
        return True
    await update.message.reply_text(
        "Zugriff verweigert. Deine ID: " + user_id
    )
    return False


def _make_handlers(settings: dict):
    """Erzeugt alle Handler-Funktionen mit Zugriff auf settings."""
    from telegram import Update
    from telegram.ext import ContextTypes

    db_path    = settings["db_path"]
    ollama_url = settings["ollama_url"]
    model      = settings["model"]
    max_r      = settings["max_results"]

    HELP_TEXT = (
        "*Mail AI Sorter — Telegram Bot*\n\n"
        "Befehle:\n"
        "`/mails` — Letzte ungelesene Mails\n"
        "`/suche <text>` — Volltext\\-Suche\n"
        "`/absender <email>` — Mails von Absender\n"
        "`/thema <stichwort>` — Mails zu Thema\n"
        "`/kategorie <name>` — Mails einer Kategorie\n"
        "`/statistik` — Übersicht aller Kategorien\n"
        "`/frage <text>` — Freie Frage \\(Ollama antwortet\\)\n\n"
        "Beispiele:\n"
        "`/frage Was kostet mein Strom-Abo?`\n"
        "`/frage Rechnungen von PayPal letzten Monat`\n"
        "`/absender amazon.de`\n"
        "`/thema rechnung März`\n"
    )

    async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")

    async def cmd_hilfe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        await update.message.reply_text(HELP_TEXT, parse_mode="MarkdownV2")

    async def cmd_mails(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        conn = _get_db(db_path)
        if not conn:
            await update.message.reply_text("Mail-Index nicht gefunden. Erst sortieren!")
            return
        rows = conn.execute(
            "SELECT from_addr, subject, date_iso, category, folder, account, snippet "
            "FROM emails ORDER BY date_iso DESC LIMIT ?",
            (max_r,)
        ).fetchall()
        conn.close()
        mails = [dict(r) for r in rows]
        await update.message.reply_text(
            _fmt_mail_list(mails, f"Letzte {len(mails)} Mails"),
            parse_mode="MarkdownV2",
        )

    async def cmd_suche(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        query = " ".join(ctx.args).strip() if ctx.args else ""
        if not query:
            await update.message.reply_text("Verwendung: `/suche <Suchbegriff>`", parse_mode="MarkdownV2")
            return
        conn = _get_db(db_path)
        if not conn:
            await update.message.reply_text("Mail-Index nicht gefunden.")
            return
        await update.message.reply_text(f"🔍 Suche nach: *{_esc(query)}*", parse_mode="MarkdownV2")
        mails = _rag.topic_stats(conn, query, limit=max_r)
        conn.close()
        await update.message.reply_text(
            _fmt_mail_list(mails, f"{len(mails)} Treffer für \"{query}\""),
            parse_mode="MarkdownV2",
        )

    async def cmd_absender(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        from_filter = " ".join(ctx.args).strip() if ctx.args else ""
        if not from_filter:
            await update.message.reply_text("Verwendung: `/absender <email oder Name>`", parse_mode="MarkdownV2")
            return
        conn = _get_db(db_path)
        if not conn:
            await update.message.reply_text("Mail-Index nicht gefunden.")
            return
        await update.message.reply_text(f"📧 Suche Mails von: *{_esc(from_filter)}*", parse_mode="MarkdownV2")
        mails = _rag.sender_stats(conn, from_filter, limit=max_r)
        conn.close()
        await update.message.reply_text(
            _fmt_mail_list(mails, f"{len(mails)} Mails von \"{from_filter}\""),
            parse_mode="MarkdownV2",
        )

    async def cmd_thema(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        topic = " ".join(ctx.args).strip() if ctx.args else ""
        if not topic:
            await update.message.reply_text("Verwendung: `/thema <Stichwort>`", parse_mode="MarkdownV2")
            return
        conn = _get_db(db_path)
        if not conn:
            await update.message.reply_text("Mail-Index nicht gefunden.")
            return
        await update.message.reply_text(f"🏷 Suche Thema: *{_esc(topic)}*", parse_mode="MarkdownV2")
        mails = _rag.topic_stats(conn, topic, limit=max_r)
        conn.close()
        await update.message.reply_text(
            _fmt_mail_list(mails, f"{len(mails)} Mails zum Thema \"{topic}\""),
            parse_mode="MarkdownV2",
        )

    async def cmd_kategorie(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        cat = " ".join(ctx.args).strip().lower() if ctx.args else ""
        if not cat:
            await update.message.reply_text("Verwendung: `/kategorie <name>`\nBeispiel: `/kategorie finanzen`", parse_mode="MarkdownV2")
            return
        conn = _get_db(db_path)
        if not conn:
            await update.message.reply_text("Mail-Index nicht gefunden.")
            return
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT from_addr, subject, date_iso, category, folder, account, snippet "
            "FROM emails WHERE category = ? ORDER BY date_iso DESC LIMIT ?",
            (cat, max_r)
        ).fetchall()
        conn.close()
        mails = [dict(r) for r in rows]
        await update.message.reply_text(
            _fmt_mail_list(mails, f"{len(mails)} Mails in Kategorie \"{cat}\""),
            parse_mode="MarkdownV2",
        )

    async def cmd_statistik(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        conn = _get_db(db_path)
        if not conn:
            await update.message.reply_text("Mail-Index nicht gefunden.")
            return
        cats = _rag.category_summary(conn)
        conn.close()
        await update.message.reply_text(
            _fmt_category_stats(cats),
            parse_mode="MarkdownV2",
        )

    async def cmd_frage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        question = " ".join(ctx.args).strip() if ctx.args else ""
        if not question:
            await update.message.reply_text(
                "Verwendung: `/frage <Frage>`\n"
                "Beispiel: `/frage Was kostet mein Strom\\-Abo?`",
                parse_mode="MarkdownV2"
            )
            return
        conn = _get_db(db_path)
        if not conn:
            await update.message.reply_text("Mail-Index nicht gefunden. Erst sortieren!")
            return
        # Lade-Nachricht
        msg = await update.message.reply_text("🤔 Analysiere Mails und frage Ollama\\.\\.\\.", parse_mode="MarkdownV2")
        try:
            result = _rag.answer(question, conn, ollama_url, model)
            text = _fmt_rag_answer(result)
            await msg.edit_text(text, parse_mode="MarkdownV2")
        except Exception as e:
            await msg.edit_text(f"Fehler: {_esc(str(e))}", parse_mode="MarkdownV2")
        finally:
            conn.close()

    # Freitext-Nachrichten → automatisch als /frage behandeln
    async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not await _check_auth(update, settings): return
        text = (update.message.text or "").strip()
        if not text or text.startswith("/"):
            return
        # Kurze Texte ignorieren
        if len(text) < 5:
            await update.message.reply_text("Tippe `/hilfe` für alle Befehle\\.", parse_mode="MarkdownV2")
            return
        # Als RAG-Frage behandeln
        ctx.args = text.split()
        await cmd_frage(update, ctx)

    return {
        "start":      cmd_start,
        "hilfe":      cmd_hilfe,
        "help":       cmd_hilfe,
        "mails":      cmd_mails,
        "suche":      cmd_suche,
        "absender":   cmd_absender,
        "thema":      cmd_thema,
        "kategorie":  cmd_kategorie,
        "statistik":  cmd_statistik,
        "frage":      cmd_frage,
        "text":       handle_text,
    }


# ── Haupt-Entry-Point ───────────────────────────────────────────────────────────

def main():
    try:
        from telegram.ext import Application, CommandHandler, MessageHandler, filters
    except ImportError:
        print("python-telegram-bot nicht installiert.")
        print("Installieren mit: pip install 'python-telegram-bot>=20.0'")
        sys.exit(1)

    settings = _get_settings()

    if not settings["token"]:
        print("Fehler: TELEGRAM_BOT_TOKEN nicht gesetzt.")
        print("Setze in secrets.env:  TELEGRAM_BOT_TOKEN=123456:ABC...")
        sys.exit(1)

    handlers = _make_handlers(settings)

    app = Application.builder().token(settings["token"]).build()

    # Befehle registrieren
    for cmd_name in ["start", "hilfe", "help", "mails", "suche",
                     "absender", "thema", "kategorie", "statistik", "frage"]:
        app.add_handler(CommandHandler(cmd_name, handlers[cmd_name]))

    # Freitext-Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers["text"]))

    allowed = settings["allowed_users"]
    logger.info(f"Bot startet | Modell: {settings['model']} | Erlaubte Nutzer: {allowed or 'alle'}")
    logger.info("Drücke STRG+C zum Beenden.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
