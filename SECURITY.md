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

### Data Isolation
- **Shared databases**: All tool calls (both MCP and Chat API) use shared global SQLite databases. There is no per-user data isolation at the storage level.
- **Chat API auth** protects endpoints but not data — authenticated users share the same notes, tasks, reminders, and time tracking data.
- **Resources expose global data**: `notes://recent`, `tasks://pending`, etc. are shared across all users.

**Why this is acceptable**: The Chat API connects to the MCP server as an MCP client — all tool calls go through the MCP protocol, which is the core value proposition. The MCP spec does not define per-user context for tool calls. For the hackathon, shared data demonstrates the architecture correctly. Per-user isolation would require a session-aware MCP extension (Phase 2).

### MCP Server Path
- **No authentication**: MCP protocol on port 8000 has no auth mechanism
- **Any local process** can connect and call tools

**Why this is acceptable**: MCP is designed for local, single-user clients (Claude Desktop, Cursor). The server binds to localhost only.

### Prompt Injection
- User messages are passed to the LLM with tool-calling enabled
- A crafted message could instruct the LLM to call tools with unintended arguments
- Side-effect dedup mitigates exact-duplicate calls but not varied arguments

## OWASP Top 10 Assessment

| OWASP | Status | Details |
|-------|--------|---------|
| **A01 Broken Access Control** | Partial | Auth on all Chat API endpoints. Data is shared (no per-user DB isolation) — all users see same notes/tasks. MCP path has no auth (localhost-only). |
| **A02 Cryptographic Failures** | Mitigated | API keys hashed with SHA-256, secrets in `.env` (gitignored), OAuth tokens excluded from git. Note: keys use unsalted hash (acceptable for high-entropy tokens). |
| **A03 Injection** | Mitigated | All SQL uses parameterized queries. No shell exec. Pydantic validates all inputs. react-markdown sanitizes HTML. |
| **A04 Insecure Design** | Partial | Tool dedup prevents duplicates. 5-round tool loop cap. Request size limit. Missing: rate limiting on LLM proxy. |
| **A05 Security Misconfiguration** | Mitigated | Localhost-only binding, CORS restricted, generic error messages. Docker volume mount is broad (dev convenience). |
| **A06 Vulnerable Components** | OK | Dependencies pinned via `uv.lock`. No known CVEs at time of audit. |
| **A07 Auth Failures** | Known limitation | Name-based auth is demo-grade (documented). Keys never expire. No rate limiting on login. |
| **A08 Data Integrity** | OK | No deserialization of untrusted data. Pydantic models for all inputs. |
| **A09 Logging & Monitoring** | Partial | Tool calls logged to stdout with user context. No structured audit log. |
| **A10 SSRF** | Low risk | API URLs configurable via env vars. Requires host access to exploit. |

## AI-Specific Security

| Concern | Status |
|---------|--------|
| **Prompt injection** | Mitigated with system prompt rules (READ/WRITE tool separation), but not fully preventable. LLM can still be tricked. |
| **Tool abuse** | Side-effect tools deduplicated. Destructive tools annotated with `destructiveHint=True`. 5-round cap on tool calls. |
| **Cost exhaustion** | No per-user rate limiting on LLM calls. Each request can trigger up to 5 LLM calls. |
| **Data exfiltration** | Per-user isolation prevents cross-user access. MCP path uses shared data (documented). |

## Hardening Roadmap

### Phase 1: Immediate (pre-production)
- [x] Hash API keys at rest (SHA-256) — **done**
- [x] Re-login invalidates old key — **done**
- [x] Parameterized SQL everywhere — **done**
- [x] Input validation with max_length — **done**
- [x] CORS restricted to localhost — **done**
- [x] Error messages sanitized — **done**
- [x] WAL mode + busy_timeout on all SQLite DBs — **done**
- [x] `/api/tools` requires authentication — **done**
- [ ] Add rate limiting on `/api/auth/login` and `/api/chat`
- [ ] Add API key expiry (e.g., 24 hours)
- [ ] Add Content-Security-Policy headers

### Phase 2: Multi-User Production
- [ ] Per-user data isolation via MCP session context or per-user MCP server instances
- [ ] Replace name-based auth with OAuth provider (Google, GitHub)
- [ ] Add salted hashing (bcrypt/argon2) for API keys
- [ ] Per-user calendar OAuth tokens
- [ ] Encrypt SQLite databases at rest
- [ ] Structured audit logging for tool invocations
- [ ] Add CSRF tokens on login endpoint
- [ ] Set restrictive file permissions on token files (0600)

### Phase 3: Enterprise
- [ ] Add MCP server authentication (token verification)
- [ ] Per-user data isolation on MCP path
- [ ] TLS termination (HTTPS)
- [ ] Secret management (vault, key rotation)
- [ ] SOC 2 / GDPR compliance (data retention, deletion, export)
- [ ] Tool confirmation UX for destructive operations

## Reporting Security Issues

If you discover a security vulnerability, please report it privately rather than opening a public issue.
