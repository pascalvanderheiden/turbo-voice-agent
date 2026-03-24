"""Tests for ACI sandbox service — container group naming, URL resolution, cleanup logic."""

import pytest

from app.services.aci_sandbox_service import (
    _container_group_name,
    _NAME_PREFIX,
)


class TestContainerGroupNaming:
    """Verify deterministic naming from task UUIDs."""

    def test_standard_uuid(self):
        name = _container_group_name("1d98be4f-bdea-4af9-a6d3-c28df6a56630")
        assert name == f"{_NAME_PREFIX}1d98be4f"

    def test_short_id(self):
        name = _container_group_name("abc123")
        assert name == f"{_NAME_PREFIX}abc123"

    def test_uppercase_normalized(self):
        name = _container_group_name("ABCD1234-EF56-7890-0000-000000000000")
        assert name == f"{_NAME_PREFIX}abcd1234"

    def test_prefix(self):
        name = _container_group_name("anything")
        assert name.startswith("sandbox-")


class TestGetSandboxUrl:
    """Test URL resolution from cached IPs."""

    def test_returns_none_when_no_ip(self):
        from unittest.mock import patch, MagicMock

        with patch("app.services.aci_sandbox_service.DefaultAzureCredential"):
            with patch("app.services.aci_sandbox_service.ContainerInstanceManagementClient"):
                from app.services.aci_sandbox_service import AciSandboxService

                svc = AciSandboxService()
                assert svc.get_sandbox_url("nonexistent") is None

    def test_returns_url_when_ip_cached(self):
        from unittest.mock import patch

        with patch("app.services.aci_sandbox_service.DefaultAzureCredential"):
            with patch("app.services.aci_sandbox_service.ContainerInstanceManagementClient"):
                from app.services.aci_sandbox_service import AciSandboxService

                svc = AciSandboxService()
                svc._task_ips["task-123"] = "10.0.4.5"
                url = svc.get_sandbox_url("task-123")
                assert url == "http://10.0.4.5:3000"
