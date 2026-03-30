from datetime import datetime, timedelta, timezone

import aiosqlite

from tools.timetracker.schemas import (
    ProjectTime,
    TimeSummaryInput,
    TimeSummaryOutput,
    TrackAction,
    TrackTimeInput,
    TrackTimeOutput,
)
from utils.dotenv_config import settings


def _format_duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


class TimeTrackerService:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.TIMETRACKER_DB_PATH

    async def _ensure_table(self, db: aiosqlite.Connection):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                started_at TEXT NOT NULL,
                stopped_at TEXT
            )
        """)
        await db.commit()

    async def track_time(self, input: TrackTimeInput) -> TrackTimeOutput:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            db.row_factory = aiosqlite.Row

            if input.action == TrackAction.START:
                # Check for already running timer on this project
                cursor = await db.execute(
                    "SELECT id FROM time_entries WHERE project = ? AND stopped_at IS NULL",
                    (input.project,),
                )
                existing = await cursor.fetchone()
                if existing:
                    return TrackTimeOutput(
                        action="start",
                        project=input.project,
                        message=f"Timer already running for '{input.project}'.",
                    )

                now = datetime.now(timezone.utc).isoformat()
                await db.execute(
                    "INSERT INTO time_entries (project, started_at) VALUES (?, ?)",
                    (input.project, now),
                )
                await db.commit()
                return TrackTimeOutput(
                    action="start",
                    project=input.project,
                    message=f"Started tracking time for '{input.project}'.",
                )

            else:  # STOP
                cursor = await db.execute(
                    "SELECT id, started_at FROM time_entries WHERE project = ? AND stopped_at IS NULL",
                    (input.project,),
                )
                row = await cursor.fetchone()
                if not row:
                    return TrackTimeOutput(
                        action="stop",
                        project=input.project,
                        message=f"No running timer found for '{input.project}'.",
                    )

                now = datetime.now(timezone.utc)
                started = datetime.fromisoformat(row["started_at"])
                duration_minutes = int((now - started).total_seconds() / 60)

                await db.execute(
                    "UPDATE time_entries SET stopped_at = ? WHERE id = ?",
                    (now.isoformat(), row["id"]),
                )
                await db.commit()

                return TrackTimeOutput(
                    action="stop",
                    project=input.project,
                    message=f"Stopped tracking '{input.project}'. Duration: {_format_duration(duration_minutes)}.",
                    duration=_format_duration(duration_minutes),
                )

    async def get_time_summary(self, input: TimeSummaryInput) -> TimeSummaryOutput:
        now = datetime.now(timezone.utc)

        if input.end_date:
            end = datetime.strptime(input.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            end = now

        if input.start_date:
            start = datetime.strptime(input.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            # Default to Monday of current week
            start = (end - timedelta(days=end.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                "SELECT project, started_at, stopped_at FROM time_entries WHERE started_at >= ? AND started_at <= ? AND stopped_at IS NOT NULL",
                (start.isoformat(), end.isoformat()),
            )
            rows = await cursor.fetchall()

            project_minutes: dict[str, int] = {}
            for row in rows:
                started = datetime.fromisoformat(row["started_at"])
                stopped = datetime.fromisoformat(row["stopped_at"])
                minutes = int((stopped - started).total_seconds() / 60)
                project_minutes[row["project"]] = project_minutes.get(row["project"], 0) + minutes

            projects = [
                ProjectTime(
                    project=name,
                    total_minutes=mins,
                    formatted=_format_duration(mins),
                )
                for name, mins in sorted(project_minutes.items(), key=lambda x: x[1], reverse=True)
            ]

            total = sum(p.total_minutes for p in projects)

            return TimeSummaryOutput(
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
                projects=projects,
                total_minutes=total,
                total_formatted=_format_duration(total),
            )
