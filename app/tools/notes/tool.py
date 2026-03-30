from tools import mcp
from tools.notes.schemas import CreateNoteInput, SearchNotesInput
from tools.notes.service import NotesService

_notes_service = None


def _get_notes_service() -> NotesService:
    global _notes_service
    if _notes_service is None:
        _notes_service = NotesService()
    return _notes_service


@mcp.tool(description="Save a note with optional tags for later retrieval. Use this to remember information, decisions, or anything the user wants to save.")
async def create_note(input: CreateNoteInput):
    return await _get_notes_service().create_note(input)


@mcp.tool(description="Search saved notes by keyword or phrase, optionally filtered by tag. Returns matching notes sorted by most recent.")
async def search_notes(input: SearchNotesInput):
    return await _get_notes_service().search_notes(input)
