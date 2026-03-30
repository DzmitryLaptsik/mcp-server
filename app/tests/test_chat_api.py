"""
Tests for the Chat API endpoints.
Tests auth enforcement, tool listing, and tool registry parity with MCP.
"""

import pytest
from unittest.mock import AsyncMock, patch

from starlette.testclient import TestClient

# Patch settings before importing chat_api
import utils.dotenv_config

@pytest.fixture(autouse=True)
def mock_chat_settings(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.dotenv_config.settings.USER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("utils.dotenv_config.settings.OPENROUTER_API_KEY", "mock_key")
    monkeypatch.setattr("utils.dotenv_config.settings.OPENWEATHER_API_KEY", "mock_weather_key")
    monkeypatch.setattr("utils.dotenv_config.settings.NEWSAPI_KEY", "mock_news_key")
    monkeypatch.setattr("utils.dotenv_config.settings.CALENDAR_PROVIDER", "")
    monkeypatch.setattr("tools.weather.service.settings.OPENWEATHER_API_KEY", "mock_weather_key")
    monkeypatch.setattr("tools.weather.service.settings.STATIC_GEO_URL", "https://mock.example.com/geo")
    monkeypatch.setattr("tools.weather.service.settings.STATIC_WEATHER_URL", "https://mock.example.com/weather")
    monkeypatch.setattr("tools.weather.service.settings.STATIC_FORECAST_URL", "https://mock.example.com/forecast")
    monkeypatch.setattr("tools.news.service.settings.NEWSAPI_KEY", "mock_news_key")
    monkeypatch.setattr("tools.news.service.settings.NEWSAPI_URL", "https://mock.example.com/news")


@pytest.fixture
def client():
    from chat_api import app
    return TestClient(app)


@pytest.fixture
async def api_key(tmp_path, monkeypatch):
    """Create a test user and return their API key."""
    monkeypatch.setattr("auth.settings.USER_DATA_DIR", str(tmp_path))
    from auth import login
    user = await login("TestUser")
    return user["api_key"]


# --- Auth endpoints ---

def test_login_success(client):
    res = client.post("/api/auth/login", json={"name": "Alice"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Alice"
    assert data["api_key"].startswith("mcp_")
    assert "user_id" in data


def test_login_empty_name(client):
    res = client.post("/api/auth/login", json={"name": ""})
    assert res.status_code == 400


def test_login_missing_name(client):
    res = client.post("/api/auth/login", json={})
    assert res.status_code == 400


def test_auth_me_valid(client):
    login_res = client.post("/api/auth/login", json={"name": "Bob"})
    key = login_res.json()["api_key"]

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {key}"})
    assert res.status_code == 200
    assert res.json()["name"] == "Bob"


def test_auth_me_invalid_key(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_key"})
    assert res.status_code == 401


def test_auth_me_no_header(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


# --- Chat endpoint auth ---

def test_chat_unauthorized(client):
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert res.status_code == 401


def test_chat_no_messages(client):
    login_res = client.post("/api/auth/login", json={"name": "Eve"})
    key = login_res.json()["api_key"]

    res = client.post(
        "/api/chat",
        json={"messages": []},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert res.status_code == 400


# --- Tools endpoint ---

def test_tools_list(client):
    # Force rebuild tool definitions
    from chat_api import _build_tool_definitions, _tool_definitions, _openai_tools
    _tool_definitions.clear()
    _openai_tools.clear()
    _build_tool_definitions()

    res = client.get("/api/tools")
    assert res.status_code == 200
    data = res.json()
    tools = data["tools"]
    assert len(tools) > 0

    # Every tool has required metadata fields
    for tool in tools:
        assert "name" in tool
        assert "label" in tool
        assert "icon" in tool
        assert "category" in tool
        assert "description" in tool
        assert "template" in tool


def test_tools_include_assistant(client):
    from chat_api import _build_tool_definitions, _tool_definitions, _openai_tools
    _tool_definitions.clear()
    _openai_tools.clear()
    _build_tool_definitions()

    res = client.get("/api/tools")
    tool_names = [t["name"] for t in res.json()["tools"]]
    assert "summarize_day" in tool_names
    assert "plan_meeting" in tool_names


# --- Health ---

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# --- Tool registry parity ---

def test_chat_tools_match_mcp_tools():
    """Verify that all MCP-registered tools have a corresponding chat API definition."""
    from tools import mcp as mcp_server
    from chat_api import _build_tool_definitions, _tool_definitions, _openai_tools

    _tool_definitions.clear()
    _openai_tools.clear()
    _build_tool_definitions()

    mcp_tool_names = set(mcp_server._tool_manager._tools.keys())
    chat_tool_names = set(t["name"] for t in _tool_definitions)

    # Calendar tools may differ (MCP has them if CALENDAR_PROVIDER is set globally,
    # chat API checks settings at build time). Exclude conditional calendar tools.
    calendar_tools = {"create_calendar_event", "list_calendar_events", "find_free_slots"}
    mcp_only = mcp_tool_names - chat_tool_names - calendar_tools
    chat_only = chat_tool_names - mcp_tool_names - calendar_tools

    assert mcp_only == set(), f"Tools in MCP but not in chat API: {mcp_only}"
    assert chat_only == set(), f"Tools in chat API but not in MCP: {chat_only}"
