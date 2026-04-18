from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

import memory

router = APIRouter(tags=["memory"])


@router.get("/api/memory")
async def api_memory():
    return {"success": True}


@router.get("/api/memory/sessions")
async def api_memory_sessions():
    return {"success": True, "sessions": memory.get_sessions()}


@router.get("/api/memory/facts")
async def api_memory_facts():
    return {"success": True, "facts": memory.get_facts()}


class SaveFactRequest(BaseModel):
    key: str
    value: str


@router.post("/api/memory/facts")
async def api_memory_save_fact(body: SaveFactRequest):
    memory.save_fact(body.key, body.value)
    return {"success": True}


@router.get("/api/memory/summaries")
async def api_memory_summaries():
    return {"success": True, "summaries": memory.get_recent_summaries()}


@router.get("/api/memory/rag-history")
async def api_memory_rag_history():
    return {"success": True, "history": memory.get_rag_history()}


@router.post("/api/memory/cleanup")
async def api_memory_cleanup():
    memory.cleanup_old_data()
    return {"success": True}
