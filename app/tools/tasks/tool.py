from mcp.types import ToolAnnotations

from tools import mcp
from tools.tasks.schemas import CreateTaskInput, ListTasksInput, ListTasksOutput, TaskResponse
from tools.tasks.service import TasksService

_tasks_service = None


def _get_tasks_service() -> TasksService:
    global _tasks_service
    if _tasks_service is None:
        _tasks_service = TasksService()
    return _tasks_service


@mcp.tool(
    description="Create a NEW task. Only use when the user explicitly asks to add, create, or make a task. Do NOT use when the user asks to see, list, or check tasks — use list_tasks instead.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_task(input: CreateTaskInput) -> TaskResponse:
    return await _get_tasks_service().create_task(input)


@mcp.tool(
    description="List existing tasks with optional filters by status, priority, project, or overdue. Use when the user asks to show, list, view, or check tasks.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_tasks(input: ListTasksInput) -> ListTasksOutput:
    return await _get_tasks_service().list_tasks(input)
