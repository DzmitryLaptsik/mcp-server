"""
Simple API key auth for multi-user support.
Users register with a name, get an API key, and all their data is isolated.
"""

import hashlib
import os
import secrets
from datetime import datetime, timezone

import aiosqlite

from utils.dotenv_config import settings

AUTH_DB_PATH = os.path.join(settings.USER_DATA_DIR, "auth.db")


async def _ensure_table(db: aiosqlite.Connection):
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    await db.commit()


def _generate_user_id(name: str) -> str:
    """Deterministic short ID from name (lowercase, stripped)."""
    normalized = name.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def _generate_api_key() -> str:
    return f"mcp_{secrets.token_urlsafe(32)}"


async def login(name: str) -> dict:
    """Login or register a user by name. Returns user info + API key."""
    name = name.strip()
    if not name or len(name) > 100:
        raise ValueError("Name must be 1-100 characters.")

    user_id = _generate_user_id(name)

    async with aiosqlite.connect(AUTH_DB_PATH) as db:
        await _ensure_table(db)
        db.row_factory = aiosqlite.Row

        # Check if user exists
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()

        if user:
            return {
                "user_id": user["id"],
                "name": user["name"],
                "api_key": user["api_key"],
            }

        # Create new user
        api_key = _generate_api_key()
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO users (id, name, api_key, created_at) VALUES (?, ?, ?, ?)",
            (user_id, name, api_key, now),
        )
        await db.commit()

        # Create user data directory
        user_data_dir = get_user_data_dir(user_id)
        os.makedirs(user_data_dir, exist_ok=True)

        return {
            "user_id": user_id,
            "name": name,
            "api_key": api_key,
        }


async def get_user_by_api_key(api_key: str) -> dict | None:
    """Resolve an API key to a user. Returns None if invalid."""
    async with aiosqlite.connect(AUTH_DB_PATH) as db:
        await _ensure_table(db)
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
        user = await cursor.fetchone()

        if not user:
            return None

        return {
            "user_id": user["id"],
            "name": user["name"],
        }


def get_user_data_dir(user_id: str) -> str:
    """Return the data directory for a specific user."""
    return os.path.join(settings.USER_DATA_DIR, user_id)


def get_user_db_path(user_id: str, db_name: str) -> str:
    """Return the path to a user-specific database file."""
    user_dir = get_user_data_dir(user_id)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, db_name)
