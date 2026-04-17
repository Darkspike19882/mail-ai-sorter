#!/usr/bin/env python3
"""
Shared LLM orchestration for Mail AI Sorter.
"""

from typing import Any, Dict, Optional

import memory
from config_service import load_config
from llm_helper import LLMHelper


def get_llm() -> LLMHelper:
    cfg = load_config()
    ollama_url = cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434")
    model = cfg.get("global", {}).get("model", "llama3.1:8b")
    return LLMHelper(ollama_url=ollama_url, model=model)


def summarize_email(
    subject: str,
    from_addr: str,
    body: str,
    category: str = "privat",
    uid: str = "",
    account: str = "",
    folder: str = "",
) -> Optional[Dict[str, Any]]:
    llm = get_llm()
    result = llm.summarize_email(subject, from_addr, body, category)
    if not result:
        return None
    if uid and account and folder:
        memory.save_email_summary(
            uid,
            account,
            folder,
            subject,
            from_addr,
            category,
            result.get("summary", ""),
            result.get("importance", "mittel"),
        )
    return result


def analyze_email(
    subject: str,
    from_addr: str,
    body: str,
    category: str = "auto",
    uid: str = "",
    account: str = "",
    folder: str = "",
) -> Optional[Dict[str, Any]]:
    llm = get_llm()
    result = llm.analyze_email(subject, from_addr, body, category)
    if not result:
        return None
    if uid and account and folder:
        memory.save_email_summary(
            uid,
            account,
            folder,
            subject,
            from_addr,
            category,
            result.get("summary", ""),
            result.get("importance", "mittel"),
            result.get("tone"),
            result.get("action_needed", False),
        )
    return result


def draft_reply(
    subject: str,
    from_addr: str,
    body: str,
    tone: str = "freundlich",
    language: str = "de",
) -> Optional[Dict[str, str]]:
    return get_llm().draft_reply(subject, from_addr, body, tone=tone, language=language)


def build_digest(days: int = 1, limit: int = 30) -> Dict[str, Any]:
    emails = memory.get_recent_summaries(days=days, limit=limit)
    if not emails:
        return {
            "success": True,
            "digest": "Keine neuen Emails in den letzten 24 Stunden.",
            "count": 0,
        }
    llm = get_llm()
    digest = llm.smart_digest(emails)
    if not digest:
        return {"success": False, "error": "LLM nicht erreichbar"}
    return {"success": True, "digest": digest, "count": len(emails)}


def chat_with_assistant(session_id: str, message: str) -> Optional[str]:
    llm = get_llm()
    llm.save_message(session_id, "user", message)
    history = llm.get_history(session_id, limit=10)
    system = (
        "Du bist ein hilfreicher Email-Assistent. Antworte auf Deutsch. "
        "Du hilfst bei Fragen zu Emails, Kategorien und Einstellungen. "
        "Sei kurz und präzise."
    )
    reply = llm.chat(history, system=system, temperature=0.7, max_tokens=300)
    if not reply:
        return None
    llm.save_message(session_id, "assistant", reply)
    return reply
