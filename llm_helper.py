#!/usr/bin/env python3
"""
LLM Helper for Mail AI Sorter.
Wraps Ollama API with conversation memory and structured outputs.
"""

import json
import os
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).parent
MEMORY_DB = BASE_DIR / "llm_memory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);

CREATE TABLE IF NOT EXISTS user_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    msg_uid TEXT,
    account TEXT,
    folder TEXT,
    subject TEXT,
    from_addr TEXT,
    category TEXT,
    summary TEXT,
    importance TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_email_sum_uid ON email_summaries(account, folder, msg_uid);
"""


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(MEMORY_DB), timeout=10)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


class LLMHelper:
    def __init__(
        self, ollama_url: str = "http://127.0.0.1:11434", model: str = "llama3.1:8b"
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.timeout = 60
        self.db = _get_db()

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        json_format: bool = False,
        json_schema: Optional[dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Optional[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "keep_alive": "10m",
        }
        if system:
            payload["system"] = system
        if json_format and json_schema:
            payload["format"] = json_schema
        elif json_format:
            payload["format"] = "json"

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.ollama_url + "/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("message", {}).get("content", "")
        except Exception as e:
            print(f"[LLM] Error: {e}")
            return None

    def save_message(self, session_id: str, role: str, content: str):
        self.db.execute(
            "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        self.db.commit()

    def get_history(self, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
        rows = self.db.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def save_fact(self, key: str, value: str):
        self.db.execute(
            "INSERT INTO user_facts (key, value, updated_at) VALUES (?, ?, datetime('now')) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
            (key, value),
        )
        self.db.commit()

    def get_facts(self) -> Dict[str, str]:
        rows = self.db.execute("SELECT key, value FROM user_facts").fetchall()
        return {r[0]: r[1] for r in rows}

    def summarize_email(
        self, subject: str, from_addr: str, body: str, category: str
    ) -> Optional[Dict[str, str]]:
        system = (
            "Du bist ein Email-Assistent. Erstelle eine kurze Zusammenfassung in 1-3 Sätzen auf Deutsch. "
            "Bewerte die Wichtigkeit: 'hoch' (Rechnungen, Fristen, wichtig), 'mittel' (normal), 'niedrig' (Newsletter, Spam). "
            "Antworte IMMER als JSON mit den Feldern: summary, importance"
        )
        prompt = (
            f"Betreff: {subject}\n"
            f"Von: {from_addr}\n"
            f"Kategorie: {category}\n"
            f"Inhalt: {body[:2000]}\n\n"
            "Fasse diese Email zusammen und bewerte ihre Wichtigkeit."
        )
        messages = [{"role": "user", "content": prompt}]
        result = self.chat(
            messages, system=system, json_format=True, temperature=0.3, max_tokens=200
        )
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return {"summary": result[:200], "importance": "mittel"}
        return None

    def smart_digest(self, emails: List[Dict[str, Any]]) -> Optional[str]:
        if not emails:
            return None
        system = (
            "Du bist ein Email-Assistent. Erstelle einen täglichen Email-Bericht auf Deutsch. "
            "Gruppiere nach Wichtigkeit. Sehr kurz und prägnant. Max 10 Sätze insgesamt."
        )
        email_list = []
        for e in emails[:30]:
            email_list.append(
                f"- [{e.get('importance', '?')}] {e.get('subject', '?')} (von {e.get('from_addr', '?')}, Kategorie: {e.get('category', '?')})"
            )
        prompt = (
            f"Hier sind {len(emails)} neue Emails von heute:\n\n"
            + "\n".join(email_list)
            + "\n\nErstelle einen kurzen täglichen Bericht."
        )
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, system=system, temperature=0.5, max_tokens=400)

    def should_notify(
        self, subject: str, from_addr: str, category: str, importance: str
    ) -> bool:
        if importance == "hoch":
            return True
        if importance == "niedrig":
            return False
        notify_categories = {"finanzen", "behoerden", "vertraege", "rettung", "wohnen"}
        return category.lower() in notify_categories
