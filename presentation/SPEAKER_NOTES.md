# Speaker Notes — MCP Assistant Presentation

Total time: ~3 minutes (20 seconds per slide average)

---

## Slide 1: Title (15 sec)

> "Hi everyone. We built MCP Assistant — a personal productivity server that exposes 19+ AI-callable tools through the Model Context Protocol. It has a React chat frontend, supports multiple LLM models, and provides per-user data isolation. Let me walk you through it."

---

## Slide 2: What is MCP Assistant? (25 sec)

> "MCP is an open protocol that lets AI models call external tools. Our server implements 19 tools across 7 domains — weather, notes, tasks, time tracking, reminders, news, and calendar."

> "The system has two access paths. The MCP server on port 8000 works with any MCP client — Claude Desktop, Cursor, any IDE. The Chat API on port 8001 adds multi-user auth and powers our React frontend. Both paths use the same tool services."

---

## Slide 3: 19+ Tools (25 sec)

> "Here are all the tools grouped by category. Weather tools call OpenWeather API. Time tools use Python stdlib. Notes, tasks, reminders, and time tracking all persist to SQLite — each user gets their own database."

> "The smart assistant tool, summarize_day, chains multiple tools together — it pulls calendar events, tasks due, weather, and news into one daily briefing. We also have MCP Resources and Prompts for richer client integration."

---

## Slide 4: Architecture (25 sec)

> "The architecture has three layers. The React frontend talks to our Chat API, which calls OpenRouter for LLM reasoning. The LLM decides which tools to call, the Chat API executes them, and returns the result."

> "Key design decisions: tool auto-discovery means adding a new tool is one file — no registration needed. Data tenancy is split — the MCP path uses shared storage for local clients, the Chat API gives each user their own isolated database."

---

## Slide 5: UI — Login & Welcome (20 sec)

> "The UI starts with a simple name-based login. After logging in, users see a personalized welcome screen with suggestion chips they can click to try common workflows instantly. The interface supports both dark and light themes."

---

## Slide 6: UI — Chat & Tool Calls (25 sec)

> "Here's the chat in action. The user asks about weather — the LLM calls get_weather, and the response is rendered with markdown formatting. Notice the tool call badge below — you can expand it to see the exact input and output."

> "The second screenshot shows task creation — multi-turn conversation with tool execution visible. The tools panel on the right shows all connected tools grouped by category with descriptions."

---

## Slide 7: Tech Stack (20 sec)

> "Quick numbers: 19+ tools, 8 LLM models via OpenRouter, 101 tests, 7 tool domains. Backend is Python with FastMCP and Starlette. Frontend is React 19 with Vite. Storage is aiosqlite with WAL mode for concurrent access. All tests run in under 2 seconds."

---

## Slide 8: Security & OWASP (25 sec)

> "Security was a priority from day one. On the left — what we implemented: per-user database isolation, hashed API keys, parameterized SQL everywhere, Pydantic validation on all inputs, localhost-only binding, and restricted CORS."

> "On the right — AI-specific safety. We separate READ and WRITE tools in the system prompt so the LLM doesn't accidentally create data when asked to view. Side-effect dedup prevents duplicate writes. We assessed all OWASP Top 10 categories and documented a 3-phase hardening roadmap in SECURITY.md."

---

## Slide 9: Thank You (10 sec)

> "That's MCP Assistant. Happy to do a live demo or take questions. The MCP server runs on 8000, Chat API on 8001, frontend on 3000 — all running right now if you'd like to try it."

---

## Tips

- **If a demo question comes up**: Switch to the browser and show it live
- **If asked about production readiness**: "We have a clear hardening roadmap — Phase 1 is rate limiting and key expiry, Phase 2 is OAuth login, Phase 3 is enterprise features. The architecture supports it."
- **If asked about calendar**: "The code supports Google Calendar and Outlook — it's behind a feature flag. We focused on the tools that work out of the box for the demo."
- **If asked about model quality**: "Different models have different tool-calling reliability. Claude Sonnet 4 is the most reliable. We support 8 models so users can compare."
