from mcp.types import ToolAnnotations

from tools import mcp
from tools.tasks.schemas import (
    CreateTaskInput,
    DeleteTaskInput,
    DeleteTaskOutput,
    ListTasksInput,
    ListTasksOutput,
    TaskResponse,
    UpdateTaskInput,
)
from tools.tasks.service import TasksService

_tasks_service = None


def _get_tasks_service() -> TasksService:
    global _tasks_service
    if _tasks_service is None:
        _tasks_service = TasksService()
    return _tasks_service


@mcp.tool(
    description="WRITE: Create a NEW task. Only use when the user explicitly asks to add or create a task.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_task(input: CreateTaskInput) -> TaskResponse:
    return await _get_tasks_service().create_task(input)


@mcp.tool(
    description="WRITE: Update an existing task (change status to done/in_progress, change priority, title, or due date). Use when user asks to complete, update, or modify a task.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def update_task(input: UpdateTaskInput) -> TaskResponse:
    return await _get_tasks_service().update_task(input)


@mcp.tool(
    description="WRITE: Delete a task by ID. Only use when user explicitly asks to delete or remove a task.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True),
)
async def delete_task(input: DeleteTaskInput) -> DeleteTaskOutput:
    return await _get_tasks_service().delete_task(input)


@mcp.tool(
    description="READ: List existing tasks with optional filters by status, priority, project, or overdue. Use when user asks to show, list, or check tasks.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_tasks(input: ListTasksInput) -> ListTasksOutput:
    return await _get_tasks_service().list_tasks(input)
