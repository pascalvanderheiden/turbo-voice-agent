"""Local Docker sandbox service — auto-starts the sandbox container for local dev.

When ACI credentials aren't available, this service manages the sandbox container
via docker compose. It starts the container on backend startup and stops it on
shutdown, so developers don't need to manually run `docker compose up -d sandbox`.

The container is the same image/config defined in the project's docker-compose.yml.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil

import httpx

logger = logging.getLogger(__name__)

SANDBOX_URL = os.getenv("SANDBOX_URL", "http://localhost:4000")
HEALTH_TIMEOUT = 90  # seconds to wait for sandbox to become healthy after start
HEALTH_POLL_INTERVAL = 2  # seconds between health polls
COMPOSE_PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _docker_compose_cmd() -> list[str] | None:
    """Return the docker compose base command, or None if unavailable."""
    if shutil.which("docker"):
        # Modern docker compose (plugin)
        return ["docker", "compose"]
    return None


class DockerSandboxService:
    """Manages a local Docker sandbox container for dev pipelines.

    Uses the ``sandbox`` service defined in the project's docker-compose.yml.
    Only used when ACI sandbox is not configured (local development).
    """

    def __init__(self) -> None:
        self._compose_cmd = _docker_compose_cmd()
        self._started = False

    @property
    def available(self) -> bool:
        """Check if docker compose is available on this machine."""
        return self._compose_cmd is not None

    async def _run_compose(self, *args: str, timeout: float = 120) -> tuple[int, str, str]:
        """Run a docker compose command and return (returncode, stdout, stderr)."""
        if not self._compose_cmd:
            return 1, "", "docker compose not available"
        cmd = [*self._compose_cmd, "-f", os.path.join(COMPOSE_PROJECT_DIR, "docker-compose.yml")]
        cmd.extend(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=COMPOSE_PROJECT_DIR,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            proc.kill()
            return 1, "", "docker compose command timed out"
        return proc.returncode or 0, stdout.decode(), stderr.decode()

    async def is_healthy(self) -> bool:
        """Check if the sandbox container is responding to health checks."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{SANDBOX_URL}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def start(self) -> bool:
        """Start the sandbox container via docker compose.

        Returns True if the sandbox is healthy after startup.
        Builds the image first if it doesn't exist.
        """
        if not self.available:
            logger.warning("Docker not available — cannot auto-start sandbox")
            return False

        # Already healthy? Nothing to do.
        if await self.is_healthy():
            logger.info("Local sandbox already running at %s", SANDBOX_URL)
            self._started = False  # We didn't start it, don't stop it
            return True

        logger.info("Starting local Docker sandbox via docker compose…")

        # Start the sandbox service (builds if needed)
        rc, stdout, stderr = await self._run_compose(
            "up", "-d", "--build", "sandbox",
            timeout=300,  # Image build can take a while first time
        )
        if rc != 0:
            logger.error(
                "Failed to start sandbox container (exit %d): %s",
                rc, stderr.strip() or stdout.strip(),
            )
            return False

        logger.info("Docker compose started sandbox — waiting for health check…")
        self._started = True

        # Poll for health
        deadline = asyncio.get_event_loop().time() + HEALTH_TIMEOUT
        while asyncio.get_event_loop().time() < deadline:
            if await self.is_healthy():
                logger.info("Local Docker sandbox is healthy at %s", SANDBOX_URL)
                return True
            await asyncio.sleep(HEALTH_POLL_INTERVAL)

        logger.error(
            "Local Docker sandbox failed to become healthy within %ds at %s",
            HEALTH_TIMEOUT, SANDBOX_URL,
        )
        return False

    async def stop(self) -> None:
        """Stop the sandbox container if we started it."""
        if not self._started:
            return
        logger.info("Stopping local Docker sandbox…")
        rc, _, stderr = await self._run_compose("stop", "sandbox", timeout=30)
        if rc != 0:
            logger.warning("Failed to stop sandbox: %s", stderr.strip())
        else:
            logger.info("Local Docker sandbox stopped")
        self._started = False
