from datetime import datetime, timezone

import aiosqlite

from tools.tasks.schemas import (
    CreateTaskInput,
    DeleteTaskInput,
    DeleteTaskOutput,
    ListTasksInput,
    ListTasksOutput,
    TaskResponse,
    UpdateTaskInput,
)
from utils.db import ensure_table, get_db
from utils.dotenv_config import settings

CREATE_TABLE = """
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
"""


class TasksService:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.TASKS_DB_PATH

    async def create_task(self, input: CreateTaskInput) -> TaskResponse:
        async with get_db(self.db_path) as db:
            await ensure_table(db, self.db_path, CREATE_TABLE)
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

    async def update_task(self, input: UpdateTaskInput) -> TaskResponse:
        async with get_db(self.db_path) as db:
            await ensure_table(db, self.db_path, CREATE_TABLE)
            db.row_factory = aiosqlite.Row

            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (input.id,))
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Task with id {input.id} not found.")

            updates = {}
            if input.status is not None:
                updates["status"] = input.status.value
            if input.priority is not None:
                updates["priority"] = input.priority.value
            if input.title is not None:
                updates["title"] = input.title
            if input.due_date is not None:
                updates["due_date"] = input.due_date

            if not updates:
                raise ValueError("No fields to update.")

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [input.id]
            await db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
            await db.commit()

            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (input.id,))
            row = await cursor.fetchone()

            return TaskResponse(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                priority=row["priority"],
                status=row["status"],
                project=row["project"],
                due_date=row["due_date"],
                created_at=row["created_at"],
            )

    async def delete_task(self, input: DeleteTaskInput) -> DeleteTaskOutput:
        async with get_db(self.db_path) as db:
            await ensure_table(db, self.db_path, CREATE_TABLE)
            cursor = await db.execute("DELETE FROM tasks WHERE id = ?", (input.id,))
            await db.commit()
            if cursor.rowcount == 0:
                return DeleteTaskOutput(id=input.id, deleted=False, message=f"Task {input.id} not found.")
            return DeleteTaskOutput(id=input.id, deleted=True, message=f"Task {input.id} deleted.")

    async def list_tasks(self, input: ListTasksInput) -> ListTasksOutput:
        async with get_db(self.db_path) as db:
            await ensure_table(db, self.db_path, CREATE_TABLE)
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
            query = f"SELECT * FROM tasks{where} ORDER BY created_at DESC LIMIT 100"

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
