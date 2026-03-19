"""In-memory development task service with JSON persistence."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.models.dev_task import DevArtifact, DevIteration, DevStage, DevTask, DevTaskCreate, SquadInfo, SquadMember
from app.services.json_persistence import JsonPersistenceMixin

logger = logging.getLogger(__name__)

STAGE_NAMES = ["init", "openspec", "skills", "squad", "propose", "apply", "archive", "screenshots"]


def _default_stages() -> list[dict]:
    return [{"name": n, "status": "pending"} for n in STAGE_NAMES]


def _default_iteration(index: int, label: str, spec_part_id: str | None = None) -> dict:
    return {
        "iterationIndex": index,
        "label": label,
        "specPartId": spec_part_id,
        "stages": _default_stages(),
        "workspacePath": None,
    }


class InMemoryDevService(JsonPersistenceMixin):
    """In-memory CRUD for development tasks with JSON file persistence."""

    _json_file = "dev_tasks.json"

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._load_from_disk()

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
            mode=doc.get("mode", "mockup"),
            status=doc.get("status", "pending"),
            skillIds=doc.get("skillIds", []),
            currentIteration=doc.get("currentIteration", 0),
            iterations=iterations,
            stages=flat_stages,
            artifacts=[DevArtifact(**a) for a in doc.get("artifacts", [])],
            squad=SquadInfo(
                teamMembers=[SquadMember(**m) for m in sq["teamMembers"]]
            ) if (sq := doc.get("squad")) else None,
            premiumRequests=doc.get("premiumRequests", 0),
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
        )

    async def create(self, data: DevTaskCreate) -> DevTask:
        now = datetime.now(UTC)
        task_id = str(uuid.uuid4())
        # Create default single iteration for mock mode
        iterations = [_default_iteration(0, data.title)]
        doc = {
            "id": task_id,
            "userId": self._user_id or "default-user",
            "title": data.title,
            "specId": data.spec_id,
            "mode": data.mode,
            "status": "pending",
            "skillIds": data.skill_ids,
            "currentIteration": 0,
            "iterations": iterations,
            "stages": _default_stages(),  # legacy compat
            "artifacts": [],
            "premiumRequests": 0,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
        self._store[task_id] = doc
        self._save_to_disk()
        logger.info("Created dev task %s (mode=%s)", task_id, data.mode)
        return self._doc_to_model(doc)

    async def set_iterations(self, task_id: str, iterations: list[dict]) -> DevTask | None:
        """Replace iterations on a task (used when populating from specs)."""
        doc = self._store.get(task_id)
        if not doc:
            return None
        doc["iterations"] = iterations
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)

    async def list(self) -> list[DevTask]:
        docs = sorted(self._user_items(), key=lambda d: d["createdAt"], reverse=True)
        return [self._doc_to_model(d) for d in docs]

    async def get_by_id(self, task_id: str) -> DevTask | None:
        doc = self._store.get(task_id)
        return self._doc_to_model(doc) if doc else None

    async def get_raw(self, task_id: str) -> dict | None:
        """Get the raw dict for a dev task (used for stage resets)."""
        return self._store.get(task_id)

    async def save_raw(self, doc: dict) -> None:
        """Save a raw dict back (used after stage resets)."""
        self._store[doc["id"]] = doc
        self._save_to_disk()

    async def delete(self, task_id: str) -> bool:
        if task_id in self._store:
            del self._store[task_id]
            self._save_to_disk()
            logger.info("Deleted dev task %s", task_id)
            return True
        return False

    async def set_skill_ids(self, task_id: str, skill_ids: list[str]) -> DevTask | None:
        doc = self._store.get(task_id)
        if not doc:
            return None
        doc["skillIds"] = skill_ids
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)

    async def set_status(self, task_id: str, status: str) -> DevTask | None:
        doc = self._store.get(task_id)
        if not doc:
            return None
        doc["status"] = status
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)

    async def set_squad(self, task_id: str, squad_data: dict) -> None:
        """Store squad metadata on a dev task."""
        doc = self._store.get(task_id)
        if not doc:
            return
        doc["squad"] = squad_data
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()

    async def add_premium_requests(self, task_id: str, count: int) -> None:
        """Increment the premium request counter for a task."""
        doc = self._store.get(task_id)
        if doc:
            doc["premiumRequests"] = doc.get("premiumRequests", 0) + count
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            self._save_to_disk()

    async def set_current_iteration(self, task_id: str, index: int) -> None:
        doc = self._store.get(task_id)
        if doc:
            doc["currentIteration"] = index
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            self._save_to_disk()

    async def set_iteration_stage_status(
        self, task_id: str, iteration_index: int, stage_name: str,
        status: str, output: str | None = None, error: str | None = None,
    ) -> DevTask | None:
        """Update a stage within a specific iteration."""
        doc = self._store.get(task_id)
        if not doc:
            return None
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
        self._save_to_disk()
        return self._doc_to_model(doc)

    async def set_stage_status(
        self, task_id: str, stage_name: str, status: str,
        output: str | None = None, error: str | None = None,
    ) -> DevTask | None:
        """Legacy: update top-level stage and iteration 0 stage."""
        return await self.set_iteration_stage_status(task_id, 0, stage_name, status, output, error)

    async def set_iteration_workspace(self, task_id: str, iteration_index: int, path: str) -> None:
        doc = self._store.get(task_id)
        if doc:
            for it in doc.get("iterations", []):
                if it["iterationIndex"] == iteration_index:
                    it["workspacePath"] = path
                    break
            doc["updatedAt"] = datetime.now(UTC).isoformat()
            self._save_to_disk()

    async def add_iteration(self, task_id: str, iteration: dict) -> int | None:
        """Append a new iteration to a task. Returns the new iteration index, or None if task not found."""
        doc = self._store.get(task_id)
        if not doc:
            return None
        iterations = doc.setdefault("iterations", [])
        new_index = max((it["iterationIndex"] for it in iterations), default=-1) + 1
        iteration["iterationIndex"] = new_index
        iterations.append(iteration)
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        logger.info("Added iteration %d to dev task %s: %s", new_index, task_id, iteration.get("label", ""))
        return new_index

    async def add_artifact(self, task_id: str, artifact: DevArtifact) -> DevTask | None:
        doc = self._store.get(task_id)
        if not doc:
            return None
        doc.setdefault("artifacts", []).append(artifact.model_dump())
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
        return self._doc_to_model(doc)
