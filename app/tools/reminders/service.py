from datetime import datetime, timedelta, timezone

import aiosqlite

from tools.reminders.schemas import ListRemindersOutput, ReminderResponse, SetReminderInput
from utils.db import ensure_table, get_db
from utils.dotenv_config import settings

CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        remind_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        is_fired INTEGER NOT NULL DEFAULT 0
    )
"""


class RemindersService:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.REMINDERS_DB_PATH

    async def set_reminder(self, input: SetReminderInput) -> ReminderResponse:
        now = datetime.now(timezone.utc)

        if input.remind_at:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    remind_at = datetime.strptime(input.remind_at, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Invalid remind_at format: '{input.remind_at}'. Use YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD HH:MM.")
        elif input.remind_in_minutes is not None:
            remind_at = now + timedelta(minutes=input.remind_in_minutes)
        else:
            raise ValueError("You must provide either 'remind_at' (absolute time) or 'remind_in_minutes' (relative offset).")

        async with get_db(self.db_path) as db:
            await ensure_table(db, self.db_path, CREATE_TABLE)
            cursor = await db.execute(
                "INSERT INTO reminders (message, remind_at, created_at) VALUES (?, ?, ?)",
                (input.message, remind_at.isoformat(), now.isoformat()),
            )
            await db.commit()
            return ReminderResponse(
                id=cursor.lastrowid,
                message=input.message,
                remind_at=remind_at.isoformat(),
                created_at=now.isoformat(),
                is_fired=False,
            )

    async def list_reminders(self, include_fired: bool = False) -> ListRemindersOutput:
        async with get_db(self.db_path) as db:
            await ensure_table(db, self.db_path, CREATE_TABLE)
            db.row_factory = aiosqlite.Row

            # Auto-mark expired reminders as fired
            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "UPDATE reminders SET is_fired = 1 WHERE is_fired = 0 AND remind_at < ?",
                (now,),
            )
            await db.commit()

            if include_fired:
                query = "SELECT * FROM reminders ORDER BY remind_at ASC LIMIT 100"
            else:
                query = "SELECT * FROM reminders WHERE is_fired = 0 ORDER BY remind_at ASC LIMIT 100"

            cursor = await db.execute(query)
            rows = await cursor.fetchall()

            reminders = [
                ReminderResponse(
                    id=row["id"],
                    message=row["message"],
                    remind_at=row["remind_at"],
                    created_at=row["created_at"],
                    is_fired=bool(row["is_fired"]),
                )
                for row in rows
            ]

            return ListRemindersOutput(reminders=reminders, total=len(reminders))
