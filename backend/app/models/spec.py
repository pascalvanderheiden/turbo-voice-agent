"""Spec Pydantic models for spec service."""

from datetime import datetime

from pydantic import BaseModel, Field


class SpecBase(BaseModel):
    """Shared fields for specs."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="")
    type: str = Field(default="foundation")  # foundation | feature
    parent_id: str | None = Field(None, alias="parentId")
    idea_id: str | None = Field(None, alias="ideaId")


class SpecCreate(SpecBase):
    """Request body for creating a spec."""

    model_config = {"populate_by_name": True}


class SpecUpdate(BaseModel):
    """Request body for updating a spec — all fields optional."""

    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = None
    type: str | None = None
    parent_id: str | None = Field(None, alias="parentId")
    status: str | None = None

    model_config = {"populate_by_name": True}


class Spec(SpecBase):
    """API response model."""

    id: str
    status: str = "draft"  # draft | optimized | in-development | developed
    format_version: str = Field("v2", alias="formatVersion")  # v1 (legacy) | v2 (mockup + openspec)
    dev_task_id: str | None = Field(None, alias="devTaskId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}
