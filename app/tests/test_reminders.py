import pytest

from tools.reminders.schemas import ListRemindersOutput, ReminderResponse, SetReminderInput
from tools.reminders.service import RemindersService


@pytest.fixture
def reminders_service(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_reminders.db")
    monkeypatch.setattr("tools.reminders.service.settings.REMINDERS_DB_PATH", db_path)
    return RemindersService()


async def test_set_reminder_absolute_time(reminders_service: RemindersService):
    result = await reminders_service.set_reminder(
        SetReminderInput(message="Call the client", remind_at="2026-04-01T15:00:00")
    )
    assert isinstance(result, ReminderResponse)
    assert result.id == 1
    assert result.message == "Call the client"
    assert "2026-04-01" in result.remind_at
    assert result.is_fired is False


async def test_set_reminder_short_format(reminders_service: RemindersService):
    result = await reminders_service.set_reminder(
        SetReminderInput(message="Check oven", remind_at="2026-04-01 15:00")
    )
    assert result.message == "Check oven"


async def test_set_reminder_relative_minutes(reminders_service: RemindersService):
    result = await reminders_service.set_reminder(
        SetReminderInput(message="Take a break", remind_in_minutes=45)
    )
    assert result.message == "Take a break"
    assert result.remind_at is not None


async def test_set_reminder_no_time_raises(reminders_service: RemindersService):
    with pytest.raises(ValueError, match="You must provide either"):
        await reminders_service.set_reminder(SetReminderInput(message="No time given"))


async def test_set_reminder_invalid_format_raises(reminders_service: RemindersService):
    with pytest.raises(ValueError, match="Invalid remind_at format"):
        await reminders_service.set_reminder(SetReminderInput(message="Bad", remind_at="next tuesday"))


async def test_list_reminders(reminders_service: RemindersService):
    await reminders_service.set_reminder(SetReminderInput(message="First", remind_in_minutes=10))
    await reminders_service.set_reminder(SetReminderInput(message="Second", remind_in_minutes=20))

    result = await reminders_service.list_reminders()
    assert isinstance(result, ListRemindersOutput)
    assert result.total == 2
    # Sorted by remind_at ascending
    assert result.reminders[0].message == "First"
    assert result.reminders[1].message == "Second"
