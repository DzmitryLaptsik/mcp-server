from tools.assistant.tool import summarize_day  # noqa: F401 — triggers @mcp.tool() registration
from utils.dotenv_config import settings

# plan_meeting requires calendar provider — only register if configured
if settings.CALENDAR_PROVIDER:
    from tools.assistant.tool import plan_meeting  # noqa: F401
