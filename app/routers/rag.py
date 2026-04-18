from fastapi import APIRouter

router = APIRouter(tags=["rag"])


@router.post("/api/rag/query")
async def api_rag_query():
    return {"success": False, "error": "Not implemented in FastAPI yet"}


@router.get("/api/rag/status")
async def api_rag_status():
    return {"success": True, "status": "ready"}


@router.get("/api/rag/history")
async def api_rag_history():
    return {"success": True, "history": []}


@router.post("/api/rag/reindex")
async def api_rag_reindex():
    return {"success": False, "error": "Not implemented in FastAPI yet"}
