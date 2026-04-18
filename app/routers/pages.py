from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config_service import load_config
from services.stats_service import get_stats, get_detailed_stats

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": get_stats()})


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    return templates.TemplateResponse("configuration.html", {"request": request, "config": load_config()})


@router.get("/inbox", response_class=HTMLResponse)
async def inbox_page(request: Request):
    return templates.TemplateResponse("inbox.html", {"request": request, "config": load_config()})


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    return templates.TemplateResponse("logs.html", {"request": request})


@router.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    return templates.TemplateResponse("stats.html", {"request": request, "stats": get_detailed_stats()})


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    return templates.TemplateResponse("setup.html", {"request": request})


@router.get("/api/stats")
async def api_stats():
    return get_stats()


@router.get("/api/stats/detailed")
async def api_stats_detailed(days: str = "30"):
    return get_detailed_stats(days)


@router.get("/api/ollama-check")
async def api_ollama_check():
    import json
    import urllib.request
    cfg = load_config()
    ollama_url = cfg.get("global", {}).get("ollama_url", "http://127.0.0.1:11434")
    result = {"installed": False, "version": None, "models": [], "url": ollama_url}
    try:
        r = urllib.request.urlopen(ollama_url + "/api/version", timeout=5)
        data = json.loads(r.read().decode())
        result["installed"] = True
        result["version"] = data.get("version", "?")
    except Exception:
        return result
    try:
        r = urllib.request.urlopen(ollama_url + "/api/tags", timeout=5)
        data = json.loads(r.read().decode())
        for m in data.get("models", []):
            result["models"].append({"name": m["name"], "size_gb": round(m.get("size", 0) / 1e9, 1)})
    except Exception:
        pass
    return result


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "stats": get_stats()})


@router.get("/configuration")
async def configuration_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/config")
