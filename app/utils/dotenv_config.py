from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    OPENWEATHER_API_KEY: str = ""
    STATIC_GEO_URL: str = "https://api.openweathermap.org/geo/1.0/direct"
    STATIC_WEATHER_URL: str = "https://api.openweathermap.org/data/2.5/weather"
    STATIC_FORECAST_URL: str = "https://api.openweathermap.org/data/2.5/forecast"
    NOTES_DB_PATH: str = "notes.db"
    TASKS_DB_PATH: str = "tasks.db"
    TIMETRACKER_DB_PATH: str = "timetracker.db"
    REMINDERS_DB_PATH: str = "reminders.db"
    NEWSAPI_KEY: str = ""
    NEWSAPI_URL: str = "https://newsapi.org/v2/everything"
    CALENDAR_PROVIDER: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_TOKEN_PATH: str = "google_token.json"
    MS_CLIENT_ID: str = ""
    MS_CLIENT_SECRET: str = ""
    MS_TENANT_ID: str = "common"
    MS_TOKEN_CACHE_PATH: str = "ms_token_cache.json"
    MS_GRAPH_URL: str = "https://graph.microsoft.com/v1.0"
    USER_DATA_DIR: str = "data"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "anthropic/claude-sonnet-4"
    CHAT_API_PORT: int = 8001
    MCP_HOST: str = "127.0.0.1"
    MCP_PORT: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()
