#!/usr/bin/env python3
"""
Shared LLM Memory for Mail AI Sorter.
Central SQLite database for conversations, email summaries, user facts, and RAG queries.
Used by: web_ui.py, llm_helper.py, rag_engine.py, telegram_bot.py, sorter_daemon.py
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).parent
MEMORY_DB = BASE_DIR / "llm_memory.db"

_db_local = threading.local()
_db_initialized = False

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL DEFAULT 'default',
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_created ON conversations(created_at);

CREATE TABLE IF NOT EXISTS user_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    confidence REAL DEFAULT 0.5,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_facts_category ON user_facts(category);

CREATE TABLE IF NOT EXISTS email_summaries (
    msg_uid TEXT NOT NULL,
    account TEXT NOT NULL,
    folder TEXT NOT NULL,
    subject TEXT,
    from_addr TEXT,
    category TEXT,
    summary TEXT,
    importance TEXT DEFAULT 'mittel',
    tone TEXT,
    action_needed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (msg_uid, account, folder)
);
CREATE INDEX IF NOT EXISTS idx_summaries_category ON email_summaries(category);
CREATE INDEX IF NOT EXISTS idx_summaries_importance ON email_summaries(importance);
CREATE INDEX IF NOT EXISTS idx_summaries_created ON email_summaries(created_at);

CREATE TABLE IF NOT EXISTS rag_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    answer TEXT,
    sources TEXT,
    email_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_rag_created ON rag_queries(created_at);

CREATE TABLE IF NOT EXISTS email_embeddings (
    msg_uid TEXT NOT NULL,
    account TEXT NOT NULL,
    folder TEXT NOT NULL,
    embedding TEXT,
    model TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (msg_uid, account, folder)
);

CREATE TABLE IF NOT EXISTS email_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_uid TEXT NOT NULL,
    account TEXT NOT NULL,
    folder TEXT NOT NULL,
    tag TEXT NOT NULL,
    source TEXT DEFAULT 'user',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_unique ON email_tags(msg_uid, account, folder, tag);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON email_tags(tag);
CREATE INDEX IF NOT EXISTS idx_tags_account ON email_tags(account, folder, msg_uid);
"""


def get_db() -> sqlite3.Connection:
    global _db_initialized
    conn = getattr(_db_local, "conn", None)
    if conn is not None:
        try:
            conn.execute("SELECT 1")
            return conn
        except Exception:
            pass
    conn = sqlite3.connect(str(MEMORY_DB), timeout=10)
    conn.row_factory = sqlite3.Row
    if not _db_initialized:
        try:
            conn.executescript(SCHEMA)
        except sqlite3.OperationalError:
            pass
        _ensure_tables(conn)
        _migrate_email_summaries(conn)
        _migrate_rag_queries(conn)
        _migrate_user_facts(conn)
        _ensure_indexes(conn)
        conn.commit()
        _db_initialized = True
    _db_local.conn = conn
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    statements = [
        """CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL DEFAULT 'default',
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS user_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            confidence REAL DEFAULT 0.5,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS email_summaries (
            msg_uid TEXT NOT NULL,
            account TEXT NOT NULL,
            folder TEXT NOT NULL,
            subject TEXT,
            from_addr TEXT,
            category TEXT,
            summary TEXT,
            importance TEXT DEFAULT 'mittel',
            tone TEXT,
            action_needed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (msg_uid, account, folder)
        )""",
        """CREATE TABLE IF NOT EXISTS rag_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            answer TEXT,
            sources TEXT,
            email_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )""",
        """CREATE TABLE IF NOT EXISTS email_embeddings (
            msg_uid TEXT NOT NULL,
            account TEXT NOT NULL,
            folder TEXT NOT NULL,
            embedding TEXT,
            model TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (msg_uid, account, folder)
        )""",
        """CREATE TABLE IF NOT EXISTS email_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_uid TEXT NOT NULL,
            account TEXT NOT NULL,
            folder TEXT NOT NULL,
            tag TEXT NOT NULL,
            source TEXT DEFAULT 'user',
            created_at TEXT DEFAULT (datetime('now'))
        )""",
    ]
    for statement in statements:
        conn.execute(statement)


def _get_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _migrate_email_summaries(conn: sqlite3.Connection) -> None:
    try:
        columns = _get_columns(conn, "email_summaries")
        if not columns:
            return
        if "category" not in columns:
            conn.execute("ALTER TABLE email_summaries ADD COLUMN category TEXT")
        if "importance" not in columns:
            conn.execute(
                "ALTER TABLE email_summaries ADD COLUMN importance TEXT DEFAULT 'mittel'"
            )
        if "tone" not in columns:
            conn.execute("ALTER TABLE email_summaries ADD COLUMN tone TEXT")
        if "action_needed" not in columns:
            conn.execute(
                "ALTER TABLE email_summaries ADD COLUMN action_needed INTEGER DEFAULT 0"
            )
        if "created_at" not in columns:
            conn.execute(
                "ALTER TABLE email_summaries ADD COLUMN created_at TEXT DEFAULT (datetime('now'))"
            )
    except Exception:
        pass


def _migrate_user_facts(conn: sqlite3.Connection) -> None:
    try:
        columns = _get_columns(conn, "user_facts")
        if not columns:
            return
        if "key" in columns or "value" in columns:
            conn.execute("ALTER TABLE user_facts RENAME TO user_facts_legacy")
            conn.execute(
                """CREATE TABLE user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    confidence REAL DEFAULT 0.5,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )"""
            )
            legacy_columns = _get_columns(conn, "user_facts_legacy")
            fact_expr = (
                "COALESCE(fact, key, value)"
                if "fact" in legacy_columns
                else ("COALESCE(key, value)" if "key" in legacy_columns else "value")
            )
            category_expr = "category" if "category" in legacy_columns else "'general'"
            confidence_expr = "confidence" if "confidence" in legacy_columns else "0.5"
            created_expr = (
                "created_at" if "created_at" in legacy_columns else "datetime('now')"
            )
            updated_expr = (
                "updated_at" if "updated_at" in legacy_columns else "datetime('now')"
            )
            conn.execute(
                f"""INSERT INTO user_facts (fact, category, confidence, created_at, updated_at)
                    SELECT {fact_expr}, {category_expr}, {confidence_expr}, {created_expr}, {updated_expr}
                    FROM user_facts_legacy
                    WHERE {fact_expr} IS NOT NULL AND TRIM({fact_expr}) != ''"""
            )
            conn.execute("DROP TABLE user_facts_legacy")
            columns = _get_columns(conn, "user_facts")
        if "fact" not in columns:
            conn.execute("ALTER TABLE user_facts ADD COLUMN fact TEXT")
            columns = _get_columns(conn, "user_facts")
        if "category" not in columns:
            conn.execute(
                "ALTER TABLE user_facts ADD COLUMN category TEXT DEFAULT 'general'"
            )
        if "confidence" not in columns:
            conn.execute(
                "ALTER TABLE user_facts ADD COLUMN confidence REAL DEFAULT 0.5"
            )
        if "created_at" not in columns:
            conn.execute(
                "ALTER TABLE user_facts ADD COLUMN created_at TEXT DEFAULT (datetime('now'))"
            )
        if "updated_at" not in columns:
            conn.execute(
                "ALTER TABLE user_facts ADD COLUMN updated_at TEXT DEFAULT (datetime('now'))"
            )
        conn.execute("DROP INDEX IF EXISTS idx_facts_unique")
        duplicate_rows = conn.execute(
            "SELECT fact FROM user_facts GROUP BY fact HAVING COUNT(*) > 1"
        ).fetchall()
        for row in duplicate_rows:
            fact = row[0]
            keep = conn.execute(
                "SELECT id FROM user_facts WHERE fact = ? ORDER BY confidence DESC, updated_at DESC, id ASC LIMIT 1",
                (fact,),
            ).fetchone()
            if keep:
                conn.execute(
                    "DELETE FROM user_facts WHERE fact = ? AND id != ?",
                    (fact, keep[0]),
                )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_unique ON user_facts(fact)"
        )
    except Exception:
        pass


def _migrate_rag_queries(conn: sqlite3.Connection) -> None:
    try:
        columns = _get_columns(conn, "rag_queries")
        if not columns:
            return
        if "sources" not in columns:
            conn.execute("ALTER TABLE rag_queries ADD COLUMN sources TEXT")
        if "email_count" not in columns:
            conn.execute(
                "ALTER TABLE rag_queries ADD COLUMN email_count INTEGER DEFAULT 0"
            )
        if "created_at" not in columns:
            conn.execute(
                "ALTER TABLE rag_queries ADD COLUMN created_at TEXT DEFAULT (datetime('now'))"
            )
    except Exception:
        pass


def _ensure_indexes(conn: sqlite3.Connection) -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_conv_created ON conversations(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_facts_category ON user_facts(category)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_facts_unique ON user_facts(fact)",
        "CREATE INDEX IF NOT EXISTS idx_summaries_category ON email_summaries(category)",
        "CREATE INDEX IF NOT EXISTS idx_summaries_importance ON email_summaries(importance)",
        "CREATE INDEX IF NOT EXISTS idx_summaries_created ON email_summaries(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_rag_created ON rag_queries(created_at)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_unique ON email_tags(msg_uid, account, folder, tag)",
        "CREATE INDEX IF NOT EXISTS idx_tags_tag ON email_tags(tag)",
        "CREATE INDEX IF NOT EXISTS idx_tags_account ON email_tags(account, folder, msg_uid)",
    ]
    for statement in statements:
        try:
            conn.execute(statement)
        except Exception:
            pass


# ─── Conversations ──────────────────────────────────────────────────────────


def save_message(session_id: str, role: str, content: str) -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.commit()
    return cursor.lastrowid


def get_history(session_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT role, content, created_at FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()
    return [
        {"role": r["role"], "content": r["content"], "created_at": r["created_at"]}
        for r in reversed(rows)
    ]


def clear_session(session_id: str) -> int:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM conversations WHERE session_id = ?", (session_id,)
    )
    conn.commit()
    return cursor.rowcount


def list_sessions() -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        """SELECT session_id, COUNT(*) as msg_count, MIN(created_at) as started, MAX(created_at) as last_active
           FROM conversations GROUP BY session_id ORDER BY last_active DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


# ─── User Facts ─────────────────────────────────────────────────────────────


def save_fact(fact: str, category: str = "general", confidence: float = 0.5) -> int:
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO user_facts (fact, category, confidence)
           VALUES (?, ?, ?)
           ON CONFLICT(fact) DO UPDATE SET
               category = excluded.category,
               confidence = excluded.confidence,
               updated_at = datetime('now')""",
        (fact, category, confidence),
    )
    conn.commit()
    return cursor.lastrowid or 0


def get_facts(
    category: Optional[str] = None, min_confidence: float = 0.3
) -> List[Dict[str, Any]]:
    conn = get_db()
    if category:
        rows = conn.execute(
            "SELECT * FROM user_facts WHERE category = ? AND confidence >= ? ORDER BY confidence DESC",
            (category, min_confidence),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM user_facts WHERE confidence >= ? ORDER BY confidence DESC",
            (min_confidence,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_fact(fact_id: int) -> bool:
    conn = get_db()
    conn.execute("DELETE FROM user_facts WHERE id = ?", (fact_id,))
    conn.commit()
    return True


# ─── Email Summaries ────────────────────────────────────────────────────────


def save_email_summary(
    msg_uid: str,
    account: str,
    folder: str,
    subject: str,
    from_addr: str,
    category: str,
    summary: str,
    importance: str = "mittel",
    tone: Optional[str] = None,
    action_needed: bool = False,
) -> bool:
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO email_summaries
           (msg_uid, account, folder, subject, from_addr, category, summary, importance, tone, action_needed)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            msg_uid,
            account,
            folder,
            subject,
            from_addr,
            category,
            summary,
            importance,
            tone,
            int(action_needed),
        ),
    )
    conn.commit()
    return True


def get_email_summary(
    msg_uid: str, account: str, folder: str
) -> Optional[Dict[str, Any]]:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM email_summaries WHERE msg_uid = ? AND account = ? AND folder = ?",
        (msg_uid, account, folder),
    ).fetchone()
    return dict(row) if row else None


def get_email_summaries_for_many(
    items: List[tuple[str, str, str]],
) -> Dict[tuple[str, str, str], Dict[str, Any]]:
    if not items:
        return {}
    conn = get_db()
    placeholders = ", ".join(["(?, ?, ?)"] * len(items))
    params: List[str] = []
    for msg_uid, account, folder in items:
        params.extend([msg_uid, account, folder])
    rows = conn.execute(
        f"SELECT * FROM email_summaries WHERE (msg_uid, account, folder) IN ({placeholders})",
        params,
    ).fetchall()
    return {(row["msg_uid"], row["account"], row["folder"]): dict(row) for row in rows}


def get_recent_summaries(
    days: int = 1, limit: int = 50, category: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_db()
    if category:
        rows = conn.execute(
            """SELECT * FROM email_summaries
               WHERE created_at >= date('now', ?) AND category = ?
               ORDER BY created_at DESC LIMIT ?""",
            (f"-{days} days", category, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM email_summaries
               WHERE created_at >= date('now', ?)
               ORDER BY created_at DESC LIMIT ?""",
            (f"-{days} days", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_summaries_by_importance(importance: str, days: int = 1) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM email_summaries
           WHERE importance = ? AND created_at >= date('now', ?)
           ORDER BY created_at DESC""",
        (importance, f"-{days} days"),
    ).fetchall()
    return [dict(r) for r in rows]


# ─── RAG Queries ────────────────────────────────────────────────────────────


def save_rag_query(query: str, answer: str, sources: str, email_count: int = 0) -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO rag_queries (query, answer, sources, email_count) VALUES (?, ?, ?, ?)",
        (query, answer, sources, email_count),
    )
    conn.commit()
    return cursor.lastrowid


def get_rag_history(limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM rag_queries ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_rag_query_count() -> int:
    conn = get_db()
    return conn.execute("SELECT COUNT(*) FROM rag_queries").fetchone()[0]


def get_rag_stats() -> Dict[str, Any]:
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM rag_queries").fetchone()[0]
    avg_emails = (
        conn.execute("SELECT AVG(email_count) FROM rag_queries").fetchone()[0] or 0
    )
    return {"total_queries": total, "avg_emails_per_query": round(avg_emails, 1)}


# ─── Email Embeddings ───────────────────────────────────────────────────────


def save_embedding(
    msg_uid: str, account: str, folder: str, embedding: List[float], model: str
) -> bool:
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO email_embeddings (msg_uid, account, folder, embedding, model)
           VALUES (?, ?, ?, ?, ?)""",
        (msg_uid, account, folder, json.dumps(embedding), model),
    )
    conn.commit()
    return True


def get_embedding(msg_uid: str, account: str, folder: str) -> Optional[List[float]]:
    conn = get_db()
    row = conn.execute(
        "SELECT embedding FROM email_embeddings WHERE msg_uid = ? AND account = ? AND folder = ?",
        (msg_uid, account, folder),
    ).fetchone()
    if row and row["embedding"]:
        return json.loads(row["embedding"])
    return None


# ─── Cleanup ────────────────────────────────────────────────────────────────


def cleanup_old_data(days: int = 90) -> Dict[str, int]:
    conn = get_db()
    convos = conn.execute(
        "DELETE FROM conversations WHERE created_at < date('now', ?)",
        (f"-{days} days",),
    ).rowcount
    rags = conn.execute(
        "DELETE FROM rag_queries WHERE created_at < date('now', ?)", (f"-{days} days",)
    ).rowcount
    conn.commit()
    return {"conversations_deleted": convos, "rag_queries_deleted": rags}


def get_db_size() -> Dict[str, Any]:
    import os

    size = MEMORY_DB.stat().st_size if MEMORY_DB.exists() else 0
    conn = get_db()
    return {
        "file_size_mb": round(size / 1024 / 1024, 2),
        "conversations": conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[
            0
        ],
        "facts": conn.execute("SELECT COUNT(*) FROM user_facts").fetchone()[0],
        "email_summaries": conn.execute(
            "SELECT COUNT(*) FROM email_summaries"
        ).fetchone()[0],
        "rag_queries": conn.execute("SELECT COUNT(*) FROM rag_queries").fetchone()[0],
        "embeddings": conn.execute("SELECT COUNT(*) FROM email_embeddings").fetchone()[
            0
        ],
        "tags": conn.execute("SELECT COUNT(*) FROM email_tags").fetchone()[0],
    }


# ─── Tags ───────────────────────────────────────────────────────────────────


def add_tag(
    msg_uid: str, account: str, folder: str, tag: str, source: str = "user"
) -> bool:
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO email_tags (msg_uid, account, folder, tag, source) VALUES (?, ?, ?, ?, ?)",
            (msg_uid, account, folder, tag.lower().strip(), source),
        )
        conn.commit()
        return True
    except Exception:
        return False


def remove_tag(msg_uid: str, account: str, folder: str, tag: str) -> bool:
    conn = get_db()
    conn.execute(
        "DELETE FROM email_tags WHERE msg_uid = ? AND account = ? AND folder = ? AND tag = ?",
        (msg_uid, account, folder, tag.lower().strip()),
    )
    conn.commit()
    return True


def get_tags(msg_uid: str, account: str, folder: str) -> List[str]:
    conn = get_db()
    rows = conn.execute(
        "SELECT tag FROM email_tags WHERE msg_uid = ? AND account = ? AND folder = ? ORDER BY tag",
        (msg_uid, account, folder),
    ).fetchall()
    return [r["tag"] for r in rows]


def get_tags_for_many(
    items: List[tuple[str, str, str]],
) -> Dict[tuple[str, str, str], List[str]]:
    if not items:
        return {}
    conn = get_db()
    placeholders = ", ".join(["(?, ?, ?)"] * len(items))
    params: List[str] = []
    for msg_uid, account, folder in items:
        params.extend([msg_uid, account, folder])
    rows = conn.execute(
        f"SELECT msg_uid, account, folder, tag FROM email_tags WHERE (msg_uid, account, folder) IN ({placeholders}) ORDER BY tag",
        params,
    ).fetchall()
    result: Dict[tuple[str, str, str], List[str]] = {item: [] for item in items}
    for row in rows:
        key = (row["msg_uid"], row["account"], row["folder"])
        result.setdefault(key, []).append(row["tag"])
    return result


def get_all_tags(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT tag, COUNT(*) as count FROM email_tags GROUP BY tag ORDER BY count DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [{"tag": r["tag"], "count": r["count"]} for r in rows]


def search_by_tag(tag: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        """SELECT et.msg_uid, et.account, et.folder, et.tag, es.subject, es.from_addr,
                  es.category, es.importance, es.created_at
           FROM email_tags et
           LEFT JOIN email_summaries es ON es.msg_uid = et.msg_uid AND es.account = et.account AND es.folder = et.folder
           WHERE et.tag = ?
           ORDER BY es.created_at DESC
           LIMIT ?""",
        (tag.lower().strip(), limit),
    ).fetchall()
    return [dict(r) for r in rows]


def merge_tags(old_tag: str, new_tag: str) -> int:
    conn = get_db()
    conn.execute(
        "UPDATE OR IGNORE email_tags SET tag = ? WHERE tag = ?",
        (new_tag.lower().strip(), old_tag.lower().strip()),
    )
    conn.execute(
        "DELETE FROM email_tags WHERE tag = ?",
        (old_tag.lower().strip(),),
    )
    conn.commit()
    return 1


def delete_tag(tag: str) -> int:
    conn = get_db()
    cursor = conn.execute(
        "DELETE FROM email_tags WHERE tag = ?", (tag.lower().strip(),)
    )
    conn.commit()
    return cursor.rowcount
