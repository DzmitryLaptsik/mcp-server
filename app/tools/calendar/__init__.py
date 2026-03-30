from utils.dotenv_config import settings

# Only register calendar tools if a provider is configured
if settings.CALENDAR_PROVIDER:
    from tools.calendar.tool import (  # noqa: F401 — triggers @mcp.tool() registration
        create_calendar_event,
        find_free_slots,
        list_calendar_events,
    )
