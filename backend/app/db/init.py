"""Database initialization — ensure database and container exist on startup."""

import logging
import os

from azure.cosmos.aio import CosmosClient

logger = logging.getLogger(__name__)

DATABASE_ID = os.environ.get("COSMOS_DATABASE", "turbovoice")
NOTES_CONTAINER_ID = "notes"
NOTES_PARTITION_KEY = "/userId"
IDEAS_CONTAINER_ID = "ideas"
IDEAS_PARTITION_KEY = "/userId"
RESEARCH_CONTAINER_ID = "research"
RESEARCH_PARTITION_KEY = "/userId"
SPECS_CONTAINER_ID = "specs"
SPECS_PARTITION_KEY = "/userId"
DEV_TASKS_CONTAINER_ID = "dev_tasks"
DEV_TASKS_PARTITION_KEY = "/userId"
MARKETING_CONTAINER_ID = "marketing"
MARKETING_PARTITION_KEY = "/userId"
SKILLS_CONTAINER_ID = "skills"
SKILLS_PARTITION_KEY = "/userId"
PROFILES_CONTAINER_ID = "profiles"
PROFILES_PARTITION_KEY = "/userId"
SANDBOX_STATE_CONTAINER_ID = "sandbox_state"
SANDBOX_STATE_PARTITION_KEY = "/userId"


async def ensure_database_and_containers(client: CosmosClient) -> None:
    """Create database and containers if they don't exist. Raises on failure."""
    database = await client.create_database_if_not_exists(id=DATABASE_ID)
    for cid, pk in [
        (NOTES_CONTAINER_ID, NOTES_PARTITION_KEY),
        (IDEAS_CONTAINER_ID, IDEAS_PARTITION_KEY),
        (RESEARCH_CONTAINER_ID, RESEARCH_PARTITION_KEY),
        (SPECS_CONTAINER_ID, SPECS_PARTITION_KEY),
        (DEV_TASKS_CONTAINER_ID, DEV_TASKS_PARTITION_KEY),
        (MARKETING_CONTAINER_ID, MARKETING_PARTITION_KEY),
        (SKILLS_CONTAINER_ID, SKILLS_PARTITION_KEY),
        (PROFILES_CONTAINER_ID, PROFILES_PARTITION_KEY),
        (SANDBOX_STATE_CONTAINER_ID, SANDBOX_STATE_PARTITION_KEY),
    ]:
        await database.create_container_if_not_exists(
            id=cid,
            partition_key={"paths": [pk], "kind": "Hash"},
        )
    logger.info("Database '%s' and containers initialized.", DATABASE_ID)
