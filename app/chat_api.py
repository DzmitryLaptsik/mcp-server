"""
Chat API server that bridges a React frontend with LLM (via OpenRouter) + MCP tools.
Supports multi-user auth with per-user data isolation.

Run: uv run python chat_api.py
"""

import json
from typing import Any

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from auth import get_user_by_api_key, get_user_db_path, login
from utils.dotenv_config import settings

SYSTEM_PROMPT = "You are a helpful personal assistant. You have access to tools for weather, notes, tasks, time tracking, reminders, news, and timezone conversion. Use them to help the user. Be concise and friendly."

# --- Tool metadata: display names, icons, categories for the frontend ---

TOOL_META = {
    "convert_temperature": {"label": "Temperature Converter", "icon": "🌡️", "category": "Weather",      "template": "Convert {temperature} degrees {Celsius/Fahrenheit} to {Fahrenheit/Celsius}"},
    "get_weather":         {"label": "Current Weather",       "icon": "☀️", "category": "Weather",      "template": "What's the weather in {city}?"},
    "get_forecast":        {"label": "Weather Forecast",      "icon": "🌤️", "category": "Weather",      "template": "What's the forecast for {city} for the next {number} days?"},
    "get_world_time":      {"label": "World Clock",           "icon": "🕐", "category": "Time",         "template": "What time is it in {city/timezone}?"},
    "convert_timezone":    {"label": "Timezone Converter",    "icon": "🌍", "category": "Time",         "template": "Convert {time} from {source timezone} to {target timezone}"},
    "create_note":         {"label": "Create Note",           "icon": "📝", "category": "Notes",        "template": "Save a note: {your note text}"},
    "search_notes":        {"label": "Search Notes",          "icon": "🔍", "category": "Notes",        "template": "Search my notes for {keyword}"},
    "create_task":         {"label": "Create Task",           "icon": "✅", "category": "Tasks",        "template": "Create a task: {title}, {priority} priority, due {date}"},
    "list_tasks":          {"label": "List Tasks",            "icon": "📋", "category": "Tasks",        "template": "Show my {pending/overdue/all} tasks"},
    "track_time":          {"label": "Time Tracker",          "icon": "⏱️", "category": "Productivity", "template": "{Start/Stop} tracking time on {project name}"},
    "get_time_summary":    {"label": "Time Report",           "icon": "📊", "category": "Productivity", "template": "How much time did I spend this week?"},
    "set_reminder":        {"label": "Set Reminder",          "icon": "🔔", "category": "Productivity", "template": "Remind me to {task} in {minutes} minutes"},
    "list_reminders":      {"label": "List Reminders",        "icon": "📌", "category": "Productivity", "template": "Show my pending reminders"},
    "get_news":            {"label": "Latest News",           "icon": "📰", "category": "Information",  "template": "What's the latest news on {topic}?"},
}

# --- Tool definitions (shared across users, no state) ---

_tool_definitions: list[dict] = []
_openai_tools: list[dict] = []


def _build_tool_definitions():
    """Build tool definitions for the LLM. Called once at startup."""
    global _tool_definitions, _openai_tools

    from tools.temperature import TemperatureInput
    from tools.timezone import TimezoneConvertInput, WorldTimeInput
    from tools.weather.schemas import ForecastInput, WeatherInput
    from tools.notes.schemas import CreateNoteInput, SearchNotesInput
    from tools.tasks.schemas import CreateTaskInput, ListTasksInput
    from tools.timetracker.schemas import TimeSummaryInput, TrackTimeInput
    from tools.reminders.schemas import SetReminderInput
    from tools.news.schemas import NewsInput

    defs = [
        ("convert_temperature", "Converts temperatures between Celsius and Fahrenheit.", TemperatureInput),
        ("get_world_time", "Get the current time in any timezone.", WorldTimeInput),
        ("convert_timezone", "Convert a time from one timezone to one or more target timezones.", TimezoneConvertInput),
    ]

    if settings.OPENWEATHER_API_KEY:
        defs.append(("get_weather", "Get current weather for a location.", WeatherInput))
        defs.append(("get_forecast", "Get a multi-day weather forecast (1-5 days) for a location.", ForecastInput))

    defs += [
        ("create_note", "Save a note with optional tags for later retrieval.", CreateNoteInput),
        ("search_notes", "Search saved notes by keyword or phrase, optionally filtered by tag.", SearchNotesInput),
        ("create_task", "Create a new task with title, priority, optional project, and due date.", CreateTaskInput),
        ("list_tasks", "List tasks with optional filters: by status, priority, project, or overdue only.", ListTasksInput),
        ("track_time", "Start or stop tracking time on a project.", TrackTimeInput),
        ("get_time_summary", "Get a summary of tracked time by project for a date range.", TimeSummaryInput),
        ("set_reminder", "Set a reminder with a message at an absolute time or relative offset in minutes.", SetReminderInput),
        ("list_reminders", "List pending reminders.", None),
    ]

    if settings.NEWSAPI_KEY:
        defs.append(("get_news", "Get latest news articles on a topic.", NewsInput))

    for name, description, schema_cls in defs:
        if schema_cls:
            input_schema = schema_cls.model_json_schema()
        else:
            input_schema = {
                "type": "object",
                "properties": {
                    "include_fired": {"type": "boolean", "description": "Include already-fired reminders", "default": False}
                },
            }

        _tool_definitions.append({"name": name, "description": description, "input_schema": input_schema})

    # Convert to OpenAI format for OpenRouter
    for tool in _tool_definitions:
        schema = dict(tool["input_schema"])
        schema.pop("title", None)
        _openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": schema,
            },
        })


# --- Per-user tool handlers ---

def _build_user_handlers(user_id: str) -> dict[str, Any]:
    """Create tool handlers scoped to a specific user's data."""
    handlers: dict[str, Any] = {}

    # Stateless tools (no user data)
    from tools.temperature import TemperatureInput, convert_temperature
    from tools.timezone import TimezoneConvertInput, WorldTimeInput, convert_timezone, get_world_time

    handlers["convert_temperature"] = lambda args: convert_temperature(TemperatureInput(**args)).model_dump()
    handlers["get_world_time"] = lambda args: get_world_time(WorldTimeInput(**args)).model_dump()
    handlers["convert_timezone"] = lambda args: convert_timezone(TimezoneConvertInput(**args)).model_dump()

    # Weather (shared, no user data)
    if settings.OPENWEATHER_API_KEY:
        from tools.weather.schemas import ForecastInput, WeatherInput
        from tools.weather.service import WeatherService
        weather_svc = WeatherService()
        handlers["get_weather"] = lambda args, svc=weather_svc: _async_handler(svc.get_weather, WeatherInput(**args))
        handlers["get_forecast"] = lambda args, svc=weather_svc: _async_handler(svc.get_forecast, ForecastInput(**args))

    # User-scoped services with per-user DB paths
    from tools.notes.schemas import CreateNoteInput, SearchNotesInput
    from tools.notes.service import NotesService
    notes_svc = NotesService(db_path=get_user_db_path(user_id, "notes.db"))
    handlers["create_note"] = lambda args, svc=notes_svc: _async_handler(svc.create_note, CreateNoteInput(**args))
    handlers["search_notes"] = lambda args, svc=notes_svc: _async_handler(svc.search_notes, SearchNotesInput(**args))

    from tools.tasks.schemas import CreateTaskInput, ListTasksInput
    from tools.tasks.service import TasksService
    tasks_svc = TasksService(db_path=get_user_db_path(user_id, "tasks.db"))
    handlers["create_task"] = lambda args, svc=tasks_svc: _async_handler(svc.create_task, CreateTaskInput(**args))
    handlers["list_tasks"] = lambda args, svc=tasks_svc: _async_handler(svc.list_tasks, ListTasksInput(**args))

    from tools.timetracker.schemas import TimeSummaryInput, TrackTimeInput
    from tools.timetracker.service import TimeTrackerService
    tt_svc = TimeTrackerService(db_path=get_user_db_path(user_id, "timetracker.db"))
    handlers["track_time"] = lambda args, svc=tt_svc: _async_handler(svc.track_time, TrackTimeInput(**args))
    handlers["get_time_summary"] = lambda args, svc=tt_svc: _async_handler(svc.get_time_summary, TimeSummaryInput(**args))

    from tools.reminders.schemas import SetReminderInput
    from tools.reminders.service import RemindersService
    rem_svc = RemindersService(db_path=get_user_db_path(user_id, "reminders.db"))
    handlers["set_reminder"] = lambda args, svc=rem_svc: _async_handler(svc.set_reminder, SetReminderInput(**args))
    handlers["list_reminders"] = lambda args, svc=rem_svc: _async_handler(svc.list_reminders, args.get("include_fired", False))

    # News (shared, no user data)
    if settings.NEWSAPI_KEY:
        from tools.news.schemas import NewsInput
        from tools.news.service import NewsService
        news_svc = NewsService()
        handlers["get_news"] = lambda args, svc=news_svc: _async_handler(svc.get_news, NewsInput(**args))

    return handlers


# Simple in-memory cache for user handlers (avoid re-creating per request)
_user_handlers_cache: dict[str, dict[str, Any]] = {}


def _get_user_handlers(user_id: str) -> dict[str, Any]:
    if user_id not in _user_handlers_cache:
        _user_handlers_cache[user_id] = _build_user_handlers(user_id)
    return _user_handlers_cache[user_id]


async def _async_handler(method, input_data):
    result = await method(input_data)
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


async def _execute_tool(handlers: dict, name: str, args: dict) -> str:
    handler = handlers.get(name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        import asyncio
        result = handler(args)
        if asyncio.iscoroutine(result):
            result = await result
        return json.dumps(result, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        print(f"[TOOL ERROR] {name}: {type(e).__name__}: {e}")
        return json.dumps({"error": f"Tool '{name}' failed"})


# --- Auth helper ---

async def _get_user(request: Request) -> dict | None:
    """Extract user from Authorization header."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    api_key = auth[7:]
    return await get_user_by_api_key(api_key)


# --- OpenRouter API calls ---

async def _call_llm(messages: list[dict], model: str | None = None) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model or settings.OPENROUTER_MODEL,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                "tools": _openai_tools,
                "max_tokens": 4096,
            },
        )
        response.raise_for_status()
        return response.json()


# --- Endpoints ---

MAX_REQUEST_SIZE = 512 * 1024  # 512KB


async def auth_login(request: Request) -> JSONResponse:
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        return JSONResponse({"error": "Name is required"}, status_code=400)
    try:
        result = await login(name)
        return JSONResponse(result)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def auth_me(request: Request) -> JSONResponse:
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return JSONResponse(user)


async def chat(request: Request) -> JSONResponse:
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        return JSONResponse({"error": "Request too large"}, status_code=413)

    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model")

    if not messages:
        return JSONResponse({"error": "No messages provided"}, status_code=400)

    handlers = _get_user_handlers(user["user_id"])

    try:
        data = await _call_llm(messages, model=model)
    except httpx.HTTPStatusError as e:
        print(f"[LLM ERROR] {e.response.status_code}: {e.response.text[:200]}")
        return JSONResponse(
            {"error": f"LLM request failed (status {e.response.status_code})"},
            status_code=502,
        )
    except Exception as e:
        print(f"[LLM ERROR] {type(e).__name__}: {e}")
        return JSONResponse(
            {"error": "Failed to reach LLM provider"},
            status_code=502,
        )

    tool_calls_log = []
    choice = data["choices"][0]
    executed_tools = set()
    max_rounds = 5
    round_num = 0

    SIDE_EFFECT_TOOLS = {"create_note", "create_task", "set_reminder", "track_time"}

    while choice["finish_reason"] == "tool_calls" and round_num < max_rounds:
        round_num += 1
        assistant_msg = choice["message"]
        messages.append(assistant_msg)

        for tool_call in assistant_msg.get("tool_calls", []):
            fn = tool_call["function"]
            tool_name = fn["name"]
            tool_args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]

            dedup_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"

            tool_calls_log.append({
                "tool": tool_name,
                "input": tool_args,
            })

            if tool_name in SIDE_EFFECT_TOOLS and dedup_key in executed_tools:
                print(f"[DEDUP] Skipping duplicate call: {tool_name}")
                result_str = json.dumps({"note": "Already executed this exact call — skipped duplicate."})
            else:
                result_str = await _execute_tool(handlers, tool_name, tool_args)
                if tool_name in SIDE_EFFECT_TOOLS:
                    executed_tools.add(dedup_key)

            tool_calls_log[-1]["output"] = json.loads(result_str)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result_str,
            })

        print(f"[TOOL ROUND {round_num}] User={user['name']} Tools={[tc['tool'] for tc in tool_calls_log[-len(assistant_msg.get('tool_calls', [])):]]}]")

        try:
            data = await _call_llm(messages, model=model)
        except httpx.HTTPStatusError as e:
            return JSONResponse(
                {"error": f"LLM request failed (status {e.response.status_code})"},
                status_code=502,
            )

        choice = data["choices"][0]

    text = choice["message"].get("content", "")

    return JSONResponse({
        "response": text,
        "tool_calls": tool_calls_log,
    })


async def list_tools(request: Request) -> JSONResponse:
    tools = []
    for t in _tool_definitions:
        meta = TOOL_META.get(t["name"], {})
        tools.append({
            "name": t["name"],
            "label": meta.get("label", t["name"]),
            "icon": meta.get("icon", "🔧"),
            "category": meta.get("category", "Other"),
            "description": t["description"],
            "template": meta.get("template", ""),
        })
    return JSONResponse({"tools": tools})


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# --- App setup ---

app = Starlette(
    routes=[
        Route("/api/auth/login", auth_login, methods=["POST"]),
        Route("/api/auth/me", auth_me, methods=["GET"]),
        Route("/api/chat", chat, methods=["POST"]),
        Route("/api/tools", list_tools, methods=["GET"]),
        Route("/api/health", health, methods=["GET"]),
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


def main():
    import os
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is required. Set it in your .env file.")
    os.makedirs(settings.USER_DATA_DIR, exist_ok=True)
    _build_tool_definitions()
    print(f"Chat API running on http://localhost:{settings.CHAT_API_PORT}")
    print(f"Model: {settings.OPENROUTER_MODEL} via OpenRouter")
    print(f"User data: {os.path.abspath(settings.USER_DATA_DIR)}/")
    print(f"Available tools: {[t['name'] for t in _tool_definitions]}")
    uvicorn.run(app, host="127.0.0.1", port=settings.CHAT_API_PORT)


if __name__ == "__main__":
    main()
