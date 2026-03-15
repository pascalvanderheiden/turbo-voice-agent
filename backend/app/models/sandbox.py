"""Sandbox Pydantic models for per-user sandbox lifecycle and task execution."""

from datetime import datetime

from pydantic import BaseModel, Field


class SandboxConfig(BaseModel):
    """User's sandbox configuration."""

    model: str = "claude-sonnet-4"

    model_config = {"populate_by_name": True}


class SandboxState(BaseModel):
    """Per-user sandbox state stored in Cosmos DB."""

    id: str
    user_id: str = Field(alias="userId")
    status: str = "stopped"
    skills_hash: str | None = Field(None, alias="skillsHash")
    github_connected: bool = Field(False, alias="githubConnected")
    config: SandboxConfig = Field(default_factory=SandboxConfig)
    container_app_url: str | None = Field(None, alias="containerAppUrl")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class SandboxTask(BaseModel):
    """A task sent to the sandbox for execution."""

    id: str
    user_id: str = Field(alias="userId")
    dev_task_id: str = Field(alias="devTaskId")
    command: str
    args: list[str] = Field(default_factory=list)
    status: str = "pending"
    output: str = ""
    error: str | None = None
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(None, alias="completedAt")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class SandboxTaskCreate(BaseModel):
    """Request body for creating a sandbox task."""

    dev_task_id: str = Field(alias="devTaskId")
    command: str
    args: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
