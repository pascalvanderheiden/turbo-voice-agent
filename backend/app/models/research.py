"""Research Pydantic models."""

from datetime import datetime

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A URL citation from web search results."""

    url: str
    title: str = ""


class ResearchCreate(BaseModel):
    """Request body for triggering research."""

    query: str = Field(..., min_length=1)
    mode: str = Field(default="web_search")  # web_search | deep_research
    idea_id: str | None = Field(None, alias="ideaId")

    model_config = {"populate_by_name": True}


class Research(BaseModel):
    """API response model."""

    id: str
    title: str
    query: str
    mode: str  # web_search | deep_research
    status: str = "pending"  # pending | completed | failed
    result: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    idea_id: str | None = Field(None, alias="ideaId")
    error: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}
