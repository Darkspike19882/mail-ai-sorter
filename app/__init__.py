from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.routers import pages, health, inbox, email, ai, sorter, config, memory, rag, telegram, templates as tpl, command, data


class CSPMiddleware(BaseHTTPMiddleware):
    """Content Security Policy: block external requests, allow only local + required CDNs."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "connect-src 'self' http://localhost:* http://127.0.0.1:*; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob: cid: https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'"
        )
        return response


@asynccontextmanager
async def lifespan(application: FastAPI):
    import os
    port = os.environ.get("PORT", "8000")
    print("⚡ Superhero Mail")
    print("=" * 50)
    print(f"Starte Server auf http://0.0.0.0:{port}")
    print(f"Lokal: http://localhost:{port}")
    print("Druecke STRG+C zum Beenden")
    print("=" * 50)
    yield


app = FastAPI(
    title="Superhero Mail",
    description="Lokaler, DSGVO-konformer E-Mail-Client mit KI-Superkraeften",
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(CSPMiddleware)

app.include_router(pages.router)
app.include_router(health.router)
app.include_router(inbox.router)
app.include_router(email.router)
app.include_router(ai.router)
app.include_router(sorter.router)
app.include_router(config.router)
app.include_router(memory.router)
app.include_router(rag.router)
app.include_router(telegram.router)
app.include_router(tpl.router)
app.include_router(command.router)
app.include_router(data.router)
