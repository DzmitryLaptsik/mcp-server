from mcp.types import ToolAnnotations

from tools import mcp
from tools.notes.schemas import CreateNoteInput, ListNotesInput, NoteResponse, SearchNotesInput, SearchNotesOutput
from tools.notes.service import NotesService

_notes_service = None


def _get_notes_service() -> NotesService:
    global _notes_service
    if _notes_service is None:
        _notes_service = NotesService()
    return _notes_service


@mcp.tool(
    description="Create a NEW note. Only use when the user explicitly asks to save, create, or write a note. Do NOT use when the user asks to see, find, or search notes.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
)
async def create_note(input: CreateNoteInput) -> NoteResponse:
    return await _get_notes_service().create_note(input)


@mcp.tool(
    description="READ: Search existing notes by keyword or phrase, optionally filtered by tag. Use when the user asks to find or search for specific notes.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def search_notes(input: SearchNotesInput) -> SearchNotesOutput:
    return await _get_notes_service().search_notes(input)


@mcp.tool(
    description="READ: List all notes, most recent first. Use when the user asks to show, list, or see all their notes. Optionally filter by tag.",
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def list_notes(input: ListNotesInput) -> SearchNotesOutput:
    return await _get_notes_service().list_notes(input)
