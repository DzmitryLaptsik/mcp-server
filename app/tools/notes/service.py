import json
from datetime import datetime, timezone

import aiosqlite

from tools.notes.schemas import CreateNoteInput, ListNotesInput, NoteResponse, SearchNotesInput, SearchNotesOutput
from utils.dotenv_config import settings


class NotesService:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.NOTES_DB_PATH

    async def _ensure_table(self, db: aiosqlite.Connection):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()

    async def create_note(self, input: CreateNoteInput) -> NoteResponse:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            now = datetime.now(timezone.utc).isoformat()
            tags_json = json.dumps(input.tags or [])
            cursor = await db.execute(
                "INSERT INTO notes (content, tags, created_at) VALUES (?, ?, ?)",
                (input.content, tags_json, now),
            )
            await db.commit()
            return NoteResponse(
                id=cursor.lastrowid,
                content=input.content,
                tags=input.tags or [],
                created_at=now,
            )

    async def search_notes(self, input: SearchNotesInput) -> SearchNotesOutput:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            db.row_factory = aiosqlite.Row

            if input.tag:
                query = "SELECT * FROM notes WHERE content LIKE ? AND tags LIKE ? ORDER BY created_at DESC"
                params = (f"%{input.query}%", f"%\"{input.tag}\"%")
            else:
                query = "SELECT * FROM notes WHERE content LIKE ? ORDER BY created_at DESC"
                params = (f"%{input.query}%",)

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            notes = [
                NoteResponse(
                    id=row["id"],
                    content=row["content"],
                    tags=json.loads(row["tags"]),
                    created_at=row["created_at"],
                )
                for row in rows
            ]

            return SearchNotesOutput(notes=notes, total=len(notes))

    async def list_notes(self, input: ListNotesInput) -> SearchNotesOutput:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            db.row_factory = aiosqlite.Row

            if input.tag:
                query = "SELECT * FROM notes WHERE tags LIKE ? ORDER BY created_at DESC LIMIT ?"
                params = (f"%\"{input.tag}\"%", input.limit)
            else:
                query = "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?"
                params = (input.limit,)

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            notes = [
                NoteResponse(
                    id=row["id"],
                    content=row["content"],
                    tags=json.loads(row["tags"]),
                    created_at=row["created_at"],
                )
                for row in rows
            ]

            return SearchNotesOutput(notes=notes, total=len(notes))
