"""
Tests for the Chat API endpoints.
Tests auth enforcement and tool listing.
"""

import pytest
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_chat_settings(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.dotenv_config.settings.USER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("utils.dotenv_config.settings.OPENROUTER_API_KEY", "mock_key")


@pytest.fixture
def client(monkeypatch):
    # Mock MCP connection so tests don't need a running MCP server
    import chat_api

    async def noop_connect():
        pass

    chat_api._connect_mcp = noop_connect
    return TestClient(chat_api.app)


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

def test_tools_unauthorized(client):
    res = client.get("/api/tools")
    assert res.status_code == 401


def test_tools_returns_list(client):
    """Tools endpoint returns a list (may be empty if MCP server not connected)."""
    login_res = client.post("/api/auth/login", json={"name": "ToolsUser"})
    key = login_res.json()["api_key"]

    res = client.get("/api/tools", headers={"Authorization": f"Bearer {key}"})
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)


# --- Health ---

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "mcp_url" in data
    assert "tools_loaded" in data
