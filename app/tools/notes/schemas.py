from typing import Optional

from pydantic import BaseModel, Field


class CreateNoteInput(BaseModel):
    content: str = Field(..., max_length=10000, description="The note content/text to save")
    tags: Optional[list[str]] = Field(None, description="Optional tags for categorization, e.g. ['client', 'design']")


class NoteResponse(BaseModel):
    id: int = Field(..., description="Unique note ID")
    content: str
    tags: list[str]
    created_at: str = Field(..., description="Timestamp when the note was created")


class SearchNotesInput(BaseModel):
    query: str = Field(..., max_length=500, description="Search keyword or phrase to find in notes")
    tag: Optional[str] = Field(None, description="Optional tag to filter notes by")


class ListNotesInput(BaseModel):
    tag: Optional[str] = Field(None, description="Optional tag to filter notes by")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of notes to return")


class SearchNotesOutput(BaseModel):
    notes: list[NoteResponse]
    total: int = Field(..., description="Total number of matching notes")
