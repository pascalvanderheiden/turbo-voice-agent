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
    # Sandbox GitHub auth
    githubSandboxToken: str | None = Field(None, description="Encrypted GitHub token for CLI sandbox")
    githubSandboxConnectedAt: str | None = Field(None, description="ISO timestamp of sandbox token connection")
    # Sandbox config
    sandboxModel: str = Field("claude-sonnet-4", description="Default Copilot CLI model for sandbox")
    # Squad theme
    squadTheme: str = Field("Star Wars", description="Theme directive for squad/autopilot prompts")
