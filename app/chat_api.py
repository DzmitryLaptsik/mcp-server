"""
Chat API server that bridges a React frontend with LLM (via OpenRouter) + MCP tools.
Connects to the MCP server as a client — all tool calls go through MCP protocol.

Requires: MCP server running on MCP_HOST:MCP_PORT (default 127.0.0.1:8000)
Run: uv run python chat_api.py
"""

import json
from contextlib import asynccontextmanager

import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from auth import get_user_by_api_key, login
from utils.dotenv_config import settings

SYSTEM_PROMPT = """You are a helpful personal assistant with access to various tools. Be concise and friendly.

IMPORTANT RULES for tool usage:
- When the user asks to SEE, SHOW, LIST, or CHECK existing data, ONLY use read tools (list_reminders, list_tasks, search_notes, get_time_summary). Do NOT create new items.
- ONLY use create/write tools (set_reminder, create_note, create_task, track_time, create_calendar_event) when the user EXPLICITLY asks to create, add, save, set, or start something NEW.
- If the user says "show me my reminders" or "what reminders do I have", call list_reminders. Do NOT call set_reminder.
- If the user says "show my notes" or "what did I write about X", call search_notes or list_notes. Do NOT call create_note.
- If the user says "show my tasks" or "what's on my todo list", call list_tasks. Do NOT call create_task.
- Never create duplicate items. If you already created something in this conversation, do not create it again.
- Use one tool at a time when possible. Do not call multiple tools unless the user's request genuinely requires combining data from different sources."""

# --- Tool metadata for frontend display ---

TOOL_META = {
    "convert_temperature": {"label": "Temperature Converter", "icon": "🌡️", "category": "Weather",      "template": "Convert {temperature} degrees {Celsius/Fahrenheit} to {Fahrenheit/Celsius}"},
    "get_weather":         {"label": "Current Weather",       "icon": "☀️", "category": "Weather",      "template": "What's the weather in {city}?"},
    "get_forecast":        {"label": "Weather Forecast",      "icon": "🌤️", "category": "Weather",      "template": "What's the forecast for {city} for the next {number} days?"},
    "get_world_time":      {"label": "World Clock",           "icon": "🕐", "category": "Time",         "template": "What time is it in {city/timezone}?"},
    "convert_timezone":    {"label": "Timezone Converter",    "icon": "🌍", "category": "Time",         "template": "Convert {time} from {source timezone} to {target timezone}"},
    "create_note":         {"label": "Create Note",           "icon": "📝", "category": "Notes",        "template": "Save a note: {your note text}"},
    "search_notes":        {"label": "Search Notes",          "icon": "🔍", "category": "Notes",        "template": "Search my notes for {keyword}"},
    "list_notes":          {"label": "All Notes",             "icon": "📒", "category": "Notes",        "template": "Show all my notes"},
    "create_task":         {"label": "Create Task",           "icon": "✅", "category": "Tasks",        "template": "Create a task: {title}, {priority} priority, due {date}"},
    "update_task":         {"label": "Update Task",           "icon": "✏️", "category": "Tasks",        "template": "Mark task {id} as done"},
    "delete_task":         {"label": "Delete Task",           "icon": "🗑️", "category": "Tasks",        "template": "Delete task {id}"},
    "list_tasks":          {"label": "List Tasks",            "icon": "📋", "category": "Tasks",        "template": "Show my {pending/overdue/all} tasks"},
    "track_time":          {"label": "Time Tracker",          "icon": "⏱️", "category": "Productivity", "template": "{Start/Stop} tracking time on {project name}"},
    "list_active_timers":  {"label": "Active Timers",         "icon": "🔄", "category": "Productivity", "template": "What timers are running?"},
    "list_time_entries":   {"label": "Time Log",              "icon": "📜", "category": "Productivity", "template": "Show my time tracking history"},
    "get_time_summary":    {"label": "Time Report",           "icon": "📊", "category": "Productivity", "template": "How much time did I spend this week?"},
    "set_reminder":        {"label": "Set Reminder",          "icon": "🔔", "category": "Productivity", "template": "Remind me to {task} in {minutes} minutes"},
    "list_reminders":      {"label": "List Reminders",        "icon": "📌", "category": "Productivity", "template": "Show my pending reminders"},
    "get_news":            {"label": "Latest News",           "icon": "📰", "category": "Information",  "template": "What's the latest news on {topic}?"},
    "create_calendar_event": {"label": "Create Event",       "icon": "📅", "category": "Calendar",     "template": "Schedule a meeting called {title} on {date} at {time}"},
    "list_calendar_events":  {"label": "List Events",        "icon": "🗓️", "category": "Calendar",     "template": "What events do I have from {start date} to {end date}?"},
    "find_free_slots":       {"label": "Find Free Slots",    "icon": "🕐", "category": "Calendar",     "template": "When can I meet with {email} this week?"},
    "summarize_day":         {"label": "Daily Briefing",     "icon": "☀️", "category": "Assistant",    "template": "Give me my daily briefing for today"},
    "plan_meeting":          {"label": "Plan Meeting",       "icon": "🤝", "category": "Assistant",    "template": "Plan a {duration}-minute meeting with {attendees} this week"},
}

# --- MCP Client ---

_mcp_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/mcp"
_tool_definitions: list[dict] = []  # Cached tool schemas from MCP server
_openai_tools: list[dict] = []      # OpenAI format for OpenRouter


async def _connect_mcp():
    """Connect to MCP server, fetch tool list, and cache definitions."""
    global _tool_definitions, _openai_tools

    async with streamablehttp_client(_mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()

    _tool_definitions = []
    _openai_tools = []

    for tool in tools_result.tools:
        schema = tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}}
        schema_dict = schema if isinstance(schema, dict) else schema.model_dump()
        schema_dict.pop("title", None)

        _tool_definitions.append({
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": schema_dict,
        })

        _openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema_dict,
            },
        })

    print(f"Connected to MCP server at {_mcp_url}")
    print(f"Loaded {len(_tool_definitions)} tools: {[t['name'] for t in _tool_definitions]}")


async def _call_mcp_tool(name: str, arguments: dict) -> str:
    """Call a tool on the MCP server via MCP protocol."""
    try:
        async with streamablehttp_client(_mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)

                if result.isError:
                    return json.dumps({"error": result.content[0].text if result.content else "Tool error"})

                # Extract text content from result
                texts = []
                for block in result.content:
                    if hasattr(block, "text"):
                        texts.append(block.text)

                combined = "\n".join(texts)

                # Try to parse as JSON, return as-is if valid
                try:
                    json.loads(combined)
                    return combined
                except json.JSONDecodeError:
                    return json.dumps({"result": combined})

    except Exception as e:
        print(f"[MCP TOOL ERROR] {name}: {type(e).__name__}: {e}")
        return json.dumps({"error": f"Tool '{name}' failed"})


# --- Auth helper ---

async def _get_user(request: Request) -> dict | None:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return await get_user_by_api_key(auth[7:])


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

MAX_REQUEST_SIZE = 512 * 1024

SIDE_EFFECT_TOOLS = {"create_note", "create_task", "set_reminder", "track_time", "create_calendar_event"}


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
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_SIZE:
                return JSONResponse({"error": "Request too large"}, status_code=413)
        except ValueError:
            return JSONResponse({"error": "Invalid Content-Length header"}, status_code=400)

    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model")

    if not messages:
        return JSONResponse({"error": "No messages provided"}, status_code=400)

    try:
        data = await _call_llm(messages, model=model)
    except httpx.HTTPStatusError as e:
        print(f"[LLM ERROR] {e.response.status_code}: {e.response.text[:200]}")
        return JSONResponse({"error": f"LLM request failed (status {e.response.status_code})"}, status_code=502)
    except Exception as e:
        print(f"[LLM ERROR] {type(e).__name__}: {e}")
        return JSONResponse({"error": "Failed to reach LLM provider"}, status_code=502)

    tool_calls_log = []
    choice = data["choices"][0]
    executed_tools = set()
    max_rounds = 5
    round_num = 0

    while choice["finish_reason"] == "tool_calls" and round_num < max_rounds:
        round_num += 1
        assistant_msg = choice["message"]
        messages.append(assistant_msg)

        for tool_call in assistant_msg.get("tool_calls", []):
            fn = tool_call["function"]
            tool_name = fn["name"]
            tool_args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]

            dedup_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"

            tool_calls_log.append({"tool": tool_name, "input": tool_args})

            if tool_name in SIDE_EFFECT_TOOLS and dedup_key in executed_tools:
                print(f"[DEDUP] Skipping duplicate call: {tool_name}")
                result_str = json.dumps({"note": "Already executed this exact call — skipped duplicate."})
            else:
                # Call tool via MCP protocol
                result_str = await _call_mcp_tool(tool_name, tool_args)
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
            return JSONResponse({"error": f"LLM request failed (status {e.response.status_code})"}, status_code=502)

        choice = data["choices"][0]

    text = choice["message"].get("content", "")

    return JSONResponse({
        "response": text,
        "tool_calls": tool_calls_log,
    })


async def list_tools(request: Request) -> JSONResponse:
    user = await _get_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

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


async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "mcp_url": _mcp_url, "tools_loaded": len(_tool_definitions)})


# --- App setup ---

@asynccontextmanager
async def lifespan(app):
    """Connect to MCP server on startup."""
    try:
        await _connect_mcp()
    except Exception as e:
        print(f"[WARNING] Could not connect to MCP server at {_mcp_url}: {e}")
        print("Chat API will start but tool calls will fail until MCP server is available.")
    yield


app = Starlette(
    routes=[
        Route("/api/auth/login", auth_login, methods=["POST"]),
        Route("/api/auth/me", auth_me, methods=["GET"]),
        Route("/api/chat", chat, methods=["POST"]),
        Route("/api/tools", list_tools, methods=["GET"]),
        Route("/api/health", health, methods=["GET"]),
    ],
    lifespan=lifespan,
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
    print(f"Chat API running on http://localhost:{settings.CHAT_API_PORT}")
    print(f"MCP server: {_mcp_url}")
    print(f"Model: {settings.OPENROUTER_MODEL} via OpenRouter")
    uvicorn.run(app, host="127.0.0.1", port=settings.CHAT_API_PORT)


if __name__ == "__main__":
    main()
