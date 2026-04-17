#!/usr/bin/env python3
"""
RAG Engine for Mail AI Sorter.
Retrieval-Augmented Generation: search emails with FTS5, feed context to Ollama, get answers.
"""

import json
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

import memory

BASE_DIR = Path(__file__).parent
INDEX_DB = BASE_DIR / "mail_index.db"


class RAGEngine:
    def __init__(
        self, ollama_url: str = "http://127.0.0.1:11434", model: str = "llama3.1:8b"
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model

    def _get_index_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(INDEX_DB), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def search_emails(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []
        conn = self._get_index_db()
        try:
            safe_query = query.replace('"', '""')
            rows = conn.execute(
                f"""
                SELECT e.id, e.account, e.folder, e.msg_uid, e.from_addr, e.subject,
                       e.date_iso, e.category, e.snippet, e.keywords,
                       snippet(emails_fts, 3, '[', ']', '...', 15) AS match_snippet
                FROM emails_fts
                JOIN emails e ON e.id = emails_fts.rowid
                WHERE emails_fts MATCH ?
                ORDER BY e.date_iso DESC
                LIMIT ?
            """,
                (safe_query, limit),
            ).fetchall()

            results = []
            for r in rows:
                results.append(
                    {
                        "id": r["id"],
                        "account": r["account"],
                        "folder": r["folder"],
                        "msg_uid": r["msg_uid"],
                        "from_addr": r["from_addr"],
                        "subject": r["subject"],
                        "date_iso": r["date_iso"],
                        "category": r["category"],
                        "snippet": r["snippet"],
                        "match_snippet": r["match_snippet"],
                        "keywords": r["keywords"],
                    }
                )
            return results
        finally:
            conn.close()

    def build_context(
        self, emails: List[Dict[str, Any]], max_tokens: int = 3000
    ) -> str:
        if not emails:
            return ""
        parts = []
        total_chars = 0
        for i, e in enumerate(emails):
            date = (e.get("date_iso") or "?")[:10]
            subject = e.get("subject") or "(Kein Betreff)"
            from_addr = e.get("from_addr") or "?"
            snippet = e.get("snippet") or e.get("match_snippet") or ""
            category = e.get("category") or "?"

            email_text = f"[{i + 1}] {date} | {from_addr} | {subject}\nKategorie: {category}\nInhalt: {snippet}\n"
            if total_chars + len(email_text) > max_tokens * 4:
                break
            parts.append(email_text)
            total_chars += len(email_text)

        return "\n".join(parts)

    def query(self, user_query: str, limit: int = 10) -> Dict[str, Any]:
        emails = self.search_emails(user_query, limit=limit)
        context = self.build_context(emails)

        if not context:
            return {
                "success": True,
                "answer": f'Keine Emails gefunden für "{user_query}".',
                "sources": [],
                "email_count": 0,
            }

        system_prompt = (
            "Du bist ein Email-Assistent. Antworte auf Deutsch. "
            "Analysiere die folgenden Emails und beantworte die Frage des Nutzers. "
            "Beziehe dich konkret auf die Emails und nenne Datum und Absender. "
            "Wenn die Frage nicht beantwortet werden kann, sag das ehrlich. "
            "Sei kurz und präzise."
        )

        user_message = f"Frage: {user_query}\n\nGefundene Emails:\n{context}"

        answer = self._call_ollama(system_prompt, user_message)

        sources = []
        for e in emails[:5]:
            sources.append(
                {
                    "id": e["id"],
                    "account": e["account"],
                    "folder": e["folder"],
                    "msg_uid": e["msg_uid"],
                    "from_addr": e["from_addr"],
                    "subject": e["subject"],
                    "date": (e.get("date_iso") or "")[:10],
                    "category": e.get("category", ""),
                }
            )

        memory.save_rag_query(
            user_query,
            answer or "Konnte keine Antwort generieren.",
            json.dumps(sources, ensure_ascii=False),
            len(emails),
        )

        return {
            "success": True,
            "answer": answer or "Konnte keine Antwort generieren.",
            "sources": sources,
            "email_count": len(emails),
        }

    def _call_ollama(
        self, system: str, user_message: str, temperature: float = 0.3
    ) -> Optional[str]:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "options": {"temperature": temperature, "num_predict": 500},
            }
        ).encode()

        try:
            req = urllib.request.Request(
                f"{self.ollama_url}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data.get("message", {}).get("content", "")
        except Exception as e:
            return None

    def get_status(self) -> Dict[str, Any]:
        conn = self._get_index_db()
        try:
            total = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
            with_body = conn.execute(
                "SELECT COUNT(*) FROM emails WHERE snippet != ''"
            ).fetchone()[0]
            oldest = conn.execute("SELECT MIN(date_iso) FROM emails").fetchone()[0]
            newest = conn.execute("SELECT MAX(date_iso) FROM emails").fetchone()[0]

            categories = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM emails GROUP BY category ORDER BY cnt DESC"
            ).fetchall()

            query_count = memory.get_rag_query_count()

            return {
                "total_emails": total,
                "emails_with_body": with_body,
                "date_range": {"oldest": oldest, "newest": newest},
                "categories": [
                    {"name": r["category"], "count": r["cnt"]} for r in categories
                ],
                "rag_queries": query_count,
                "model": self.model,
                "ollama_url": self.ollama_url,
            }
        finally:
            conn.close()

    def reindex(self) -> Dict[str, Any]:
        conn = self._get_index_db()
        try:
            conn.execute("DELETE FROM emails")
            conn.execute("DELETE FROM emails_fts")
            conn.commit()
            return {
                "success": True,
                "message": "Index gelöscht. Neu aufbauen mit sorter.py --index",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
