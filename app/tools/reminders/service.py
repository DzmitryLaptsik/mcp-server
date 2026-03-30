from datetime import datetime, timedelta, timezone

import aiosqlite

from tools.reminders.schemas import ListRemindersOutput, ReminderResponse, SetReminderInput
from utils.dotenv_config import settings


class RemindersService:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.REMINDERS_DB_PATH

    async def _ensure_table(self, db: aiosqlite.Connection):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_fired INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.commit()

    async def set_reminder(self, input: SetReminderInput) -> ReminderResponse:
        now = datetime.now(timezone.utc)

        if input.remind_at:
            # Parse absolute time
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

        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
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
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            db.row_factory = aiosqlite.Row

            if include_fired:
                query = "SELECT * FROM reminders ORDER BY remind_at ASC"
                params = ()
            else:
                query = "SELECT * FROM reminders WHERE is_fired = 0 ORDER BY remind_at ASC"
                params = ()

            cursor = await db.execute(query, params)
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
