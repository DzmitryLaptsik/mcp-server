from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class CreateTaskInput(BaseModel):
    title: str = Field(..., max_length=500, description="Task title")
    description: Optional[str] = Field(None, max_length=5000, description="Task description or details")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority: low, medium, or high")
    project: Optional[str] = Field(None, description="Project name the task belongs to")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format")


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    priority: str
    status: str
    project: Optional[str]
    due_date: Optional[str]
    created_at: str


class ListTasksInput(BaseModel):
    status: Optional[TaskStatus] = Field(None, description="Filter by status: pending, in_progress, or done")
    priority: Optional[TaskPriority] = Field(None, description="Filter by priority: low, medium, or high")
    project: Optional[str] = Field(None, description="Filter by project name")
    overdue: Optional[bool] = Field(None, description="If true, show only overdue tasks (past due_date and not done)")


class ListTasksOutput(BaseModel):
    tasks: list[TaskResponse]
    total: int
