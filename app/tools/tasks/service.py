from datetime import datetime, timezone

import aiosqlite

from tools.tasks.schemas import CreateTaskInput, ListTasksInput, ListTasksOutput, TaskResponse
from utils.dotenv_config import settings


class TasksService:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.TASKS_DB_PATH

    async def _ensure_table(self, db: aiosqlite.Connection):
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'pending',
                project TEXT,
                due_date TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()

    async def create_task(self, input: CreateTaskInput) -> TaskResponse:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            now = datetime.now(timezone.utc).isoformat()
            cursor = await db.execute(
                "INSERT INTO tasks (title, description, priority, status, project, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (input.title, input.description, input.priority.value, "pending", input.project, input.due_date, now),
            )
            await db.commit()
            return TaskResponse(
                id=cursor.lastrowid,
                title=input.title,
                description=input.description,
                priority=input.priority.value,
                status="pending",
                project=input.project,
                due_date=input.due_date,
                created_at=now,
            )

    async def list_tasks(self, input: ListTasksInput) -> ListTasksOutput:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_table(db)
            db.row_factory = aiosqlite.Row

            conditions = []
            params = []

            if input.status:
                conditions.append("status = ?")
                params.append(input.status.value)

            if input.priority:
                conditions.append("priority = ?")
                params.append(input.priority.value)

            if input.project:
                conditions.append("project = ?")
                params.append(input.project)

            if input.overdue:
                conditions.append("due_date < ? AND status != 'done'")
                params.append(datetime.now(timezone.utc).strftime("%Y-%m-%d"))

            where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f"SELECT * FROM tasks{where} ORDER BY created_at DESC"

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

            tasks = [
                TaskResponse(
                    id=row["id"],
                    title=row["title"],
                    description=row["description"],
                    priority=row["priority"],
                    status=row["status"],
                    project=row["project"],
                    due_date=row["due_date"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

            return ListTasksOutput(tasks=tasks, total=len(tasks))
