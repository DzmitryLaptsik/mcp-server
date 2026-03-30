# Security Model

This document describes the security architecture, current protections, known limitations, and the hardening roadmap for the MCP Personal Productivity Server.

## Architecture Overview

The system has two access paths with different security characteristics:

```
┌──────────────────────────────────────────────────┐
│            MCP Server (port 8000)                 │
│  Local-only, single-user, no auth                 │
│  Binds to 127.0.0.1 by default                   │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│            Chat API (port 8001)                   │
│  Multi-user, API key auth, per-user isolation     │
│  Binds to 127.0.0.1 by default                   │
│  CORS restricted to localhost:3000                │
└──────────────────────────────────────────────────┘
```

## Current Protections

### Network Security
- Both servers bind to `127.0.0.1` by default — not accessible from the network
- CORS restricted to `http://localhost:3000` and `http://127.0.0.1:3000`
- Only `GET` and `POST` methods allowed; only `Content-Type` and `Authorization` headers

### Authentication (Chat API)
- API key auth via `Authorization: Bearer <key>` header
- Keys generated with `secrets.token_urlsafe(32)` (cryptographically secure, 256-bit entropy)
- Unauthenticated requests return `401 Unauthorized`
- Auth verified on every `/api/chat` and `/api/auth/me` request

### Data Isolation (Chat API)
- Each user gets a separate data directory: `data/{user_id}/`
- Separate SQLite databases per user: `notes.db`, `tasks.db`, `reminders.db`, `timetracker.db`
- User A cannot access User B's data — enforced at the storage layer
- Shared/stateless tools (weather, timezone, news) have no user data to isolate

### Input Validation
- All tool inputs validated via Pydantic schemas with typed fields
- Text fields have `max_length` constraints (notes: 10K, tasks: 500/5K, reminders: 1K)
- Request body size limited to 512KB
- `Content-Length` header validated before parsing
- Reminder minutes validated `>= 1` (prevents past-time scheduling)

### SQL Injection Prevention
- All SQLite queries use parameterized statements (`?` placeholders)
- No string interpolation in SQL construction
- Dynamic `WHERE` clauses in task listing use static condition strings with `?` params

### API Key Security
- OpenRouter, OpenWeather, and NewsAPI keys stored in `.env` (not committed to git)
- `.env` excluded via both root and `app/` `.gitignore` files
- OAuth tokens (`google_token.json`, `ms_token_cache.json`) excluded from git
- SQLite database files (`*.db`) excluded from git
- API keys never included in error responses sent to clients

### Error Handling
- Internal exceptions are caught and logged server-side
- Client receives generic error messages (no stack traces, no internal paths)
- `ValueError` exceptions (user input errors) are passed through with their message
- LLM API errors return status code only, not the full response body

### Tool Safety
- Side-effect tools (`create_note`, `create_task`, `set_reminder`, `track_time`, `create_calendar_event`) are deduplicated per request — prevents duplicate writes from LLM retry behavior
- Tool call loop capped at 5 rounds to prevent runaway LLM tool chains
- Tool annotations (`readOnlyHint`, `destructiveHint`) signal safety characteristics to MCP clients

## Known Limitations

### Authentication Model (Demo-Grade)
- **Identity is name-based**: entering a name creates or returns an account. No password required.
- **Deterministic user IDs**: same name always maps to the same user (case-insensitive)
- **API keys hashed at rest** (SHA-256) — raw key only visible on login, never stored
- **No session expiry**: API keys are valid indefinitely

**Why this is acceptable for the demo**: The system runs locally, behind `127.0.0.1`. Name-based login eliminates signup friction for live demos. The API key provides per-session isolation, not account security.

### MCP Server Path
- **No authentication**: MCP protocol on port 8000 has no auth mechanism
- **Shared data**: Notes, tasks, reminders use global database paths (not per-user)
- **Resources expose global data**: `notes://recent`, `tasks://pending`, etc. are shared

**Why this is acceptable**: MCP is designed for local, single-user clients (Claude Desktop, Cursor). The server binds to localhost only. The MCP spec does not define a standard auth mechanism for streamable HTTP transport.

### Prompt Injection
- User messages are passed to the LLM with tool-calling enabled
- A crafted message could instruct the LLM to call tools with unintended arguments
- Side-effect dedup mitigates exact-duplicate calls but not varied arguments

## Hardening Roadmap

### Phase 1: Immediate (pre-production)
- [x] Hash API keys at rest (store `sha256(key)`, compare on lookup) — **done**
- [x] Re-login invalidates old key and generates new one — **done**
- [ ] Add API key expiry (e.g., 30 days, auto-expire)
- [ ] Add rate limiting on `/api/chat` (e.g., 60 requests/min per user)
- [ ] Add rate limiting on external API calls (OpenWeather, NewsAPI)

### Phase 2: Multi-User Production
- [ ] Replace name-based auth with OAuth provider (Google, GitHub)
- [ ] Add password support or magic link login
- [ ] Encrypt SQLite databases at rest
- [ ] Add audit logging for tool invocations
- [ ] Add user consent for tool actions (confirmation before write operations)

### Phase 3: Enterprise
- [ ] Add MCP server authentication (token verification)
- [ ] Per-user data isolation on MCP path (via session/token context)
- [ ] TLS termination (HTTPS)
- [ ] Secret management (vault, environment-specific key rotation)
- [ ] SOC 2 / GDPR compliance (data retention, deletion, export)

## Reporting Security Issues

If you discover a security vulnerability, please report it privately rather than opening a public issue.
