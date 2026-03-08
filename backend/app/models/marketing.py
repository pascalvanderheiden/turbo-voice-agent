"""Marketing Video Pydantic models."""

from datetime import datetime

from pydantic import BaseModel, Field


class MarketingVideoCreate(BaseModel):
    """Request body for creating a marketing video."""

    title: str = Field(..., min_length=1)
    dev_task_id: str = Field(..., alias="devTaskId")

    model_config = {"populate_by_name": True}


class MarketingVideo(BaseModel):
    """API response model for a marketing video."""

    id: str
    title: str
    dev_task_id: str | None = Field(None, alias="devTaskId")
    spec_id: str | None = Field(None, alias="specId")
    status: str = "pending"  # pending | scripting | generating | composing | completed | failed
    video_path: str | None = Field(None, alias="videoPath")
    video_url: str | None = Field(None, alias="videoUrl")
    script_content: str | None = Field(None, alias="scriptContent")
    duration_seconds: int | None = Field(None, alias="durationSeconds")
    error: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}
