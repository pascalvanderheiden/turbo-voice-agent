"""Development Task Pydantic models."""

from datetime import datetime

from pydantic import BaseModel, Field


class DevArtifact(BaseModel):
    """An artifact produced during pipeline execution."""

    name: str
    type: str  # screenshot | archive
    data: str | None = None  # base64 for screenshots, path for archives
    iteration_index: int | None = Field(None, alias="iterationIndex")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class DevStage(BaseModel):
    """A single pipeline stage."""

    name: str  # plan | build | run | test
    status: str = "pending"  # pending | running | completed | failed
    output: str | None = None
    error: str | None = None
    started_at: str | None = Field(None, alias="startedAt")
    completed_at: str | None = Field(None, alias="completedAt")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class DevIteration(BaseModel):
    """A single development iteration (foundation or feature)."""

    iteration_index: int = Field(alias="iterationIndex")
    label: str  # e.g. "Foundation: Dark Cyberpunk" or "Feature: Combat System"
    spec_part_id: str | None = Field(None, alias="specPartId")
    stages: list[DevStage] = Field(default_factory=list)
    workspace_path: str | None = Field(None, alias="workspacePath")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class DevTaskCreate(BaseModel):
    """Request body for creating a development task."""

    title: str = Field(..., min_length=1)
    spec_id: str | None = Field(None, alias="specId")
    slides_id: str | None = Field(None, alias="slidesId")
    mode: str = "mockup"  # mockup | openspec | slides
    skill_ids: list[str] = Field(default_factory=list, alias="skillIds")

    model_config = {"populate_by_name": True}


class DevDecision(BaseModel):
    """A decision made automatically by the agent during pipeline execution."""

    question: str
    answer: str
    stage: str
    timestamp: str

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class SquadMember(BaseModel):
    """A member of the squad team assigned to a dev task."""

    name: str
    role: str
    expertise: str = ""
    status: str = "idle"  # idle | working | done

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class SquadInfo(BaseModel):
    """Squad metadata for a dev task."""

    team_members: list[SquadMember] = Field(default_factory=list, alias="teamMembers")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class OpenSpecStatus(BaseModel):
    """Status of the OpenSpec change being applied."""

    change_name: str = Field("", alias="changeName")
    total_tasks: int = Field(0, alias="totalTasks")
    completed_tasks: int = Field(0, alias="completedTasks")
    current_task: str = Field("", alias="currentTask")
    files_changed: int = Field(0, alias="filesChanged")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class DevExportArtifacts(BaseModel):
    """Export artifacts for slides dev-tasks."""

    pdf_url: str | None = Field(None, alias="pdfUrl")
    code_url: str | None = Field(None, alias="codeUrl")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class DevTask(BaseModel):
    """API response model for a development task."""

    id: str
    title: str
    spec_id: str | None = Field(None, alias="specId")
    slides_id: str | None = Field(None, alias="slidesId")
    mode: str = "mockup"  # mockup | openspec | slides
    status: str = "pending"  # pending | running | completed | failed
    archived: bool = False
    skill_ids: list[str] = Field(default_factory=list, alias="skillIds")
    current_iteration: int = Field(0, alias="currentIteration")
    iterations: list[DevIteration] = Field(default_factory=list)
    # Legacy flat stages for backward compat (populated from iterations[0] for mockup)
    stages: list[DevStage] = Field(default_factory=list)
    artifacts: list[DevArtifact] = Field(default_factory=list)
    export_artifacts: DevExportArtifacts | None = Field(None, alias="exportArtifacts")
    screenshots: list[str] = Field(default_factory=list)
    artifact_url: str | None = Field(None, alias="artifactUrl")
    sandbox_task_id: str | None = Field(None, alias="sandboxTaskId")
    decisions: list[DevDecision] = Field(default_factory=list)
    squad: SquadInfo | None = None
    openspec_status: OpenSpecStatus | None = Field(None, alias="openspecStatus")
    premium_requests: int = Field(0, alias="premiumRequests")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "serialize_by_alias": True}
