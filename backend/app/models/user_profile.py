"""User profile model."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    id: str = Field(..., description="Entra Object ID (oid)")
    userId: str = Field(..., description="Same as id, partition key")
    displayName: str = ""
    email: str = ""
    locale: str = "en"
    avatarUrl: str | None = None
    lastLoginAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
