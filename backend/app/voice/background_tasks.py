"""Background task manager for voice sessions.

Tracks long-running tasks and notifies active voice sessions on completion.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class BackgroundTask:
    id: str
    action: str
    description: str
    status: str = "running"  # running | completed | failed
    result_summary: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class BackgroundTaskManager:
    """Manages background tasks and notifies voice sessions on completion."""

    def __init__(self):
        self._tasks: dict[str, BackgroundTask] = {}
        self._completion_queue: asyncio.Queue[BackgroundTask] = asyncio.Queue()

    def create_task(self, action: str, description: str) -> BackgroundTask:
        task = BackgroundTask(
            id=str(uuid.uuid4()),
            action=action,
            description=description,
        )
        self._tasks[task.id] = task
        return task

    async def complete_task(self, task_id: str, summary: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = "completed"
            task.result_summary = summary
            await self._completion_queue.put(task)
            logger.info("Background task %s completed: %s", task_id, task.action)

    async def fail_task(self, task_id: str, error: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = "failed"
            task.result_summary = error
            await self._completion_queue.put(task)
            logger.info("Background task %s failed: %s", task_id, task.action)

    async def get_completion(self, timeout: float = 1.0) -> BackgroundTask | None:
        """Non-blocking check for completed tasks."""
        try:
            return self._completion_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
