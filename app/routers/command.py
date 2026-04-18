from fastapi import APIRouter
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(tags=["command-palette"])


class CommandItem(BaseModel):
    id: str
    label: str
    icon: str
    shortcut: str = ""
    category: str = "action"
    url: str = ""


def _all_commands() -> List[CommandItem]:
    return [
        CommandItem(id="inbox", label="Inbox oeffnen", icon="inbox", shortcut="G I", category="navigation", url="/inbox"),
        CommandItem(id="config", label="Einstellungen", icon="settings", shortcut="G C", category="navigation", url="/config"),
        CommandItem(id="stats", label="Statistiken", icon="bar-chart-3", shortcut="G S", category="navigation", url="/stats"),
        CommandItem(id="logs", label="Logs anzeigen", icon="file-text", shortcut="G L", category="navigation", url="/logs"),
        CommandItem(id="setup", label="Setup-Assistent", icon="wrench", shortcut="G X", category="navigation", url="/setup"),
        CommandItem(id="compose", label="Neue Email schreiben", icon="pen-square", shortcut="C", category="action", url=""),
        CommandItem(id="search", label="Emails durchsuchen", icon="search", shortcut="/", category="action", url=""),
        CommandItem(id="refresh", label="Inbox aktualisieren", icon="refresh-cw", shortcut="R", category="action", url=""),
        CommandItem(id="sorter_start", label="Sortier-Daemon starten", icon="play", shortcut="", category="daemon", url=""),
        CommandItem(id="sorter_stop", label="Sortier-Daemon stoppen", icon="square", shortcut="", category="daemon", url=""),
        CommandItem(id="sorter_run", label="Sortierung einmal ausfuehren", icon="zap", shortcut="", category="daemon", url=""),
        CommandItem(id="ai_summarize", label="AI: Aktuelle Email zusammenfassen", icon="sparkles", shortcut="S", category="ai", url=""),
        CommandItem(id="ai_draft", label="AI: Antwort-Entwurf erstellen", icon="message-square", shortcut="A", category="ai", url=""),
        CommandItem(id="ai_digest", label="AI: Tages Digest erstellen", icon="newspaper", shortcut="", category="ai", url=""),
        CommandItem(id="ai_chat", label="AI: Chat mit Assistent", icon="bot", shortcut="", category="ai", url=""),
        CommandItem(id="snooze_1h", label="Snooze: 1 Stunde", icon="clock", shortcut="H", category="snooze", url=""),
        CommandItem(id="snooze_tomorrow", label="Snooze: Morgen", icon="sunrise", shortcut="", category="snooze", url=""),
        CommandItem(id="snooze_week", label="Snooze: Naechste Woche", icon="calendar", shortcut="", category="snooze", url=""),
        CommandItem(id="archive", label="Archivieren", icon="archive", shortcut="E", category="action", url=""),
        CommandItem(id="delete", label="Loeschen", icon="trash-2", shortcut="D", category="action", url=""),
        CommandItem(id="flag", label="Stern setzen", icon="star", shortcut="F", category="action", url=""),
        CommandItem(id="dark_mode", label="Dark Mode umschalten", icon="moon", shortcut="", category="settings", url=""),
        CommandItem(id="health", label="System-Status pruefen", icon="activity", shortcut="", category="navigation", url="/api/health"),
    ]


@router.get("/api/command-palette")
async def search_commands(q: str = "") -> List[CommandItem]:
    commands = _all_commands()
    if not q:
        return commands
    q_lower = q.lower()
    return [c for c in commands if q_lower in c.label.lower() or q_lower in c.category.lower()]


@router.get("/api/command-palette/shortcuts")
async def get_shortcuts() -> List[CommandItem]:
    return [c for c in _all_commands() if c.shortcut]
