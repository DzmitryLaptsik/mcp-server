from typing import Optional

from pydantic import BaseModel, Field


class SetReminderInput(BaseModel):
    message: str = Field(..., max_length=1000, description="The reminder message")
    remind_at: Optional[str] = Field(None, description="Absolute time in ISO format (YYYY-MM-DDTHH:MM:SS) or YYYY-MM-DD HH:MM")
    remind_in_minutes: Optional[int] = Field(None, description="Relative offset: remind in N minutes from now")


class ReminderResponse(BaseModel):
    id: int
    message: str
    remind_at: str = Field(..., description="When the reminder is scheduled for (UTC)")
    created_at: str
    is_fired: bool = Field(False, description="Whether the reminder has already fired")


class ListRemindersOutput(BaseModel):
    reminders: list[ReminderResponse]
    total: int
