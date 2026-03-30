# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP (Model Context Protocol) server built with FastMCP and Python. A personal assistant platform with 19 AI-callable tools across weather, notes, tasks, time tracking, reminders, news, calendar, and timezone domains. Includes a React chat frontend backed by OpenRouter for multi-model LLM support.

## Commands

All backend commands should be run from the `app/` directory.

```bash
# Install dependencies
uv sync

# Run the MCP server (streamable-http transport on port 8000)
uv run main.py

# Run the Chat API backend (port 8001)
uv run python chat_api.py

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_weather.py

# Run a single test
uv run pytest tests/test_weather.py::test_get_weather_by_city_resolves_location_and_fetches_weather

# Docker (from app/ directory)
docker compose up

# MCP Inspector (dev tool for testing MCP servers)
mcp inspector
```

Frontend commands (from `frontend/` directory):

```bash
npm install
npm run dev          # Runs on http://localhost:3000
```

## Architecture

**Entry point**: `app/main.py` — imports `mcp` from `tools/` and runs it. No tool registration here.

**Chat API**: `app/chat_api.py` — FastAPI/Starlette server bridging React frontend with LLM (via OpenRouter) + MCP tools. Supports model switching, tool dedup for side-effect tools, and per-tool metadata (labels, icons, categories, templates).

**Tool auto-discovery**: `tools/__init__.py` owns the `FastMCP` instance and auto-imports all tool modules in the package via `pkgutil`. Adding a new tool = create a file in `tools/`, no other files need editing.

**Tool structure** — organized by domain, not by layer:
- **Simple tools** (single file): `tools/temperature.py`, `tools/timezone.py` — schema, logic, and `@mcp.tool()` in one file.
- **Complex tools** (sub-package): `tools/weather/`, `tools/notes/`, `tools/tasks/`, `tools/timetracker/`, `tools/reminders/`, `tools/news/`, `tools/calendar/`, `tools/assistant/` — split into `schemas.py`, `service.py`, `tool.py`.
- **Conditional tools**: `tools/calendar/` only registers if `CALENDAR_PROVIDER` is set.

**Config**: `utils/dotenv_config.py` — `pydantic-settings` `Settings` class with typed fields and defaults. Reads from `.env` file.

**Frontend**: `frontend/` — React + Vite chat UI with model selector, tools panel, and template prompts.

**Environment**: See `.env.example` for all settings. Key variables:
- `OPENWEATHER_API_KEY` — weather + forecast tools
- `NEWSAPI_KEY` — news tool
- `OPENROUTER_API_KEY` — chat API (LLM backend)
- `CALENDAR_PROVIDER` — `"google"` or `"outlook"` for calendar tools

## Tools

| Category | Tool | Type |
|----------|------|------|
| Weather | `get_weather`, `get_forecast`, `convert_temperature` | API / sync |
| Time | `get_world_time`, `convert_timezone` | sync (stdlib) |
| Notes | `create_note`, `search_notes` | SQLite |
| Tasks | `create_task`, `list_tasks` | SQLite |
| Productivity | `track_time`, `get_time_summary`, `set_reminder`, `list_reminders` | SQLite |
| Information | `get_news` | API |
| Calendar | `create_calendar_event`, `list_calendar_events`, `find_free_slots` | Google/Outlook API |
| Smart Assistant | `summarize_day`, `plan_meeting` | Chains other tools |

## Adding a New Tool

1. Create `tools/my_tool.py` (or `tools/my_tool/` for complex tools)
2. Import `mcp` from `tools` and use the `@mcp.tool()` decorator
3. Define Pydantic schemas in the same file (or `schemas.py` in the sub-package)
4. Add metadata to `TOOL_META` in `chat_api.py` (label, icon, category, template)
5. Done — auto-discovery handles MCP registration

## Testing

Tests use `pytest-asyncio` (auto mode) and `pytest-mock`. `conftest.py` provides fixtures that mock the `settings` object and `httpx.AsyncClient` so tests don't make real HTTP calls. Test deps are in the `[dependency-groups] dev` section of `pyproject.toml`.

63 tests covering all tools. Run with `uv run pytest` from `app/`.

See `ARCHITECTURE.md` for detailed architecture documentation including data flows and design decisions.
