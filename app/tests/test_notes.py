import os
import pytest

from tools.notes.schemas import CreateNoteInput, NoteResponse, SearchNotesInput, SearchNotesOutput
from tools.notes.service import NotesService


@pytest.fixture
def notes_service(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_notes.db")
    monkeypatch.setattr("tools.notes.service.settings.NOTES_DB_PATH", db_path)
    return NotesService()


async def test_create_note(notes_service: NotesService):
    result = await notes_service.create_note(
        CreateNoteInput(content="Client prefers blue color scheme", tags=["client", "design"])
    )
    assert isinstance(result, NoteResponse)
    assert result.id == 1
    assert result.content == "Client prefers blue color scheme"
    assert result.tags == ["client", "design"]
    assert result.created_at is not None


async def test_create_note_without_tags(notes_service: NotesService):
    result = await notes_service.create_note(
        CreateNoteInput(content="Just a quick note")
    )
    assert result.tags == []


async def test_search_notes_by_keyword(notes_service: NotesService):
    await notes_service.create_note(CreateNoteInput(content="API migration plan for Q2", tags=["api"]))
    await notes_service.create_note(CreateNoteInput(content="Budget is 5k for the redesign", tags=["budget"]))
    await notes_service.create_note(CreateNoteInput(content="API rate limits are 100/min", tags=["api"]))

    result = await notes_service.search_notes(SearchNotesInput(query="API"))
    assert isinstance(result, SearchNotesOutput)
    assert result.total == 2
    assert all("API" in note.content for note in result.notes)


async def test_search_notes_by_tag(notes_service: NotesService):
    await notes_service.create_note(CreateNoteInput(content="Design meeting notes", tags=["design"]))
    await notes_service.create_note(CreateNoteInput(content="Design system colors", tags=["design", "client"]))
    await notes_service.create_note(CreateNoteInput(content="Budget spreadsheet", tags=["budget"]))

    result = await notes_service.search_notes(SearchNotesInput(query="Design", tag="client"))
    assert result.total == 1
    assert result.notes[0].content == "Design system colors"


async def test_search_notes_no_results(notes_service: NotesService):
    await notes_service.create_note(CreateNoteInput(content="Something unrelated"))

    result = await notes_service.search_notes(SearchNotesInput(query="nonexistent"))
    assert result.total == 0
    assert result.notes == []


async def test_search_notes_returns_most_recent_first(notes_service: NotesService):
    await notes_service.create_note(CreateNoteInput(content="First note about testing"))
    await notes_service.create_note(CreateNoteInput(content="Second note about testing"))

    result = await notes_service.search_notes(SearchNotesInput(query="testing"))
    assert result.total == 2
    assert result.notes[0].id == 2  # most recent first
    assert result.notes[1].id == 1
