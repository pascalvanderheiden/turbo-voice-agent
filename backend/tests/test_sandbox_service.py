"""Tests for SandboxService."""

import pytest

from app.models.sandbox import SandboxConfig
from app.services.inmemory_sandbox_service import InMemorySandboxService


@pytest.fixture
def service():
    svc = InMemorySandboxService()
    return svc.with_user("test-user")


@pytest.mark.asyncio
async def test_initial_state_is_none(service):
    """No state exists initially."""
    state = await service.get_state()
    assert state is None


@pytest.mark.asyncio
async def test_update_config_creates_state(service):
    """Updating config auto-creates sandbox state."""
    config = SandboxConfig(model="gpt-4.1")
    state = await service.update_config(config)
    assert state is not None
    assert state.config.model == "gpt-4.1"
    assert state.user_id == "test-user"


@pytest.mark.asyncio
async def test_set_status(service):
    """Can update sandbox status."""
    await service.update_config(SandboxConfig())
    state = await service.set_status("ready")
    assert state.status == "ready"


@pytest.mark.asyncio
async def test_set_github_connected(service):
    """Can set github connected flag."""
    await service.update_config(SandboxConfig())
    state = await service.set_github_connected(True)
    assert state.github_connected is True


@pytest.mark.asyncio
async def test_delete_state(service):
    """Can delete sandbox state."""
    await service.update_config(SandboxConfig())
    deleted = await service.delete_state()
    assert deleted is True
    state = await service.get_state()
    assert state is None


@pytest.mark.asyncio
async def test_user_isolation():
    """Different users have isolated sandbox state."""
    svc = InMemorySandboxService()
    user1 = svc.with_user("user-1")
    user2 = svc.with_user("user-2")

    await user1.update_config(SandboxConfig(model="gpt-4.1"))
    await user2.update_config(SandboxConfig(model="claude-sonnet-4"))

    state1 = await user1.get_state()
    state2 = await user2.get_state()
    assert state1.config.model == "gpt-4.1"
    assert state2.config.model == "claude-sonnet-4"
