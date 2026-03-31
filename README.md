# MCP Personal Assistant Server

A full-featured [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server with 19+ AI-callable tools and a React chat frontend. Built with FastMCP, Python, and OpenRouter for multi-model LLM support.

## Features

**21 tools across 8 categories (+ 3 calendar when configured):**

| Category | Tools |
|----------|-------|
| Weather | Current weather, 5-day forecast, temperature conversion |
| Time | World clock, timezone converter |
| Notes | Create, list, and search notes with tags |
| Tasks | Create, update, delete, list tasks with priority and due dates |
| Productivity | Time tracking (start/stop, history, active timers, summaries), reminders |
| Information | News search |
| Calendar | Google Calendar + Outlook integration (create, list, find free slots) |
| Smart Assistant | Daily briefing, cross-timezone meeting planner |

**Chat frontend with:**
- Multi-model switching (Claude, GPT, Gemini, Llama, DeepSeek)
- Tools panel with categories, descriptions, and click-to-insert templates
- Tool call visualization (expandable input/output per call)

## Quick Start

### Prerequisites

- Python 3.11+
- [UV](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for frontend)

### 1. Install dependencies

```bash
# Backend
cd app
uv sync

# Frontend
cd ../frontend
npm install
```

### 2. Configure environment

```bash
cp app/.env.example app/.env
```

Edit `app/.env` and set your API keys:

```env
# Required for chat frontend
OPENROUTER_API_KEY="sk-or-..."

# Required for weather tools
OPENWEATHER_API_KEY="..."

# Optional: news tool
NEWSAPI_KEY="..."

# Optional: calendar (set to "google" or "outlook")
CALENDAR_PROVIDER=""
```

### 3. Run

```bash
# Terminal 1 — MCP server (port 8000)
cd app
uv run main.py

# Terminal 2 — Chat API backend (port 8001)
cd app
uv run python chat_api.py

# Terminal 3 — React frontend (port 3000)
cd frontend
npm run dev
```

Open **http://localhost:3000** to use the chat interface.

### Alternative: MCP Inspector

Test tools directly without the chat frontend:

```bash
cd app
mcp inspector
```

### Alternative: Docker

```bash
cd app
docker compose up
```

## Project Structure

```
mcp-server/
├── app/                        # Backend
│   ├── main.py                 # MCP server entry point
│   ├── chat_api.py             # Chat API (LLM + tools + metadata)
│   ├── auth.py                 # User auth (hashed API keys, per-user data)
│   ├── tools/                  # 21 tools (+ 3 calendar when configured)
│   │   ├── temperature.py      # Simple tool (single file)
│   │   ├── timezone.py         # Simple tool (single file)
│   │   ├── weather/            # Complex tool (sub-package)
│   │   ├── notes/              # SQLite-backed
│   │   ├── tasks/              # SQLite-backed
│   │   ├── timetracker/        # SQLite-backed
│   │   ├── reminders/          # SQLite-backed
│   │   ├── news/               # NewsAPI integration
│   │   ├── calendar/           # Google + Outlook backends
│   │   ├── assistant/          # Chains other tools
│   │   ├── resources.py        # MCP Resources (read-only context)
│   │   └── prompts.py          # MCP Prompts (workflow templates)
│   ├── utils/dotenv_config.py  # Settings (pydantic-settings)
│   └── tests/                  # 101 tests
├── frontend/                   # React + Vite chat UI
├── ARCHITECTURE.md             # Detailed architecture docs
├── SECURITY.md                 # Security model and roadmap
├── MCP_CLIENTS.md              # How to connect MCP clients
├── CALENDAR_SETUP.md           # Google + Outlook setup guide
└── CLAUDE.md                   # Claude Code instructions
```

## Adding a New Tool

1. Create `app/tools/my_tool.py` (or `app/tools/my_tool/` for complex tools)
2. Import `mcp` from `tools` and use `@mcp.tool()` decorator
3. Define Pydantic schemas for input/output
4. Add metadata to `TOOL_META` in `chat_api.py` (label, icon, category, template)
5. Done — auto-discovery handles registration

## Tests

```bash
cd app
uv run pytest        # 101 tests, all tools covered
uv run pytest -v     # Verbose output
```

## Tech Stack

- **Backend**: Python 3.11+, FastMCP, Starlette, aiosqlite, httpx
- **Frontend**: React, Vite, react-markdown
- **LLM**: OpenRouter (Claude, GPT, Gemini, Llama, DeepSeek)
- **APIs**: OpenWeatherMap, NewsAPI, Google Calendar, Microsoft Graph
- **Testing**: pytest, pytest-asyncio, pytest-mock
