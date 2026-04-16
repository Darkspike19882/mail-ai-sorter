#!/usr/bin/env python3
"""
LLM Helper for Mail AI Sorter.
Wraps Ollama API with conversation memory and structured outputs.
Uses shared memory.py for persistence.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import memory


class LLMHelper:
    def __init__(
        self, ollama_url: str = "http://127.0.0.1:11434", model: str = "llama3.1:8b"
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.timeout = 60
        self.db = memory.get_db()

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        json_format: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
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
        memory.save_message(session_id, role, content)

    def get_history(self, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
        rows = memory.get_history(session_id, limit)
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    def save_fact(self, key: str, value: str):
        memory.save_fact(key, value)

    def get_facts(self) -> Dict[str, str]:
        facts = memory.get_facts()
        return {f["fact"]: f.get("category", "") for f in facts}

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
