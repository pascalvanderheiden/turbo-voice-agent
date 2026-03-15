"""End-to-end test stubs for sandbox integration.

These tests require a running sandbox Container App and are skipped in CI
unless SANDBOX_E2E=true is set.
"""

import os
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SANDBOX_E2E") != "true",
    reason="Sandbox E2E tests require SANDBOX_E2E=true and a running sandbox",
)


@pytest.mark.asyncio
async def test_mockup_pipeline_e2e():
    """E2E: Generate spec → create Mockup task → sandbox executes → screenshots."""
    # TODO: implement when sandbox Container App is deployed
    pytest.skip("Sandbox not yet deployed")


@pytest.mark.asyncio
async def test_openspec_pipeline_e2e():
    """E2E: Generate spec → create OpenSpec task → foundation + features → screenshots."""
    pytest.skip("Sandbox not yet deployed")


@pytest.mark.asyncio
async def test_skill_sync_e2e():
    """E2E: Install skill → sandbox recreation → verify skill present."""
    pytest.skip("Sandbox not yet deployed")


@pytest.mark.asyncio
async def test_auth_flow_e2e():
    """E2E: Connect token → trigger dev task → CLI authenticates."""
    pytest.skip("Sandbox not yet deployed")


@pytest.mark.asyncio
async def test_live_streaming_e2e():
    """E2E: Trigger task → SSE stream delivers CLI output."""
    pytest.skip("Sandbox not yet deployed")
