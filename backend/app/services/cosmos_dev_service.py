"""DevService — CRUD operations for dev tasks against Cosmos DB."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from azure.cosmos.aio import ContainerProxy, CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.db.init import DATABASE_ID, DEV_TASKS_CONTAINER_ID
from app.models.dev_task import DevArtifact, DevIteration, DevStage, DevTask, DevTaskCreate, SquadInfo, SquadMember

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default-user"

STAGE_NAMES = ["init", "openspec", "skills", "squad", "propose", "apply", "archive", "screenshots"]
SLIDES_STAGE_NAMES = ["init", "slides", "export"]


def _default_stages() -> list[dict]:
    return [{"name": n, "status": "pending"} for n in STAGE_NAMES]


def _slides_stages() -> list[dict]:
    return [{"name": n, "status": "pending"} for n in SLIDES_STAGE_NAMES]


def _default_iteration(index: int, label: str, spec_part_id: str | None = None) -> dict:
    return {
        "iterationIndex": index,
        "label": label,
        "specPartId": spec_part_id,
        "stages": _default_stages(),
        "workspacePath": None,
    }


def _slides_iteration(index: int, label: str, slides_id: str | None = None) -> dict:
    return {
        "iterationIndex": index,
        "label": label,
        "specPartId": slides_id,
        "stages": _slides_stages(),
        "workspacePath": None,
    }


class DevService:
    """Service layer for dev tasks CRUD backed by Cosmos DB."""

    def __init__(self, client: CosmosClient, user_id: str = DEFAULT_USER_ID):
        self._client = client
        self._user_id = user_id

    def with_user(self, user_id: str) -> "DevService":
        """Return a view of this service scoped to a specific user."""
        return self.__class__(self._client, user_id)

    async def _container(self) -> ContainerProxy:
        db = self._client.get_database_client(DATABASE_ID)
        return db.get_container_client(DEV_TASKS_CONTAINER_ID)

    def _doc_to_model(self, doc: dict) -> DevTask:
        iterations = [
            DevIteration(
                iterationIndex=it["iterationIndex"],
                label=it.get("label", f"Iteration {it['iterationIndex']}"),
                specPartId=it.get("specPartId"),
                stages=[DevStage(**s) for s in it.get("stages", _default_stages())],
                workspacePath=it.get("workspacePath"),
            )
            for it in doc.get("iterations", [])
        ]
        # Legacy stages: flatten from first iteration or use top-level
        if iterations:
            flat_stages = iterations[0].stages
        else:
            flat_stages = [DevStage(**s) for s in doc.get("stages", _default_stages())]

        return DevTask(
            id=doc["id"],
            title=doc["title"],
            specId=doc.get("specId"),
            slidesId=doc.get("slidesId"),
            mode=doc.get("mode", "mockup"),
            status=doc.get("status", "pending"),
            archived=doc.get("archived", False),
            skillIds=doc.get("skillIds", []),
            currentIteration=doc.get("currentIteration", 0),
            iterations=iterations,
            stages=flat_stages,
            artifacts=[DevArtifact(**a) for a in doc.get("artifacts", [])],
            exportArtifacts=doc.get("exportArtifacts"),
            squad=SquadInfo(
                teamMembers=[SquadMember(**m) for m in sq["teamMembers"]]
            ) if (sq := doc.get("squad")) else None,
            premiumRequests=doc.get("premiumRequests", 0),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    async def create(self, data: DevTaskCreate) -> DevTask:
        """Create a new dev task."""
        try:
            container = await self._container()
            now = datetime.now(UTC)
            task_id = str(uuid.uuid4())
            if data.mode == "slides":
                iterations = [_slides_iteration(
                    0, data.title, getattr(data, "slides_id", None)
                )]
                flat_stages = _slides_stages()
            else:
                iterations = [_default_iteration(0, data.title)]
                flat_stages = _default_stages()
            doc = {
                "id": task_id,
                "userId": self._user_id,
                "docType": "dev_task",
                "title": data.title,
                "specId": data.spec_id,
                "slidesId": getattr(data, "slides_id", None),
                "mode": data.mode,
                "status": "pending",
                "archived": False,
                "skillIds": data.skill_ids,
                "currentIteration": 0,
                "iterations": iterations,
                "stages": flat_stages,
                "artifacts": [],
                "exportArtifacts": None,
                "premiumRequests": 0,
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
            }
            result = await container.upsert_item(doc)
            logger.info("Created dev task %s (mode=%s)", task_id, data.mode)
            return self._doc_to_model(result)
        except Exception:
            logger.exception("Failed to create dev task")
            return None

    async def list(self) -> list[DevTask]:
        """List all dev tasks for the current user."""
        try:
            container = await self._container()
            query = (
                "SELECT * FROM c WHERE c.userId = @userId AND c.docType = 'dev_task' "
                "ORDER BY c.createdAt DESC"
            )
            params = [{"name": "@userId", "value": self._user_id}]
            items = container.query_items(
                query=query,
                parameters=params,
                partition_key=self._user_id,
            )
            return [self._doc_to_model(doc) async for doc in items]
        except Exception:
            logger.exception("Failed to list dev tasks")
            return []

    async def get_by_id(self, task_id: str) -> DevTask | None:
        """Get a single dev task by ID."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            return self._doc_to_model(doc)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to get dev task %s", task_id)
            return None

    async def get_raw(self, task_id: str) -> dict | None:
        """Get the raw Cosmos document for a dev task (used for stage resets)."""
        try:
            container = await self._container()
            return await container.read_item(item=task_id, partition_key=self._user_id)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to get raw dev task %s", task_id)
            return None

    async def save_raw(self, doc: dict) -> None:
        """Upsert a raw Cosmos document (used after stage resets)."""
        try:
            container = await self._container()
            await container.upsert_item(doc)
        except Exception:
            logger.exception("Failed to save raw dev task %s", doc.get("id"))

    async def delete(self, task_id: str) -> bool:
        """Delete a dev task by ID."""
        try:
            container = await self._container()
            await container.delete_item(item=task_id, partition_key=self._user_id)
            logger.info("Deleted dev task %s", task_id)
            return True
        except CosmosResourceNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to delete dev task %s", task_id)
            return False

    async def set_skill_ids(self, task_id: str, skill_ids: list[str]) -> DevTask | None:
        """Update skill IDs on a task."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["skillIds"] = skill_ids
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to set skill IDs on dev task %s", task_id)
            return None

    async def set_status(self, task_id: str, status: str) -> DevTask | None:
        """Update status on a task."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["status"] = status
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to set status on dev task %s", task_id)
            return None

    async def set_squad(self, task_id: str, squad_data: dict) -> None:
        """Store squad metadata on a dev task."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["squad"] = squad_data
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            await container.upsert_item(doc)
        except Exception:
            logger.exception("Failed to set squad on dev task %s", task_id)

    async def set_openspec_status(self, task_id: str, status_data: dict) -> None:
        """Store openspec change status on a dev task."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["openspecStatus"] = status_data
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            await container.upsert_item(doc)
        except Exception:
            logger.exception("Failed to set openspec status on dev task %s", task_id)

    async def set_archived(self, task_id: str, archived: bool) -> DevTask | None:
        """Set the archived status on a dev task."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["archived"] = archived
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to set archived on dev task %s", task_id)
            return None

    async def set_export_artifacts(self, task_id: str, artifacts: dict) -> None:
        """Store export artifacts (PDF/code URLs) on a dev task."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["exportArtifacts"] = artifacts
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            await container.upsert_item(doc)
        except Exception:
            logger.exception("Failed to set export artifacts on dev task %s", task_id)

    async def add_premium_requests(self, task_id: str, count: int) -> None:
        """Increment the premium request counter for a task."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["premiumRequests"] = doc.get("premiumRequests", 0) + count
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            await container.upsert_item(doc)
        except Exception:
            logger.exception("Failed to add premium requests on dev task %s", task_id)

    async def set_current_iteration(self, task_id: str, index: int) -> None:
        """Set the current iteration index."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["currentIteration"] = index
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            await container.upsert_item(doc)
        except Exception:
            logger.exception("Failed to set current iteration on dev task %s", task_id)

    async def set_iterations(self, task_id: str, iterations: list[dict]) -> DevTask | None:
        """Replace iterations on a task (used when populating from specs)."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc["iterations"] = iterations
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to set iterations on dev task %s", task_id)
            return None

    async def set_iteration_stage_status(
        self, task_id: str, iteration_index: int, stage_name: str,
        status: str, output: str | None = None, error: str | None = None,
    ) -> DevTask | None:
        """Update a stage within a specific iteration."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            iterations = doc.get("iterations", [])
            for it in iterations:
                if it["iterationIndex"] == iteration_index:
                    for stage in it.get("stages", []):
                        if stage["name"] == stage_name:
                            stage["status"] = status
                            if status == "running":
                                stage["startedAt"] = datetime.now(UTC).isoformat()
                            if status in ("completed", "failed"):
                                stage["completedAt"] = datetime.now(UTC).isoformat()
                            if output is not None:
                                stage["output"] = output
                            if error is not None:
                                stage["error"] = error
                            break
                    break
            # Also update legacy top-level stages for iteration 0
            if iteration_index == 0:
                for stage in doc.get("stages", []):
                    if stage["name"] == stage_name:
                        stage["status"] = status
                        if status == "running":
                            stage["startedAt"] = datetime.now(UTC).isoformat()
                        if status in ("completed", "failed"):
                            stage["completedAt"] = datetime.now(UTC).isoformat()
                        if output is not None:
                            stage["output"] = output
                        if error is not None:
                            stage["error"] = error
                        break
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to set stage status on dev task %s", task_id)
            return None

    async def set_stage_status(
        self, task_id: str, stage_name: str, status: str,
        output: str | None = None, error: str | None = None,
    ) -> DevTask | None:
        """Legacy: update top-level stage and iteration 0 stage."""
        return await self.set_iteration_stage_status(task_id, 0, stage_name, status, output, error)

    async def set_iteration_workspace(self, task_id: str, iteration_index: int, path: str) -> None:
        """Set workspace path for a specific iteration."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            for it in doc.get("iterations", []):
                if it["iterationIndex"] == iteration_index:
                    it["workspacePath"] = path
                    break
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            await container.upsert_item(doc)
        except Exception:
            logger.exception("Failed to set iteration workspace on dev task %s", task_id)

    async def add_artifact(self, task_id: str, artifact: DevArtifact) -> DevTask | None:
        """Add an artifact to a dev task."""
        try:
            container = await self._container()
            doc = await container.read_item(item=task_id, partition_key=self._user_id)
            doc.setdefault("artifacts", []).append(artifact.model_dump())
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            result = await container.upsert_item(doc)
            return self._doc_to_model(result)
        except CosmosResourceNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to add artifact to dev task %s", task_id)
            return None
