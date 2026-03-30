import os
import pytest

from auth import (
    _generate_user_id,
    _hash_api_key,
    get_user_by_api_key,
    get_user_data_dir,
    get_user_db_path,
    login,
)


@pytest.fixture(autouse=True)
def mock_auth_dir(tmp_path, monkeypatch):
    """Point auth DB and user data to a temp directory."""
    monkeypatch.setattr("auth.settings.USER_DATA_DIR", str(tmp_path))


# --- login ---

async def test_login_creates_new_user():
    result = await login("Alex")
    assert result["name"] == "Alex"
    assert result["user_id"] == _generate_user_id("Alex")
    assert result["api_key"].startswith("mcp_")


async def test_login_returns_same_user_with_new_key():
    first = await login("Alex")
    second = await login("Alex")
    assert first["user_id"] == second["user_id"]
    # Re-login generates a fresh key (old key is invalidated)
    assert first["api_key"] != second["api_key"]


async def test_relogin_invalidates_old_key():
    first = await login("Alex")
    old_key = first["api_key"]
    second = await login("Alex")

    # Old key should no longer work
    assert await get_user_by_api_key(old_key) is None
    # New key works
    assert await get_user_by_api_key(second["api_key"]) is not None


async def test_login_is_case_insensitive():
    lower = await login("alex")
    upper = await login("ALEX")
    assert lower["user_id"] == upper["user_id"]


async def test_login_strips_whitespace():
    result = await login("  Alex  ")
    assert result["name"] == "Alex"


async def test_login_different_users_get_different_keys():
    alex = await login("Alex")
    maria = await login("Maria")
    assert alex["user_id"] != maria["user_id"]
    assert alex["api_key"] != maria["api_key"]


async def test_login_empty_name_raises():
    with pytest.raises(ValueError, match="Name must be 1-100 characters"):
        await login("")


async def test_login_whitespace_only_raises():
    with pytest.raises(ValueError, match="Name must be 1-100 characters"):
        await login("   ")


async def test_login_too_long_name_raises():
    with pytest.raises(ValueError, match="Name must be 1-100 characters"):
        await login("x" * 101)


# --- API key hashing ---

async def test_api_key_not_stored_in_plaintext(tmp_path):
    """Verify that the raw API key is not in the database."""
    result = await login("Alex")
    raw_key = result["api_key"]

    import aiosqlite
    db_path = os.path.join(str(tmp_path), "auth.db")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (result["user_id"],))
        row = await cursor.fetchone()

    # DB stores hash, not raw key
    assert row["api_key_hash"] != raw_key
    assert row["api_key_hash"] == _hash_api_key(raw_key)


# --- get_user_by_api_key ---

async def test_get_user_by_valid_key():
    created = await login("Alex")
    user = await get_user_by_api_key(created["api_key"])
    assert user is not None
    assert user["user_id"] == created["user_id"]
    assert user["name"] == "Alex"


async def test_get_user_by_invalid_key():
    user = await get_user_by_api_key("mcp_nonexistent_key_12345")
    assert user is None


async def test_get_user_by_empty_key():
    user = await get_user_by_api_key("")
    assert user is None


# --- user data isolation ---

async def test_login_creates_user_data_dir(tmp_path):
    result = await login("Alex")
    user_dir = os.path.join(str(tmp_path), result["user_id"])
    assert os.path.isdir(user_dir)


def test_get_user_db_path_creates_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("auth.settings.USER_DATA_DIR", str(tmp_path))
    path = get_user_db_path("test_user_123", "notes.db")
    assert path.endswith("test_user_123/notes.db")
    assert os.path.isdir(os.path.dirname(path))


def test_user_id_is_deterministic():
    assert _generate_user_id("Alex") == _generate_user_id("Alex")
    assert _generate_user_id("Alex") == _generate_user_id("alex")
    assert _generate_user_id("Alex") != _generate_user_id("Maria")
