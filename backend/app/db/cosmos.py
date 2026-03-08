"""Cosmos DB client with dual authentication (DefaultAzureCredential + emulator)."""

import logging
import os

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

logger = logging.getLogger(__name__)

_client: CosmosClient | None = None


def _is_emulator(endpoint: str) -> bool:
    return "localhost" in endpoint or "127.0.0.1" in endpoint


async def get_cosmos_client() -> CosmosClient:
    """Return a singleton async CosmosClient."""
    global _client
    if _client is not None:
        return _client

    endpoint = os.environ.get("COSMOS_ENDPOINT", "https://localhost:8081")

    if _is_emulator(endpoint):
        key = os.environ.get(
            "COSMOS_KEY",
            "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
        )
        _client = CosmosClient(endpoint, credential=key, connection_verify=False)
    else:
        credential = DefaultAzureCredential()
        _client = CosmosClient(endpoint, credential=credential)

    logger.info("Cosmos DB client initialized (emulator=%s)", _is_emulator(endpoint))
    return _client


async def close_cosmos_client() -> None:
    """Close the singleton client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
