# Calendar Integration Setup

This guide covers how to connect the MCP server to Google Calendar and Microsoft Outlook.

## Google Calendar

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Calendar API**:
   - Go to **APIs & Services > Library**
   - Search "Google Calendar API"
   - Click **Enable**

### Step 2: Create OAuth 2.0 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure the **OAuth consent screen**:
   - User type: **External** (or Internal for Google Workspace)
   - App name: "MCP Assistant"
   - Scopes: add `https://www.googleapis.com/auth/calendar`
   - Add your email as a test user
4. Back in Credentials, create OAuth client ID:
   - Application type: **Desktop app**
   - Name: "MCP Assistant"
5. Download the credentials — you'll need the **Client ID** and **Client Secret**

### Step 3: Configure `.env`

```env
CALENDAR_PROVIDER="google"
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
GOOGLE_TOKEN_PATH="google_token.json"
```

### Step 4: First Run — Authorization

1. Start the chat API: `uv run python chat_api.py`
2. On the first calendar tool call, a **browser window** will open
3. Sign in with your Google account and grant calendar access
4. The token is saved to `google_token.json` (auto-refreshes)
5. Subsequent runs use the saved token — no browser needed

### Troubleshooting

- **"Access blocked: This app's request is invalid"** — Make sure redirect URI `http://localhost` is in your OAuth client settings
- **"Token expired"** — Delete `google_token.json` and re-authorize
- **Scope warning** — App is in "testing" mode; add users in OAuth consent screen

---

## Microsoft Outlook / Office 365

### Step 1: Register an Azure AD App

1. Go to [Azure Portal > App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**:
   - Name: "MCP Assistant"
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
   - Redirect URI: leave empty (we use device code flow)
3. Note the **Application (client) ID** and **Directory (tenant) ID**

### Step 2: Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission > Microsoft Graph > Delegated permissions**
3. Add:
   - `Calendars.ReadWrite`
4. Click **Grant admin consent** (if you're an admin) or have users consent individually

### Step 3: Enable Public Client Flow

1. Go to **Authentication**
2. Under **Advanced settings**, set **Allow public client flows** to **Yes**
3. Save

### Step 4: Configure `.env`

```env
CALENDAR_PROVIDER="outlook"
MS_CLIENT_ID="your-application-client-id"
MS_TENANT_ID="common"
MS_TOKEN_CACHE_PATH="ms_token_cache.json"
```

> **Note**: `MS_CLIENT_SECRET` is optional for public client (device code) flow. Only needed if using confidential client flow.

### Step 5: First Run — Device Code Authorization

1. Start the chat API: `uv run python chat_api.py`
2. On the first calendar tool call, the console will show:
   ```
   To sign in to Microsoft, visit: https://microsoft.com/devicelogin
   Enter code: ABCD1234
   ```
3. Open that URL in a browser, enter the code, sign in
4. The token is cached to `ms_token_cache.json` (auto-refreshes)
5. Subsequent runs use the cached token

### Troubleshooting

- **"AADSTS65001: The user or administrator has not consented"** — Go to Azure Portal > API permissions > Grant admin consent
- **"AADSTS7000218: The request body must contain client_assertion or client_secret"** — Enable "Allow public client flows" in Authentication settings
- **Token expired** — Delete `ms_token_cache.json` and re-authorize
- **Personal vs Work accounts** — Use `MS_TENANT_ID="common"` to support both, or set a specific tenant ID for work-only

---

## What Happens After Setup

Once configured, three calendar tools become available:

| Tool | What it does |
|------|-------------|
| `create_calendar_event` | Create events with title, time, attendees, recurrence |
| `list_calendar_events` | List events in a date range |
| `find_free_slots` | Check availability across attendees (9am-6pm weekdays) |

The smart assistant tools also gain calendar awareness:
- `summarize_day` includes your calendar events in the daily briefing
- `plan_meeting` uses `find_free_slots` + timezone conversion to plan cross-timezone meetings

## Switching Providers

Change `CALENDAR_PROVIDER` in `.env` and restart. Only one provider can be active at a time.

```env
# Switch from Google to Outlook
CALENDAR_PROVIDER="outlook"
```

## Security Notes

- Token files (`google_token.json`, `ms_token_cache.json`) contain sensitive OAuth tokens
- They are excluded from git via `.gitignore`
- Store them securely; do not share or commit them
- Tokens grant full read/write access to the user's calendar
- To revoke access:
  - **Google**: [myaccount.google.com/permissions](https://myaccount.google.com/permissions)
  - **Microsoft**: [myapps.microsoft.com](https://myapps.microsoft.com)
