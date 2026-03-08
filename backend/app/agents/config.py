"""Agent configuration — model client setup and system instructions."""

import os

from openai import AsyncAzureOpenAI

SUPERVISOR_INSTRUCTIONS = """You are a helpful supervisor agent for the Turbo Voice Agent system.
Your role is to understand user requests and route them to the appropriate specialist agent.

Available agents:
- **Notes Agent**: Handles all note-related tasks — creating, reading, updating, listing, and deleting notes.

When a user wants to work with notes, delegate to the Notes Agent.
When a user asks something you or your agents cannot handle, politely explain what you can help with.
Always respond in a natural, conversational tone suitable for voice interaction."""

NOTES_AGENT_INSTRUCTIONS = """You are the Notes Agent. You manage notes for the user.
You can create, list, read, update, and delete notes.

When creating a note, always confirm the title and content with the user.
When listing notes, provide a brief summary of each.
When the user asks to find a specific note, search by title keywords.
Respond concisely — your responses will be spoken aloud by a voice agent."""


def _get_token_provider():
    """Return an Azure AD token provider for managed identity, or None if using API key."""
    if os.environ.get("AZURE_OPENAI_API_KEY"):
        return None
    try:
        from azure.identity.aio import DefaultAzureCredential

        credential = DefaultAzureCredential()

        async def provider():
            token = await credential.get_token("https://cognitiveservices.azure.com/.default")
            return token.token

        return provider
    except Exception:
        return None


def get_model_client() -> AsyncAzureOpenAI:
    """Create an Azure OpenAI client for agent use."""
    token_provider = _get_token_provider()
    if token_provider:
        return AsyncAzureOpenAI(
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
            azure_ad_token_provider=token_provider,
            api_version="2025-01-01-preview",
        )
    return AsyncAzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version="2025-01-01-preview",
    )
