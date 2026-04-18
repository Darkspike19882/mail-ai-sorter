from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

import memory
from services import sorter_service

router = APIRouter(tags=["sorter"])


@router.get("/api/sorter/status")
async def api_sorter_status():
    return sorter_service.get_status()


@router.post("/api/sorter/start")
async def api_sorter_start():
    return sorter_service.start_daemon()


@router.post("/api/sorter/pause")
async def api_sorter_pause():
    return sorter_service.pause_daemon()


@router.post("/api/sorter/resume")
async def api_sorter_resume():
    return sorter_service.resume_daemon()


@router.post("/api/sorter/stop")
async def api_sorter_stop():
    return sorter_service.stop_daemon()


class QuietHoursRequest(BaseModel):
    enabled: Optional[bool] = None
    start: Optional[str] = None
    end: Optional[str] = None


@router.post("/api/sorter/quiet-hours")
async def api_sorter_quiet_hours(body: QuietHoursRequest):
    return sorter_service.update_quiet_hours(body.model_dump(exclude_none=True))


class RunRequest(BaseModel):
    dry_run: bool = False
    max_mails: int = 10


@router.post("/api/run")
async def api_run(body: RunRequest):
    return sorter_service.run_sorter_once(dry_run=body.dry_run, max_mails=body.max_mails)


@router.get("/api/logs")
async def api_logs():
    return sorter_service.get_logs()


@router.post("/api/logs/clear")
async def api_logs_clear():
    return sorter_service.clear_logs()


@router.get("/api/sort-actions")
async def api_sort_actions(limit: int = 50, account: str = "", since: str = ""):
    return {
        "success": True,
        "actions": memory.get_sort_actions(limit=min(limit, 200), account=account or None, since=since or None),
    }


@router.get("/api/sort-actions/stats")
async def api_sort_actions_stats(since: str = ""):
    return {"success": True, "stats": memory.get_sort_action_stats(since=since or None)}
