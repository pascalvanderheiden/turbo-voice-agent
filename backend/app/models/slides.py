"""Slides Pydantic models for presentation service."""

from datetime import datetime

from pydantic import BaseModel, Field


class SlideSection(BaseModel):
    """A single slide section in a presentation."""

    title: str = ""
    content: str = ""
    notes: str = ""
    image_url: str | None = Field(None, alias="imageUrl")

    model_config = {"populate_by_name": True}


class SlidesBase(BaseModel):
    """Shared fields for slide presentations."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="")
    sections: list[SlideSection] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    # Deck config fields (from create-deckio)
    subtitle: str = Field(default="")
    icon: str = Field(default="")
    theme: str = Field(default="shadcn/ui")
    appearance: str = Field(default="dark")
    palette: str = Field(default="arctic")


class SlidesCreate(SlidesBase):
    """Request body for creating a presentation."""

    pass


class SlidesUpdate(BaseModel):
    """Request body for updating a presentation — all fields optional."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    sections: list[SlideSection] | None = None
    attachments: list[str] | None = None
    subtitle: str | None = None
    icon: str | None = None
    theme: str | None = None
    appearance: str | None = None
    palette: str | None = None


class Slides(SlidesBase):
    """API response model."""

    id: str
    status: str = "draft"  # draft | refined
    refined_draft: str | None = Field(None, alias="refinedDraft")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}
