"""ACI Sandbox Service — per-task Azure Container Instance lifecycle management.

Provisions a dedicated ACI container group for each dev-task, polls for readiness,
resolves the private IP, and tears down the container on completion.

Feature-gated by USE_ACI_SANDBOX env var. When disabled, the shared Container App
sandbox is used via static SANDBOX_URL.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime

import httpx
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (
    Container,
    ContainerGroup,
    ContainerGroupSubnetId,
    ContainerPort,
    EnvironmentVariable,
    IpAddress,
    Port,
    ResourceRequests,
    ResourceRequirements,
    UserAssignedIdentities,
)

logger = logging.getLogger(__name__)

# ── Configuration from environment ──────────────────────────────────────
ACI_RESOURCE_GROUP = os.getenv("ACI_RESOURCE_GROUP", "")
ACI_SUBNET_ID = os.getenv("ACI_SUBNET_ID", "")
ACI_IDENTITY_ID = os.getenv("ACI_IDENTITY_ID", "")
ACI_IDENTITY_CLIENT_ID = os.getenv("ACI_IDENTITY_CLIENT_ID", "")
ACI_SANDBOX_IMAGE = os.getenv("ACI_SANDBOX_IMAGE", "")
ACI_SANDBOX_CPU = float(os.getenv("ACI_SANDBOX_CPU", "2.0"))
ACI_SANDBOX_MEMORY = float(os.getenv("ACI_SANDBOX_MEMORY", "4.0"))
ACI_ACR_LOGIN_SERVER = os.getenv("ACI_ACR_LOGIN_SERVER", "")

# Default env vars passed to every ACI sandbox container
_DEFAULT_ENV = {
    "PORT": os.getenv("ACI_SANDBOX_PORT", "3000"),
    "BACKEND_URL": os.getenv("BACKEND_URL", ""),
    "COPILOT_MODEL": os.getenv("COPILOT_MODEL", "claude-opus-4.6"),
    "AZURE_STORAGE_ACCOUNT_NAME": os.getenv("AZURE_STORAGE_ACCOUNT_NAME", ""),
    "SINGLE_TASK_MODE": "true",
}

# Timeouts
PROVISION_TIMEOUT = 120  # seconds to wait for ACI to become ready
HEALTH_POLL_INTERVAL = 5  # seconds between health polls
ORPHAN_MAX_AGE_HOURS = 2
ORPHAN_CLEANUP_INTERVAL = 900  # 15 minutes

# Container group naming: sandbox-{first 8 chars of task UUID}
_NAME_PREFIX = "sandbox-"


def _container_group_name(task_id: str) -> str:
    """Generate a deterministic ACI container group name from a task ID."""
    short = task_id.replace("-", "")[:8].lower()
    return f"{_NAME_PREFIX}{short}"


class AciSandboxService:
    """Manages per-task ACI sandbox container groups."""

    def __init__(self) -> None:
        self._credential = DefaultAzureCredential()
        sub_id = os.getenv("AZURE_SUBSCRIPTION_ID", "")
        if not sub_id and ACI_SUBNET_ID:
            # Extract from ACI_SUBNET_ID (format: /subscriptions/{id}/...)
            parts = ACI_SUBNET_ID.split("/")
            if len(parts) > 2 and parts[1] == "subscriptions":
                sub_id = parts[2]
        if not sub_id:
            raise RuntimeError(
                "AZURE_SUBSCRIPTION_ID is required for ACI sandbox service. "
                "Set it as an environment variable."
            )
        self._client = ContainerInstanceManagementClient(self._credential, sub_id)
        # task_id → private IP mapping (cache)
        self._task_ips: dict[str, str] = {}

    async def create_container_group(
        self,
        task_id: str,
        extra_env: dict[str, str] | None = None,
    ) -> str:
        """Provision an ACI container group for a dev-task. Returns the private IP.

        Raises RuntimeError if provisioning times out.
        """
        name = _container_group_name(task_id)
        env_vars = {**_DEFAULT_ENV, **(extra_env or {})}

        container = Container(
            name="sandbox",
            image=ACI_SANDBOX_IMAGE,
            resources=ResourceRequirements(
                requests=ResourceRequests(cpu=ACI_SANDBOX_CPU, memory_in_gb=ACI_SANDBOX_MEMORY)
            ),
            ports=[ContainerPort(port=3000, protocol="TCP")],
            environment_variables=[
                EnvironmentVariable(name=k, value=v) if k != "GH_TOKEN"
                else EnvironmentVariable(name=k, secure_value=v)
                for k, v in env_vars.items()
                if v
            ],
        )

        group = ContainerGroup(
            location=os.getenv("AZURE_LOCATION", "eastus2"),
            identity={
                "type": "UserAssigned",
                "user_assigned_identities": {ACI_IDENTITY_ID: UserAssignedIdentities()},
            } if ACI_IDENTITY_ID else None,
            containers=[container],
            os_type="Linux",
            restart_policy="Never",
            subnet_ids=[ContainerGroupSubnetId(id=ACI_SUBNET_ID)] if ACI_SUBNET_ID else None,
            ip_address=IpAddress(
                ports=[Port(port=3000, protocol="TCP")],
                type="Private" if ACI_SUBNET_ID else "Public",
            ),
            image_registry_credentials=[{
                "server": ACI_ACR_LOGIN_SERVER,
                "identity": ACI_IDENTITY_ID,
            }] if ACI_ACR_LOGIN_SERVER and ACI_IDENTITY_ID else None,
            tags={
                "task_id": task_id,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

        logger.info("Creating ACI container group %s for task %s", name, task_id)

        # ARM create is blocking — run in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.container_groups.begin_create_or_update(
                ACI_RESOURCE_GROUP, name, group
            ).result(),
        )

        # Poll for readiness
        ip = await self._poll_until_ready(task_id, name)
        self._task_ips[task_id] = ip
        logger.info("ACI container group %s ready at %s for task %s", name, ip, task_id)
        return ip

    async def _poll_until_ready(self, task_id: str, name: str) -> str:
        """Poll ACI provisioning state + health endpoint until ready."""
        deadline = asyncio.get_event_loop().time() + PROVISION_TIMEOUT
        ip = ""

        while asyncio.get_event_loop().time() < deadline:
            loop = asyncio.get_event_loop()
            cg = await loop.run_in_executor(
                None,
                lambda: self._client.container_groups.get(ACI_RESOURCE_GROUP, name),
            )

            state = cg.provisioning_state
            if state == "Failed":
                raise RuntimeError(f"ACI provisioning failed for task {task_id}")

            if state == "Succeeded" and cg.ip_address and cg.ip_address.ip:
                ip = cg.ip_address.ip
                # Check sandbox health endpoint
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(f"http://{ip}:3000/health")
                        if resp.status_code == 200:
                            return ip
                except Exception:
                    pass  # Not ready yet

            await asyncio.sleep(HEALTH_POLL_INTERVAL)

        raise RuntimeError(
            f"ACI sandbox provisioning timed out after {PROVISION_TIMEOUT}s for task {task_id}"
        )

    def get_sandbox_url(self, task_id: str) -> str | None:
        """Get the sandbox URL for a task (from cached private IP)."""
        ip = self._task_ips.get(task_id)
        return f"http://{ip}:3000" if ip else None

    async def delete_container_group(self, task_id: str) -> None:
        """Delete the ACI container group for a task (best-effort)."""
        name = _container_group_name(task_id)
        self._task_ips.pop(task_id, None)
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._client.container_groups.begin_delete(
                    ACI_RESOURCE_GROUP, name
                ).result(),
            )
            logger.info("Deleted ACI container group %s for task %s", name, task_id)
        except Exception as exc:
            logger.warning(
                "Failed to delete ACI container group %s for task %s: %s",
                name, task_id, exc,
            )

    async def is_ready(self, task_id: str) -> bool:
        """Check if the ACI container for a task is healthy."""
        url = self.get_sandbox_url(task_id)
        if not url:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def cleanup_orphans(self, active_task_ids: set[str]) -> int:
        """Delete ACI container groups that are orphaned (no active task, >2h old)."""
        deleted = 0
        try:
            loop = asyncio.get_event_loop()
            groups = await loop.run_in_executor(
                None,
                lambda: list(
                    self._client.container_groups.list_by_resource_group(ACI_RESOURCE_GROUP)
                ),
            )
            now = datetime.now(UTC)
            for cg in groups:
                if not cg.name or not cg.name.startswith(_NAME_PREFIX):
                    continue
                task_id = (cg.tags or {}).get("task_id", "")
                if task_id in active_task_ids:
                    continue
                created_str = (cg.tags or {}).get("created_at", "")
                if created_str:
                    try:
                        created = datetime.fromisoformat(created_str)
                        age_hours = (now - created).total_seconds() / 3600
                        if age_hours < ORPHAN_MAX_AGE_HOURS:
                            continue
                    except ValueError:
                        pass
                # Orphaned — delete
                try:
                    await loop.run_in_executor(
                        None,
                        lambda n=cg.name: self._client.container_groups.begin_delete(
                            ACI_RESOURCE_GROUP, n
                        ).result(),
                    )
                    deleted += 1
                    logger.info("Cleaned up orphaned ACI container group: %s", cg.name)
                except Exception as exc:
                    logger.warning("Failed to cleanup orphan %s: %s", cg.name, exc)
        except Exception as exc:
            logger.warning("Orphan cleanup sweep failed: %s", exc)
        return deleted
