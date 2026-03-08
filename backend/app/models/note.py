"""Note Pydantic models — five-tier hierarchy."""

from datetime import datetime

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Shared fields for notes."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    images: list[str] = Field(default_factory=list)


class NoteCreate(NoteBase):
    """Request body for creating a note."""

    pass


class NoteUpdate(BaseModel):
    """Request body for updating a note — all fields optional."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)
    images: list[str] | None = None


class Note(NoteBase):
    """API response model."""

    id: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class NoteInDB(NoteBase):
    """Internal model matching Cosmos DB document shape."""

    id: str
    user_id: str = Field(alias="userId")
    doc_type: str = Field(default="note", alias="docType")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}
