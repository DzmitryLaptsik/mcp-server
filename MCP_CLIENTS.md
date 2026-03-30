# Connecting MCP Clients

The MCP server runs on port 8000 with streamable HTTP transport. Any MCP-compatible client can connect to it directly — no frontend or chat API needed.

## Quick Start

```bash
cd app
uv run main.py
# MCP server running at http://localhost:8000/mcp
```

## Supported Clients

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "personal-assistant": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Restart Claude Desktop. The tools will appear automatically.

### Claude Code (CLI)

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "personal-assistant": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### MCP Inspector

Interactive testing tool — test tools directly in the browser:

```bash
cd app
mcp inspector
```

Then connect to `http://localhost:8000/mcp`.

### Cursor / Windsurf / Other IDEs

Most AI IDEs support MCP. Add the server URL in their MCP settings:

```
http://localhost:8000/mcp
```

### Python SDK Client

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # List available tools
        tools = await session.list_tools()
        for tool in tools.tools:
            print(f"  {tool.name}: {tool.description}")

        # Call a tool
        result = await session.call_tool("get_world_time", {"timezone": "Asia/Tokyo"})
        print(result)
```

## MCP Server vs Chat API

This project has two servers that serve different purposes:

| | MCP Server (port 8000) | Chat API (port 8001) |
|---|---|---|
| **Protocol** | MCP (streamable HTTP) | REST JSON |
| **Who uses it** | MCP clients (Claude Desktop, Cursor, etc.) | React chat frontend |
| **LLM included** | No — the client brings its own LLM | Yes — calls OpenRouter |
| **Auth** | None (single user) | API key per user |
| **User isolation** | No | Yes (per-user databases) |
| **Entry point** | `uv run main.py` | `uv run python chat_api.py` |

**MCP server** exposes raw tools. The client's LLM decides which tools to call and when.

**Chat API** is a convenience wrapper that adds LLM reasoning (via OpenRouter), multi-user auth, and per-user data isolation on top of the same tool services.

## Available Tools

When a client connects, it gets access to 19 tools (+ 3 calendar when configured):

**Weather**: `get_weather`, `get_forecast`, `convert_temperature`
**Time**: `get_world_time`, `convert_timezone`
**Notes**: `create_note`, `search_notes`, `list_notes`
**Tasks**: `create_task`, `list_tasks`
**Productivity**: `track_time`, `list_active_timers`, `list_time_entries`, `get_time_summary`, `set_reminder`, `list_reminders`
**Information**: `get_news`
**Calendar**: `create_calendar_event`, `list_calendar_events`, `find_free_slots` *(only if CALENDAR_PROVIDER is configured)*
**Smart Assistant**: `summarize_day`, `plan_meeting`

## Remote Access

To expose the MCP server beyond localhost, set in your `.env`:

```env
MCP_HOST="0.0.0.0"
```

Then clients on your network can connect via `http://<your-ip>:8000/mcp`.

> **Note**: The MCP server has no authentication. Only expose it on trusted networks.
