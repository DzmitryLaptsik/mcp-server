"""
Shared database utilities for SQLite services.
Handles WAL mode, busy timeout, and table initialization.
"""

from contextlib import asynccontextmanager

import aiosqlite

# Track which DB files have been initialized (table created)
_initialized_dbs: set[str] = set()


@asynccontextmanager
async def get_db(db_path: str):
    """Open a SQLite connection with WAL mode and busy timeout."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        yield db


async def ensure_table(db: aiosqlite.Connection, db_path: str, create_sql: str):
    """Create table if not exists, but only once per DB path per process."""
    if db_path not in _initialized_dbs:
        await db.execute(create_sql)
        await db.commit()
        _initialized_dbs.add(db_path)
