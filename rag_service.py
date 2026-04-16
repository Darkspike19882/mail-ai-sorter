#!/usr/bin/env python3
"""
RAG-Service (Retrieval-Augmented Generation) über den Mail-Index.

Ablauf:
  1. Natürlichsprachige Frage → Filter extrahieren (Absender, Datum, Kategorie, Thema)
  2. SQLite FTS5 + Filter → Top-N relevante Mails abrufen
  3. Kontext aufbauen aus Mail-Snippets
  4. Ollama mit Kontext → präzise Antwort

Keine Vektordatenbank nötig — FTS5 reicht für Mail-Suche vollständig aus.
"""

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ai_features import _call_ollama, _parse_json_safe


# ── Query-Parser ───────────────────────────────────────────────────────────────

_MONTH_DE = {
    "januar": "01", "februar": "02", "märz": "03", "april": "04",
    "mai": "05", "juni": "06", "juli": "07", "august": "08",
    "september": "09", "oktober": "10", "november": "11", "dezember": "12",
    "jan": "01", "feb": "02", "mär": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "okt": "10", "nov": "11", "dez": "12",
}

_RELATIVE_DATES = {
    "heute": 0, "today": 0,
    "gestern": 1, "yesterday": 1,
    "diese woche": 7, "this week": 7,
    "letzte woche": 14, "last week": 14,
    "diesen monat": 30, "this month": 30,
    "letzten monat": 60, "last month": 60,
    "letztes jahr": 365, "last year": 365,
}


def parse_query_filters(query: str) -> Dict[str, Any]:
    """
    Extrahiert strukturierte Filter aus einer natürlichsprachigen Anfrage.

    Beispiele:
      "Mails von amazon.de letzte Woche"
        → {from_filter: "amazon.de", since_days: 14}
      "Was kostet mein Strom-Abo?"
        → {search: "strom abo kosten", category: "vertraege"}
      "Rechnungen von PayPal im März"
        → {from_filter: "paypal", search: "rechnung", since_iso: "YYYY-03-01"}
    """
    q = query.strip()
    filters: Dict[str, Any] = {"original": q}

    q_lower = q.lower()

    # ── Absender-Filter ──────────────────────────────────────────────────
    # "von X" / "from X" / "absender X"
    from_m = re.search(
        r"(?:von|from|absender(?:in)?|geschrieben von)\s+([a-zA-Z0-9._@\-]+\.[a-zA-Z]{2,}|[a-zA-Z0-9._@\-]+@[a-zA-Z0-9.\-]+)",
        q, re.I
    )
    if from_m:
        filters["from_filter"] = from_m.group(1).lower()
        q = q[:from_m.start()] + q[from_m.end():]

    # ── Kategorie-Filter ─────────────────────────────────────────────────
    _CATEGORY_KEYWORDS = {
        "finanzen":   ["rechnung", "zahlung", "überweisung", "konto", "bank", "paypal", "kreditkarte", "invoice"],
        "einkauf":    ["bestellung", "paket", "lieferung", "amazon", "dhl", "shop", "kaufen"],
        "reisen":     ["flug", "bahn", "hotel", "reise", "booking", "ticket", "urlaub"],
        "arbeit":     ["job", "büro", "projekt", "meeting", "kollege", "chef", "bewerbung"],
        "vertraege":  ["abo", "vertrag", "kündigung", "laufzeit", "mitgliedschaft", "strom", "internet", "mobilfunk"],
        "behoerden":  ["amt", "finanzamt", "bescheid", "behörde", "gemeinde", "steuer"],
        "paperless":  ["rechnung", "beleg", "dokument", "steuer", "quittung"],
        "newsletter": ["newsletter", "werbung", "angebot", "promotion", "marketing"],
        "tech":       ["server", "github", "deployment", "error", "alert", "monitoring"],
    }
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in q_lower for kw in keywords):
            # Nur setzen wenn nicht bereits gesetzt (erste Übereinstimmung gewinnt)
            filters.setdefault("category_hint", cat)
            break

    # ── Datum-Filter: relativ ────────────────────────────────────────────
    for phrase, days in sorted(_RELATIVE_DATES.items(), key=lambda x: -len(x[0])):
        if phrase in q_lower:
            since_dt = datetime.now(timezone.utc) - timedelta(days=days)
            filters["since_iso"] = since_dt.strftime("%Y-%m-%d")
            q = q_lower.replace(phrase, "").strip()
            break

    # ── Datum-Filter: Monat/Jahr ─────────────────────────────────────────
    if "since_iso" not in filters:
        # "im März", "im März 2025", "März 2025"
        month_m = re.search(
            r"(?:im\s+)?(" + "|".join(_MONTH_DE.keys()) + r")(?:\s+(\d{4}))?",
            q_lower
        )
        if month_m:
            month_num = _MONTH_DE[month_m.group(1)]
            year = month_m.group(2) or str(datetime.now().year)
            filters["since_iso"]  = f"{year}-{month_num}-01"
            filters["until_iso"]  = f"{year}-{month_num}-{'28' if month_num == '02' else '30'}"
            q = q[:month_m.start()] + q[month_m.end():]

    # ── Bereinigter Suchbegriff ──────────────────────────────────────────
    # Stopwords entfernen
    stopwords = {"mails", "emails", "mail", "email", "alle", "zeig", "zeige",
                 "mir", "was", "wie", "wann", "wer", "wo", "gibt", "es",
                 "haben", "hat", "hatte", "ich", "mein", "meine", "bitte",
                 "suche", "finde", "find", "suchen", "nach", "über"}
    words = [w for w in re.split(r"[\s,;]+", q.strip()) if w.lower() not in stopwords and len(w) > 2]
    search_term = " ".join(words).strip()
    if search_term:
        filters["search"] = search_term

    return filters


# ── Retrieval ──────────────────────────────────────────────────────────────────

def retrieve(
    conn: sqlite3.Connection,
    filters: Dict[str, Any],
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """
    Holt relevante Mails aus dem SQLite-Index basierend auf den extrahierten Filtern.
    Kombiniert FTS5-Volltext-Suche mit strukturierten Filtern.
    """
    search = filters.get("search", "").strip()
    from_f = filters.get("from_filter", "").strip()
    cat    = filters.get("category_hint", "").strip()
    since  = filters.get("since_iso", "").strip()
    until  = filters.get("until_iso", "").strip()

    if search:
        # FTS5-Suche mit Join für strukturierte Filter
        # FTS5-Sonderzeichen escapen
        safe_search = re.sub(r'["\(\)\*:^]', " ", search).strip()
        sql = """
            SELECT e.id, e.account, e.folder, e.from_addr, e.subject,
                   e.date_iso, e.category, e.keywords, e.snippet,
                   snippet(emails_fts, 2, '**', '**', '...', 15) AS match_snippet
            FROM emails_fts
            JOIN emails e ON e.id = emails_fts.rowid
            WHERE emails_fts MATCH ?
        """
        params: List[Any] = [safe_search]
    else:
        sql = """
            SELECT id, account, folder, from_addr, subject,
                   date_iso, category, keywords, snippet, snippet AS match_snippet
            FROM emails
            WHERE 1=1
        """
        params = []

    if from_f:
        col = "e.from_addr" if search else "from_addr"
        sql += f" AND {col} LIKE ?"
        params.append(f"%{from_f}%")

    if cat:
        col = "e.category" if search else "category"
        sql += f" AND {col} = ?"
        params.append(cat)

    if since:
        col = "e.date_iso" if search else "date_iso"
        sql += f" AND {col} >= ?"
        params.append(since)

    if until:
        col = "e.date_iso" if search else "date_iso"
        sql += f" AND {col} <= ?"
        params.append(until + "T23:59:59")

    order_col = "e.date_iso" if search else "date_iso"
    sql += f" ORDER BY {order_col} DESC LIMIT ?"
    params.append(limit)

    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ── Kontext-Builder ────────────────────────────────────────────────────────────

def build_context(mails: List[Dict[str, Any]], max_chars: int = 4000) -> str:
    """Formatiert die gefundenen Mails als kompakten Kontext für das LLM."""
    if not mails:
        return "Keine Mails gefunden."

    parts = []
    total = 0
    for i, m in enumerate(mails, 1):
        date   = (m.get("date_iso") or "")[:10]
        sender = m.get("from_addr") or ""
        subj   = m.get("subject")   or "(kein Betreff)"
        cat    = m.get("category")  or ""
        snip   = (m.get("match_snippet") or m.get("snippet") or "").strip()

        entry = (
            f"[{i}] {date} | Von: {sender} | Kategorie: {cat}\n"
            f"     Betreff: {subj}\n"
        )
        if snip:
            entry += f"     Inhalt: {snip[:300]}\n"
        entry += "\n"

        if total + len(entry) > max_chars:
            break
        parts.append(entry)
        total += len(entry)

    return "".join(parts)


# ── RAG-Antwort ────────────────────────────────────────────────────────────────

def answer(
    question: str,
    conn: sqlite3.Connection,
    ollama_url: str,
    model: str,
    limit: int = 8,
    timeout: int = 90,
) -> Dict[str, Any]:
    """
    Vollständige RAG-Pipeline:
    1. Filter aus Frage extrahieren
    2. Relevante Mails abrufen
    3. LLM-Antwort generieren

    Gibt zurück:
    {
        answer:   str,          # LLM-Antwort
        sources:  [dict],       # verwendete Mails
        filters:  dict,         # extrahierte Filter
        found:    int,          # Anzahl gefundener Mails
    }
    """
    # 1. Filter extrahieren
    filters = parse_query_filters(question)

    # 2. Retrieval
    mails = retrieve(conn, filters, limit=limit)

    # 3. Kontext aufbauen
    context = build_context(mails)

    # 4. LLM-Antwort
    system = (
        "Du bist ein hilfreicher Email-Assistent. "
        "Beantworte Fragen über Emails des Nutzers auf Deutsch. "
        "Nutze NUR die bereitgestellten Email-Daten. "
        "Wenn die Antwort nicht in den Daten steht, sag das ehrlich. "
        "Sei präzise und nenne konkrete Details (Beträge, Daten, Absender)."
    )
    user = (
        f"Frage: {question}\n\n"
        f"Verfügbare Emails ({len(mails)} gefunden):\n\n"
        f"{context}\n"
        f"---\n"
        f"Beantworte die Frage basierend auf den obigen Emails."
    )

    try:
        raw = _call_ollama(
            ollama_url, model, system, user,
            temperature=0.2,
            num_predict=400,
            timeout=timeout,
        )
        answer_text = raw.strip()
    except RuntimeError as e:
        answer_text = f"Ollama nicht erreichbar: {e}"

    # Quellen aufbereiten (ohne Snippet-Rohdaten)
    sources = [
        {
            "subject":   m.get("subject", ""),
            "from_addr": m.get("from_addr", ""),
            "date_iso":  (m.get("date_iso") or "")[:10],
            "category":  m.get("category", ""),
            "folder":    m.get("folder", ""),
            "account":   m.get("account", ""),
        }
        for m in mails
    ]

    return {
        "answer":  answer_text,
        "sources": sources,
        "filters": {k: v for k, v in filters.items() if k != "original"},
        "found":   len(mails),
    }


# ── Absender-Statistik ────────────────────────────────────────────────────────

def sender_stats(
    conn: sqlite3.Connection,
    from_filter: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Gibt alle Mails von einem bestimmten Absender zurück."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT from_addr, subject, date_iso, category, folder, account
        FROM emails
        WHERE from_addr LIKE ?
        ORDER BY date_iso DESC
        LIMIT ?
        """,
        (f"%{from_filter}%", limit),
    ).fetchall()
    return [dict(r) for r in rows]


def topic_stats(
    conn: sqlite3.Connection,
    topic: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Sucht nach Mails zu einem bestimmten Thema via FTS5."""
    conn.row_factory = sqlite3.Row
    safe = re.sub(r'["\(\)\*:^]', " ", topic).strip()
    try:
        rows = conn.execute(
            """
            SELECT e.from_addr, e.subject, e.date_iso, e.category, e.folder, e.account,
                   snippet(emails_fts, 2, '**', '**', '...', 12) AS match_snippet
            FROM emails_fts
            JOIN emails e ON e.id = emails_fts.rowid
            WHERE emails_fts MATCH ?
            ORDER BY e.date_iso DESC
            LIMIT ?
            """,
            (safe, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


def category_summary(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Gibt Kategorie-Statistiken zurück."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT category, COUNT(*) as count,
               MAX(date_iso) as latest,
               MIN(date_iso) as oldest
        FROM emails
        GROUP BY category
        ORDER BY count DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]
