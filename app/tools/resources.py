"""
MCP Resources — read-only data that gives context to LLMs.
Resources are application-driven (host decides when to include them).

NOTE: These resources use the default (global) database paths from settings.
When accessed via the MCP server directly (port 8000), data is shared across
all clients. The Chat API (port 8001) provides per-user data isolation through
a separate path — these resources are not used by the Chat API.
"""

import json

from tools import mcp
from utils.dotenv_config import settings


@mcp.resource("config://status")
def get_config_status() -> str:
    """Server configuration status — which services are available."""
    status = {
        "weather": bool(settings.OPENWEATHER_API_KEY),
        "news": bool(settings.NEWSAPI_KEY),
        "calendar_provider": settings.CALENDAR_PROVIDER or None,
        "notes": True,
        "tasks": True,
        "reminders": True,
        "time_tracking": True,
        "timezone": True,
        "temperature": True,
    }
    return json.dumps(status, indent=2)


@mcp.resource("notes://recent")
async def get_recent_notes() -> str:
    """Most recent 10 notes for context."""
    from tools.notes.schemas import SearchNotesInput
    from tools.notes.service import NotesService

    svc = NotesService()
    # Search with empty-ish query to get all, limited by results
    try:
        result = await svc.search_notes(SearchNotesInput(query=""))
        notes = [
            {"id": n.id, "content": n.content[:200], "tags": n.tags, "created_at": n.created_at}
            for n in result.notes[:10]
        ]
        return json.dumps(notes, indent=2)
    except Exception:
        return json.dumps([])


@mcp.resource("tasks://pending")
async def get_pending_tasks() -> str:
    """Current pending and in-progress tasks."""
    from tools.tasks.schemas import ListTasksInput, TaskStatus
    from tools.tasks.service import TasksService

    svc = TasksService()
    try:
        pending = await svc.list_tasks(ListTasksInput(status=TaskStatus.PENDING))
        in_progress = await svc.list_tasks(ListTasksInput(status=TaskStatus.IN_PROGRESS))
        tasks = [
            {"id": t.id, "title": t.title, "priority": t.priority, "status": t.status, "due_date": t.due_date, "project": t.project}
            for t in pending.tasks + in_progress.tasks
        ]
        return json.dumps(tasks, indent=2)
    except Exception:
        return json.dumps([])


@mcp.resource("reminders://pending")
async def get_pending_reminders() -> str:
    """Pending reminders that haven't fired yet."""
    from tools.reminders.service import RemindersService

    svc = RemindersService()
    try:
        result = await svc.list_reminders(include_fired=False)
        reminders = [
            {"id": r.id, "message": r.message, "remind_at": r.remind_at}
            for r in result.reminders
        ]
        return json.dumps(reminders, indent=2)
    except Exception:
        return json.dumps([])


@mcp.resource("timetracker://active")
async def get_active_timers() -> str:
    """Currently running time tracking entries."""
    import aiosqlite
    svc_path = settings.TIMETRACKER_DB_PATH
    try:
        async with aiosqlite.connect(svc_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT project, started_at FROM time_entries WHERE stopped_at IS NULL"
            )
            rows = await cursor.fetchall()
            active = [{"project": r["project"], "started_at": r["started_at"]} for r in rows]
            return json.dumps(active, indent=2)
    except Exception:
        return json.dumps([])
