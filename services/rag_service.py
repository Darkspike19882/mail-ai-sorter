#!/usr/bin/env python3
"""
Shared RAG service wrapper.
"""

from typing import Any, Dict, Optional

from config_service import load_config
from rag_engine import RAGEngine


def get_engine() -> RAGEngine:
    cfg = load_config()
    ollama_url = cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434")
    model = cfg.get("global", {}).get("model", "llama3.1:8b")
    return RAGEngine(ollama_url=ollama_url, model=model)


def query(
    user_query: str,
    limit: int = 10,
    account: Optional[str] = None,
    folder: Optional[str] = None,
    since: Optional[str] = None,
    before: Optional[str] = None,
) -> Dict[str, Any]:
    return get_engine().query(
        user_query,
        limit=limit,
        account=account,
        folder=folder,
        since=since,
        before=before,
    )


def get_status() -> Dict[str, Any]:
    return get_engine().get_status()


def reindex() -> Dict[str, Any]:
    return get_engine().reindex()
