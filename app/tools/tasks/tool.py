from tools import mcp
from tools.tasks.schemas import CreateTaskInput, ListTasksInput
from tools.tasks.service import TasksService

_tasks_service = None


def _get_tasks_service() -> TasksService:
    global _tasks_service
    if _tasks_service is None:
        _tasks_service = TasksService()
    return _tasks_service


@mcp.tool(description="Create a new task with title, priority, optional project, and due date. Use for tracking to-dos and action items.")
async def create_task(input: CreateTaskInput):
    return await _get_tasks_service().create_task(input)


@mcp.tool(description="List tasks with optional filters: by status (pending/in_progress/done), priority (low/medium/high), project name, or overdue only.")
async def list_tasks(input: ListTasksInput):
    return await _get_tasks_service().list_tasks(input)
