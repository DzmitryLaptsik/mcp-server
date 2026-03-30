# Architecture Description

## 1. Project Overview

**MCP Personal Assistant Server** is a Python-based [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk). It exposes 19+ AI-callable tools over a streamable HTTP transport, covering weather, notes, tasks, time tracking, reminders, news, calendar integration, and smart assistant capabilities. A React chat frontend with multi-model LLM support is included.

- **Language**: Python 3.11+
- **Package manager**: [UV](https://docs.astral.sh/uv/)
- **Transport**: Streamable HTTP (port 8000)
- **Chat API**: Starlette + OpenRouter (port 8001)
- **Frontend**: React + Vite (port 3000)
- **Storage**: SQLite via aiosqlite (notes, tasks, time tracking, reminders)
- **External APIs**: OpenWeatherMap, NewsAPI, Google Calendar, Microsoft Graph

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         React Chat Frontend                          │
│                        (frontend/ — port 3000)                       │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  /api/chat, /api/tools
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      Chat API (chat_api.py)                          │
│                   Starlette + OpenRouter — port 8001                 │
│                                                                      │
│  • Multi-model LLM support (Claude, GPT, Gemini, Llama, DeepSeek)   │
│  • Tool execution loop with dedup for side-effect tools              │
│  • Tool metadata (labels, icons, categories, templates)              │
└────────────────────────────┬─────────────────────────────────────────┘
                             │  Direct service calls
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     FastMCP Server (tools/__init__.py)                │
│                    Streamable HTTP — port 8000                       │
│                                                                      │
│  Auto-discovered tools:                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │ weather/      │ │ notes/       │ │ tasks/       │ │ timezone   │ │
│  │ • get_weather │ │ • create     │ │ • create     │ │ • world    │ │
│  │ • forecast    │ │ • search     │ │ • list       │ │ • convert  │ │
│  ├──────────────┤ ├──────────────┤ ├──────────────┤ ├────────────┤ │
│  │ timetracker/  │ │ reminders/   │ │ news/        │ │ calendar/  │ │
│  │ • track_time  │ │ • set        │ │ • get_news   │ │ • create   │ │
│  │ • summary     │ │ • list       │ │              │ │ • list     │ │
│  ├──────────────┤ ├──────────────┤ │              │ │ • free     │ │
│  │ assistant/    │ │ temperature  │ │              │ │            │ │
│  │ • summarize   │ │ • convert    │ │              │ │ Google /   │ │
│  │ • plan_mtg    │ │              │ │              │ │ Outlook    │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
└───────┬──────────────────┬──────────────────┬────────────────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
  ┌───────────┐    ┌──────────────┐    ┌──────────────┐
  │ SQLite DBs│    │ OpenWeather  │    │ Google Cal / │
  │ notes.db  │    │ NewsAPI      │    │ MS Graph API │
  │ tasks.db  │    │ OpenRouter   │    │              │
  │ time.db   │    │              │    │              │
  │ remind.db │    │              │    │              │
  └───────────┘    └──────────────┘    └──────────────┘
```

---

## 3. Project Structure

```
app/
├── main.py                         # MCP server entry point
├── chat_api.py                     # Chat API — LLM + tool execution + metadata
├── auth.py                         # User auth (hashed API keys, per-user data)
├── tools/
│   ├── __init__.py                 # FastMCP instance + auto-discovery
│   ├── temperature.py              # Simple: Celsius ↔ Fahrenheit
│   ├── timezone.py                 # Simple: world clock + timezone conversion
│   ├── weather/                    # Complex: current weather + forecast
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tool.py
│   ├── notes/                      # Complex: SQLite-backed notes
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tool.py
│   ├── tasks/                      # Complex: SQLite-backed task management
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tool.py
│   ├── timetracker/                # Complex: start/stop time tracking
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tool.py
│   ├── reminders/                  # Complex: timed reminders
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tool.py
│   ├── news/                       # Complex: NewsAPI integration
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── tool.py
│   ├── calendar/                   # Complex: Google Calendar + Outlook
│   │   ├── __init__.py             # Conditional registration
│   │   ├── schemas.py
│   │   ├── base.py                 # CalendarProvider protocol
│   │   ├── google_calendar.py
│   │   ├── outlook_calendar.py
│   │   └── tool.py                 # Provider factory + tools
│   └── assistant/                  # Smart: chains other tools
│       ├── __init__.py
│       ├── schemas.py
│       ├── service.py
│       └── tool.py
├── utils/
│   └── dotenv_config.py            # pydantic-settings configuration
├── tests/
│   ├── conftest.py                 # Shared fixtures
│   ├── test_temperature.py         # 4 tests
│   ├── test_timezone.py            # 6 tests
│   ├── test_weather.py             # 6 tests
│   ├── test_forecast.py            # 4 tests
│   ├── test_notes.py               # 6 tests
│   ├── test_tasks.py               # 6 tests
│   ├── test_timetracker.py         # 6 tests
│   ├── test_reminders.py           # 6 tests
│   ├── test_news.py                # 3 tests
│   ├── test_calendar_google.py     # 4 tests
│   ├── test_calendar_outlook.py    # 4 tests
│   ├── test_assistant.py           # 9 tests
│   ├── test_auth.py               # 16 tests
│   └── test_chat_api.py           # 12 tests — 92 total
├── pyproject.toml
├── Dockerfile
├── docker-compose.yaml
├── .env.example
└── .dockerignore

frontend/
├── index.html
├── vite.config.js                  # Dev server (port 3000) + API proxy
├── package.json
└── src/
    ├── main.jsx
    ├── index.css
    ├── App.jsx                     # Chat UI + model selector + tools panel
    └── App.css
```

---

## 4. Tool Auto-Discovery

`tools/__init__.py` is the core of the architecture:

```python
mcp = FastMCP(...)

for module_info in pkgutil.iter_modules(__path__):
    importlib.import_module(f".{module_info.name}", __package__)
```

When `main.py` does `from tools import mcp`, this triggers auto-import of every module and sub-package under `tools/`. Each module that uses `@mcp.tool()` self-registers. **No manual registration in main.py is needed.**

### Adding a new tool

**Simple tool** (no external I/O, fits in one file):
```
tools/my_tool.py
```

**Complex tool** (external APIs, needs service layer):
```
tools/my_tool/
├── __init__.py      # imports tool.py to trigger registration
├── schemas.py       # Pydantic input/output models
├── service.py       # Business logic, API calls
└── tool.py          # @mcp.tool() + service wiring
```

**Chat API metadata** — add to `TOOL_META` in `chat_api.py`:
```python
"my_tool": {"label": "My Tool", "icon": "🔧", "category": "Category", "template": "Do {something}"}
```

---

## 5. Tool Categories

### 5.1 Weather (`tools/weather/`, `tools/temperature.py`)

- `get_weather` — current weather by city or lat/lon via OpenWeatherMap
- `get_forecast` — 1-5 day forecast with daily aggregation (min/max temp, rain chance)
- `convert_temperature` — Celsius ↔ Fahrenheit (sync, pure math)

### 5.2 Time (`tools/timezone.py`)

- `get_world_time` — current time in any IANA timezone (stdlib `zoneinfo`)
- `convert_timezone` — convert time across multiple timezones

### 5.3 Notes (`tools/notes/`)

- `create_note` — save text with optional tags to SQLite
- `search_notes` — keyword search with optional tag filter
- `list_notes` — list all notes, most recent first, optional tag filter

### 5.4 Tasks (`tools/tasks/`)

- `create_task` — title, description, priority, project, due date
- `list_tasks` — filter by status, priority, project, or overdue

### 5.5 Time Tracking (`tools/timetracker/`)

- `track_time` — start/stop timer on a project, logs duration
- `list_active_timers` — show currently running timers
- `list_time_entries` — show individual session history with start/stop times
- `get_time_summary` — aggregated per-project time breakdown for a date range

### 5.6 Reminders (`tools/reminders/`)

- `set_reminder` — absolute time or relative offset (N minutes from now)
- `list_reminders` — pending reminders, optionally include fired

### 5.7 News (`tools/news/`)

- `get_news` — search articles by topic via NewsAPI.org

### 5.8 Calendar (`tools/calendar/`)

Pluggable backend architecture with `CalendarProvider` protocol:

- `create_calendar_event` — with attendees, recurrence support
- `list_calendar_events` — events in a date range
- `find_free_slots` — availability check across attendees (9am-6pm weekdays)

**Backends**: `GoogleCalendarProvider` (OAuth 2.0 + google-api-python-client), `OutlookCalendarProvider` (MSAL + Microsoft Graph API). Selected via `CALENDAR_PROVIDER` env var. Conditional registration — tools don't appear if no provider is configured.

### 5.9 Smart Assistant (`tools/assistant/`)

Chaining tools that combine multiple services:

- `summarize_day` — daily briefing: calendar events + tasks due + weather + news headlines
- `plan_meeting` — find free slots across timezones, optionally auto-book

---

## 6. Chat API (`chat_api.py`)

The chat API bridges the React frontend with LLM providers via OpenRouter:

**Endpoints**:
- `POST /api/auth/login` — register/login by name, returns API key
- `GET /api/auth/me` — verify API key, returns user info
- `POST /api/chat` — send messages, get response with tool calls (requires auth)
- `GET /api/tools` — list tools with metadata (label, icon, category, template)
- `GET /api/health` — health check

**Key features**:
- **Multi-model**: Frontend sends `model` field, backend passes to OpenRouter. Supports Claude, GPT, Gemini, Llama, DeepSeek, etc.
- **Tool execution loop**: Calls LLM → executes tool calls → feeds results back → repeats until text response. Max 5 rounds.
- **Side-effect dedup**: Tools like `create_note`, `set_reminder` are tracked — identical duplicate calls within a request are skipped.
- **Tool metadata**: `TOOL_META` dict provides display names, emoji icons, categories, and template prompts for the frontend.

---

## 7. Data Tenancy Model

The project has two access paths with different data isolation behavior:

```
┌─────────────────────────────────────────────────────────────────┐
│                   MCP Server (port 8000)                        │
│  • Single-user / shared data                                    │
│  • Tools read/write to default DB paths (notes.db, tasks.db)   │
│  • Resources expose global data                                 │
│  • No authentication                                            │
│  • Designed for: local MCP clients (Claude Desktop, Cursor)     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Chat API (port 8001)                           │
│  • Multi-user / per-user data isolation                         │
│  • Each user gets own DB files in data/{user_id}/               │
│  • API key auth (Bearer token)                                  │
│  • Designed for: React frontend, multi-user demos               │
└─────────────────────────────────────────────────────────────────┘
```

**Why two modes?** The MCP protocol is designed for local, single-user clients (your IDE, your desktop app). The chat API adds multi-user support for the web frontend. Both paths use the same tool services — the difference is how DB paths are resolved.

**Shared tools** (same behavior in both paths): weather, forecast, temperature, timezone, news — these are stateless or use external APIs.

**User-scoped tools** (isolated in chat API, global in MCP): notes, tasks, reminders, time tracking — these read/write SQLite databases.

**Calendar tools**: use provider-level auth (Google/Outlook OAuth), shared across paths.

---

## 8. Frontend (`frontend/`)

React + Vite single-page chat application:

- **Model selector**: Dropdown to switch LLM models mid-conversation
- **Tools panel**: Clickable badge showing all connected tools grouped by category with icons and descriptions
- **Template prompts**: Clicking a tool inserts a template (e.g. "What's the weather in {city}?") with auto-selected placeholder
- **Tool call display**: Expandable cards showing tool input/output per message
- **Suggestion chips**: Quick-start prompts on the welcome screen

Vite dev server proxies `/api` to the chat API backend (port 8001).

---

## 9. Testing Architecture

92 tests across 14 test files:

```
tests/
├── conftest.py                # Shared fixtures (mock settings, httpx)
├── test_temperature.py        #  4 tests — pure unit tests
├── test_timezone.py           #  6 tests — stdlib, no mocks
├── test_weather.py            #  6 tests — mocked httpx for OpenWeather
├── test_forecast.py           #  4 tests — mocked httpx for forecast
├── test_notes.py              #  6 tests — tmp_path SQLite DB
├── test_tasks.py              #  6 tests — tmp_path SQLite DB
├── test_timetracker.py        #  6 tests — tmp_path SQLite DB
├── test_reminders.py          #  6 tests — tmp_path SQLite DB
├── test_news.py               #  3 tests — mocked httpx for NewsAPI
├── test_calendar_google.py    #  4 tests — mocked Google API service
├── test_calendar_outlook.py   #  4 tests — mocked httpx for MS Graph
├── test_assistant.py          #  9 tests — mocked sub-services
├── test_auth.py               # 16 tests — auth, login, API key hashing
└── test_chat_api.py           # 12 tests — endpoints, auth, tool parity
```

**Patterns**:
- API tools: mock `httpx.AsyncClient` via `pytest-mock`, build real `httpx.Response` objects
- SQLite tools: use `tmp_path` fixture for isolated DB per test
- Calendar: mock auth + API service objects
- Assistant: mock individual service classes to test chaining logic
- All tests import service/schema layers directly — test real logic, not wrappers

---

## 10. Infrastructure

### Docker

- **Base image**: `python:3.12-slim-bookworm` with UV from `ghcr.io/astral-sh/uv:latest`
- **Production build**: `uv sync --no-dev` — test deps excluded
- **docker-compose**: mounts `.:/app` for live reload, passes `.env` via `env_file`

### Dependencies

**Production**:
- `httpx` — async HTTP client
- `mcp[cli]` — MCP framework + CLI tools
- `aiosqlite` — async SQLite for notes, tasks, time tracking, reminders
- `google-api-python-client`, `google-auth-oauthlib` — Google Calendar
- `msal` — Microsoft authentication
- `uvicorn` — ASGI server for chat API

**Dev only**:
- `pytest`, `pytest-asyncio`, `pytest-mock`

**Frontend**:
- `react`, `react-dom` — UI framework
- `vite`, `@vitejs/plugin-react` — build tool
