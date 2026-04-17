#!/usr/bin/env python3
"""
Mail-Index — SQLite FTS5 Volltext-Suche für alle sortierten Mails.

Befehle:
  python3 index.py search "rettinar 2025"
  python3 index.py search --category rettung
  python3 index.py search --from rdschule
  python3 index.py search --since 2025-01-01 "fortbildung"
  python3 index.py stats
  python3 index.py rebuild --config config.json   (re-indiziert alles)
"""

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mail_index.db")


# ── Schema ─────────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account     TEXT NOT NULL,
    folder      TEXT NOT NULL,
    msg_uid     TEXT,
    from_addr   TEXT,
    subject     TEXT,
    date_iso    TEXT,
    category    TEXT,
    keywords    TEXT,
    snippet     TEXT,
    indexed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_emails_uid
    ON emails (account, folder, msg_uid)
    WHERE msg_uid IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_emails_category ON emails (category);
CREATE INDEX IF NOT EXISTS idx_emails_date     ON emails (date_iso);
CREATE INDEX IF NOT EXISTS idx_emails_account  ON emails (account);

-- FTS5 Volltext-Index: sucht in from_addr, subject, keywords, snippet
CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
    from_addr, subject, keywords, snippet,
    content=emails,
    content_rowid=id,
    tokenize="unicode61 tokenchars '-'"
);

-- Trigger: FTS automatisch aktualisieren
CREATE TRIGGER IF NOT EXISTS emails_ai AFTER INSERT ON emails BEGIN
    INSERT INTO emails_fts(rowid, from_addr, subject, keywords, snippet)
    VALUES (new.id, new.from_addr, new.subject, new.keywords, new.snippet);
END;

CREATE TRIGGER IF NOT EXISTS emails_ad AFTER DELETE ON emails BEGIN
    INSERT INTO emails_fts(emails_fts, rowid, from_addr, subject, keywords, snippet)
    VALUES ('delete', old.id, old.from_addr, old.subject, old.keywords, old.snippet);
END;

CREATE TRIGGER IF NOT EXISTS emails_au AFTER UPDATE ON emails BEGIN
    INSERT INTO emails_fts(emails_fts, rowid, from_addr, subject, keywords, snippet)
    VALUES ('delete', old.id, old.from_addr, old.subject, old.keywords, old.snippet);
    INSERT INTO emails_fts(rowid, from_addr, subject, keywords, snippet)
    VALUES (new.id, new.from_addr, new.subject, new.keywords, new.snippet);
END;
"""


def get_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


# ── Write ───────────────────────────────────────────────────────────────────────


def index_email(
    conn: sqlite3.Connection,
    account: str,
    folder: str,
    from_addr: str,
    subject: str,
    date_iso: Optional[str],
    category: str,
    keywords: List[str],
    snippet: str,
    msg_uid: Optional[str] = None,
) -> None:
    """Insert or update one email in the index."""
    kw_str = " ".join(keywords) if keywords else ""
    conn.execute(
        """
        INSERT INTO emails (account, folder, msg_uid, from_addr, subject,
                            date_iso, category, keywords, snippet)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(account, folder, msg_uid) WHERE msg_uid IS NOT NULL
        DO UPDATE SET
            from_addr  = excluded.from_addr,
            subject    = excluded.subject,
            date_iso   = excluded.date_iso,
            category   = excluded.category,
            keywords   = excluded.keywords,
            snippet    = excluded.snippet,
            indexed_at = datetime('now')
        """,
        (
            account,
            folder,
            msg_uid,
            from_addr,
            subject,
            date_iso,
            category,
            kw_str,
            snippet,
        ),
    )
    conn.commit()


# ── Search ──────────────────────────────────────────────────────────────────────


def search(
    conn: sqlite3.Connection,
    query: str = "",
    category: Optional[str] = None,
    from_filter: Optional[str] = None,
    since: Optional[str] = None,
    before: Optional[str] = None,
    account: Optional[str] = None,
    folder: Optional[str] = None,
    limit: int = 30,
) -> List[sqlite3.Row]:
    """Full-text + filter search. Returns matching rows, newest first."""

    if query:
        sql = """
            SELECT e.id, e.account, e.folder, e.from_addr, e.subject,
                   e.date_iso, e.category, e.keywords,
                   snippet(emails_fts, 3, '[', ']', '...', 12) AS match_snippet
            FROM emails_fts
            JOIN emails e ON e.id = emails_fts.rowid
            WHERE emails_fts MATCH ?
        """
        params: List[Any] = [query]
    else:
        sql = """
            SELECT id, account, folder, from_addr, subject,
                   date_iso, category, keywords, snippet AS match_snippet
            FROM emails
            WHERE 1=1
        """
        params = []

    if category:
        sql += " AND e.category = ?" if query else " AND category = ?"
        params.append(category)
    if from_filter:
        sql += " AND e.from_addr LIKE ?" if query else " AND from_addr LIKE ?"
        params.append(f"%{from_filter}%")
    if since:
        sql += " AND e.date_iso >= ?" if query else " AND date_iso >= ?"
        params.append(since)
    if before:
        sql += " AND e.date_iso < ?" if query else " AND date_iso < ?"
        params.append(before)
    if account:
        sql += " AND e.account = ?" if query else " AND account = ?"
        params.append(account)
    if folder:
        sql += " AND e.folder = ?" if query else " AND folder = ?"
        params.append(folder)

    sql += " ORDER BY e.date_iso DESC" if query else " ORDER BY date_iso DESC"
    sql += f" LIMIT {limit}"

    return conn.execute(sql, params).fetchall()


# ── Stats ───────────────────────────────────────────────────────────────────────


def stats(conn: sqlite3.Connection) -> None:
    total = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
    print(f"\n{'═' * 55}")
    print(f"  Mail-Index: {total:,} indizierte Mails")
    print(f"{'═' * 55}")

    print("\n  Nach Kategorie:")
    rows = conn.execute(
        "SELECT category, COUNT(*) n FROM emails GROUP BY category ORDER BY n DESC"
    ).fetchall()
    for r in rows:
        bar = "█" * (r["n"] * 30 // max(1, rows[0]["n"]))
        print(f"    {r['category']:<12} {r['n']:>5}  {bar}")

    print("\n  Nach Konto:")
    for r in conn.execute(
        "SELECT account, COUNT(*) n FROM emails GROUP BY account ORDER BY n DESC"
    ).fetchall():
        print(f"    {r['account']:<40} {r['n']:>5}")

    oldest = conn.execute("SELECT MIN(date_iso) FROM emails").fetchone()[0]
    newest = conn.execute("SELECT MAX(date_iso) FROM emails").fetchone()[0]
    print(f"\n  Zeitraum: {oldest or '?'} → {newest or '?'}")
    print(f"{'═' * 55}\n")


# ── CLI ─────────────────────────────────────────────────────────────────────────


def _fmt_row(r: sqlite3.Row, i: int) -> str:
    date = (r["date_iso"] or "")[:10]
    cat = (r["category"] or "").ljust(11)
    frm = (r["from_addr"] or "")[:30].ljust(30)
    subj = (r["subject"] or "")[:55]
    try:
        snip = (r["match_snippet"] or "").replace("\n", " ")[:80]
    except (IndexError, KeyError):
        snip = ""
    kw = (r["keywords"] or "")[:40]

    lines = [
        f"  {i:>3}. [{date}] {cat} | {frm}",
        f"       Betreff: {subj}",
    ]
    if kw:
        lines.append(f"       Keywords: {kw}")
    if snip and snip != subj:
        lines.append(f"       Treffer:  {snip}")
    lines.append(f"       Ordner:   {r['account']} / {r['folder']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Mail-Index Suche")
    sub = ap.add_subparsers(dest="cmd")

    # search
    sp = sub.add_parser("search", help="Mails suchen")
    sp.add_argument("query", nargs="?", default="", help="Suchbegriff(e)")
    sp.add_argument("--category", "-c", help="Nur diese Kategorie")
    sp.add_argument("--from", dest="from_filter", help="Absender enthält...")
    sp.add_argument("--since", help="Nur ab Datum (YYYY-MM-DD)")
    sp.add_argument("--before", help="Nur vor Datum (YYYY-MM-DD)")
    sp.add_argument("--account", help="Nur dieses Konto")
    sp.add_argument("--folder", help="Nur diesen Ordner")
    sp.add_argument("--limit", type=int, default=30)
    sp.add_argument("--db", default=DB_PATH)

    # stats
    sst = sub.add_parser("stats", help="Index-Statistik anzeigen")
    sst.add_argument("--db", default=DB_PATH)

    # rebuild (re-index from IMAP — reads config + credentials)
    srb = sub.add_parser("rebuild", help="Index aus IMAP neu aufbauen")
    srb.add_argument("--config", default="config.json")
    srb.add_argument("--db", default=DB_PATH)

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0

    db_path = getattr(args, "db", DB_PATH)
    conn = get_db(db_path)

    if args.cmd == "stats":
        stats(conn)

    elif args.cmd == "search":
        rows = search(
            conn,
            query=args.query,
            category=args.category,
            from_filter=args.from_filter,
            since=args.since,
            before=getattr(args, "before", None),
            account=getattr(args, "account", None),
            folder=getattr(args, "folder", None),
            limit=args.limit,
        )
        if not rows:
            print("Keine Treffer.")
        else:
            q_info = f'"{args.query}"' if args.query else "(kein Suchbegriff)"
            print(f"\n{len(rows)} Treffer für {q_info}:\n")
            for i, r in enumerate(rows, 1):
                print(_fmt_row(r, i))
                print()

    elif args.cmd == "rebuild":
        _rebuild(conn, args.config, db_path)

    return 0


def _rebuild(conn: sqlite3.Connection, config_path: str, db_path: str) -> None:
    """Fetch headers from all IMAP accounts and populate the index."""
    import imaplib
    import email as email_lib
    import email.utils
    import ssl

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    global_cfg = cfg["global"]

    for acc in cfg.get("accounts", []):
        name = acc["name"]
        host = acc["imap_host"]
        port = int(acc.get("imap_port", 993))
        username = acc["username"]
        pw = acc.get("password") or os.getenv(acc.get("password_env", ""))
        if not pw:
            print(f"[{name}] SKIP: Passwort fehlt", file=sys.stderr)
            continue

        target_folders = acc.get("target_folders", {})
        folders = sorted(set(target_folders.values()))

        print(f"[{name}] verbinde {host}:{port} …")
        try:
            conn_imap = imaplib.IMAP4_SSL(
                host, port, ssl_context=ssl.create_default_context()
            )
            conn_imap.login(username, pw)
        except Exception as e:
            print(f"[{name}] Login fehlgeschlagen: {e}", file=sys.stderr)
            continue

        total_indexed = 0
        for folder in folders:
            category = next(
                (k for k, v in target_folders.items() if v == folder), folder.lower()
            )
            typ, _ = conn_imap.select(folder)
            if typ != "OK":
                continue
            typ, data = conn_imap.search(None, "ALL")
            if typ != "OK" or not data or not data[0]:
                continue
            msg_ids = data[0].split()
            if not msg_ids:
                continue

            # Batch fetch headers
            id_str = b",".join(msg_ids)
            typ, headers = conn_imap.fetch(id_str, "(BODY.PEEK[HEADER] UID)")
            if typ != "OK":
                continue

            import re as _re

            for item in headers:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue
                if not isinstance(item[1], bytes):
                    continue
                uid_m = _re.search(rb"UID\s+(\d+)", item[0])
                uid = uid_m.group(1).decode() if uid_m else None
                msg = email_lib.message_from_bytes(item[1])

                def _dh(v: object) -> str:
                    if not v:
                        return ""
                    parts = email_lib.header.decode_header(v)
                    out = []
                    for chunk, enc in parts:
                        if isinstance(chunk, bytes):
                            try:
                                out.append(
                                    chunk.decode(enc or "utf-8", errors="replace")
                                )
                            except (LookupError, TypeError):
                                out.append(chunk.decode("utf-8", errors="replace"))
                        else:
                            out.append(str(chunk))
                    return "".join(out)

                subject = _dh(msg.get("Subject"))
                from_a = _dh(msg.get("From"))
                date_raw = msg.get("Date", "")
                try:
                    d = email_lib.utils.parsedate_to_datetime(date_raw)
                    date_iso = d.isoformat()
                except Exception:
                    date_iso = None

                index_email(
                    conn, name, folder, from_a, subject, date_iso, category, [], "", uid
                )
                total_indexed += 1

            print(f"  {folder}: {len(msg_ids)} Mails indiziert")

        conn_imap.logout()
        print(f"[{name}] {total_indexed} Mails gesamt indiziert")

    print(f"\nIndex: {db_path}")
    stats(conn)


if __name__ == "__main__":
    raise SystemExit(main())
