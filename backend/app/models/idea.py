"""Idea Pydantic models for brainstorm service."""

from datetime import datetime

from pydantic import BaseModel, Field


class IdeaBase(BaseModel):
    """Shared fields for ideas."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="")
    images: list[str] = Field(default_factory=list)


class IdeaCreate(IdeaBase):
    """Request body for creating an idea."""

    pass


class IdeaUpdate(BaseModel):
    """Request body for updating an idea — all fields optional."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    images: list[str] | None = None


class Idea(IdeaBase):
    """API response model."""

    id: str
    status: str = "draft"  # draft | refined
    refined_draft: str | None = Field(None, alias="refinedDraft")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}
