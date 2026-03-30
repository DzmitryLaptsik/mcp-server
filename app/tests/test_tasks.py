import pytest

from tools.tasks.schemas import (
    CreateTaskInput,
    ListTasksInput,
    ListTasksOutput,
    TaskPriority,
    TaskResponse,
    TaskStatus,
)
from tools.tasks.service import TasksService


@pytest.fixture
def tasks_service(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_tasks.db")
    monkeypatch.setattr("tools.tasks.service.settings.TASKS_DB_PATH", db_path)
    return TasksService()


async def test_create_task(tasks_service: TasksService):
    result = await tasks_service.create_task(
        CreateTaskInput(title="Update invoice template", priority=TaskPriority.HIGH, project="billing", due_date="2026-04-04")
    )
    assert isinstance(result, TaskResponse)
    assert result.id == 1
    assert result.title == "Update invoice template"
    assert result.priority == "high"
    assert result.status == "pending"
    assert result.project == "billing"
    assert result.due_date == "2026-04-04"


async def test_create_task_defaults(tasks_service: TasksService):
    result = await tasks_service.create_task(CreateTaskInput(title="Quick task"))
    assert result.priority == "medium"
    assert result.project is None
    assert result.due_date is None


async def test_list_tasks_no_filter(tasks_service: TasksService):
    await tasks_service.create_task(CreateTaskInput(title="Task 1"))
    await tasks_service.create_task(CreateTaskInput(title="Task 2"))

    result = await tasks_service.list_tasks(ListTasksInput())
    assert isinstance(result, ListTasksOutput)
    assert result.total == 2


async def test_list_tasks_filter_by_priority(tasks_service: TasksService):
    await tasks_service.create_task(CreateTaskInput(title="Low task", priority=TaskPriority.LOW))
    await tasks_service.create_task(CreateTaskInput(title="High task", priority=TaskPriority.HIGH))
    await tasks_service.create_task(CreateTaskInput(title="Another high", priority=TaskPriority.HIGH))

    result = await tasks_service.list_tasks(ListTasksInput(priority=TaskPriority.HIGH))
    assert result.total == 2
    assert all(t.priority == "high" for t in result.tasks)


async def test_list_tasks_filter_by_project(tasks_service: TasksService):
    await tasks_service.create_task(CreateTaskInput(title="Billing task", project="billing"))
    await tasks_service.create_task(CreateTaskInput(title="Frontend task", project="frontend"))

    result = await tasks_service.list_tasks(ListTasksInput(project="billing"))
    assert result.total == 1
    assert result.tasks[0].project == "billing"


async def test_list_tasks_overdue(tasks_service: TasksService):
    await tasks_service.create_task(CreateTaskInput(title="Overdue", due_date="2020-01-01"))
    await tasks_service.create_task(CreateTaskInput(title="Future", due_date="2030-12-31"))

    result = await tasks_service.list_tasks(ListTasksInput(overdue=True))
    assert result.total == 1
    assert result.tasks[0].title == "Overdue"
