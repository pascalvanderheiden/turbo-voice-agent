"""Seed demo data for local development with in-memory services."""

from __future__ import annotations

import logging

from app.models.dev_task import DevTaskCreate
from app.models.idea import IdeaCreate
from app.models.marketing import MarketingVideoCreate
from app.models.note import NoteCreate
from app.models.research import ResearchCreate
from app.models.spec import SpecCreate, SpecUpdate

logger = logging.getLogger(__name__)

DEMO_USER_ID = "local-dev-user"


async def seed_demo_data(
    notes_service,
    brainstorm_service,
    research_service,
    spec_service,
    dev_service,
    marketing_service,
) -> None:
    """Populate in-memory services with representative demo data.

    Idempotent — checks whether demo-user data already exists before inserting.
    """
    # Check if any data exists for the demo user already
    has_demo_data = any(
        d.get("userId") == DEMO_USER_ID for d in notes_service._store.values()
    )
    if has_demo_data:
        logger.info("Seed data already present — skipping.")
        return

    logger.info("Seeding demo data for user '%s'...", DEMO_USER_ID)

    # Scope every service to the demo user
    notes_svc = notes_service.with_user(DEMO_USER_ID)
    ideas_svc = brainstorm_service.with_user(DEMO_USER_ID)
    research_svc = research_service.with_user(DEMO_USER_ID)
    spec_svc = spec_service.with_user(DEMO_USER_ID)
    dev_svc = dev_service.with_user(DEMO_USER_ID)
    marketing_svc = marketing_service.with_user(DEMO_USER_ID)

    # ── Notes ──────────────────────────────────────────────────────
    await notes_svc.create(
        NoteCreate(
            title="Sprint Planning — Voice Agent v2",
            content=(
                "## Key Decisions\n\n"
                "- Migrate from REST polling to WebSocket for real-time voice streaming\n"
                "- Use Azure Voice Live API for speech-to-speech pipeline\n"
                "- SupervisorAgent routes to specialist agents based on intent\n\n"
                "## Action Items\n\n"
                "- [ ] Set up WebSocket endpoint `/ws/voice`\n"
                "- [ ] Implement PCM16 audio encoding/decoding\n"
                "- [ ] Add background task support for long-running operations\n"
            ),
        )
    )

    await notes_svc.create(
        NoteCreate(
            title="Architecture Decision: Multi-Agent Orchestration",
            content=(
                "## Context\n\n"
                "We need a scalable way to handle diverse user intents during voice "
                "sessions. A single monolithic agent becomes unwieldy as capabilities "
                "grow.\n\n"
                "## Decision\n\n"
                "Adopt a supervisor pattern: one SupervisorAgent that routes function "
                "calls to 9 specialist agents (Notes, Brainstorm, Research, Spec, Dev, "
                "Marketing, Skills, Todo).\n\n"
                "## Consequences\n\n"
                "- Each agent owns its domain and tool definitions\n"
                "- Easy to add new agents without modifying existing ones\n"
                "- Supervisor handles cross-agent coordination\n"
            ),
        )
    )

    await notes_svc.create(
        NoteCreate(
            title="Quick Note: Cosmos DB Dual Auth",
            content=(
                "Remember: production uses `DefaultAzureCredential` (managed identity), "
                "while the local emulator is auto-detected by checking if the endpoint "
                "contains `localhost` or `127.0.0.1`. No API keys in production!\n\n"
                "The `InMemory*` services with JSON persistence are the fallback when "
                "Cosmos DB is unavailable."
            ),
        )
    )

    await notes_svc.create(
        NoteCreate(
            title="Voice Config: Language Support",
            content=(
                "## Supported Languages\n\n"
                "- **English (EN)**: Default voice config, uses `en-US-GuyNeural`\n"
                "- **Dutch (NL)**: Secondary config, uses `nl-NL-MaartenNeural`\n\n"
                "Voice config is selected via `get_voice_config(lang=)` and passed to "
                "the Voice Live API session. Token-based auth on the WebSocket connection."
            ),
        )
    )

    # ── Brainstorm Ideas ───────────────────────────────────────────
    idea_dashboard = await ideas_svc.create(
        IdeaCreate(
            title="Real-Time Voice Analytics Dashboard",
            description=(
                "Build a live dashboard that shows voice session metrics: "
                "active sessions, average latency, agent routing distribution, "
                "and sentiment analysis. Could help monitor the health of the "
                "voice agent system in production."
            ),
        )
    )

    idea_marketplace = await ideas_svc.create(
        IdeaCreate(
            title="Skill Marketplace for Custom Agents",
            description=(
                "Create a marketplace where users can discover, install, and share "
                "custom agent skills. Skills could extend the supervisor with new "
                "capabilities — like a CRM integration skill or a code review skill. "
                "Use blob storage for skill packages and Cosmos DB for metadata."
            ),
        )
    )

    await ideas_svc.create(
        IdeaCreate(
            title="iOS Native Voice Experience",
            description=(
                "Build a native iOS voice interface using React Native and Expo. "
                "Leverage the device microphone with low-latency PCM streaming, "
                "haptic feedback during voice interactions, and an animated orb "
                "UI that responds to voice state (listening, thinking, speaking)."
            ),
        )
    )

    # ── Research ───────────────────────────────────────────────────
    r1 = await research_svc.create(
        ResearchCreate(
            query="Best practices for real-time audio streaming over WebSocket",
            mode="web_search",
            idea_id=idea_dashboard.id if idea_dashboard else None,
        )
    )
    await research_svc.set_result(
        r1.id,
        result=(
            "## Key Findings\n\n"
            "1. **PCM16 at 24 kHz** is the sweet spot for voice — good quality "
            "with manageable bandwidth (~48 KB/s per direction)\n"
            "2. **Chunked streaming** with 20 ms frames reduces perceived latency\n"
            "3. **Opus codec** can reduce bandwidth 10× but adds encoding complexity\n"
            "4. **WebSocket ping/pong** every 30 s prevents proxy timeouts\n"
            "5. **Graceful degradation**: buffer 2–3 frames to handle network jitter\n\n"
            "## Recommendations\n\n"
            "- Use binary WebSocket frames for audio, text frames for control\n"
            "- Implement echo cancellation on the client side\n"
            "- Add server-side Voice Activity Detection (VAD) for turn management\n"
        ),
        citations=[
            {
                "url": "https://developer.mozilla.org/en-US/docs/Web/API/WebSocket",
                "title": "MDN WebSocket API",
            },
            {
                "url": "https://learn.microsoft.com/azure/ai-services/speech-service/",
                "title": "Azure Speech Service Documentation",
            },
        ],
    )

    r2 = await research_svc.create(
        ResearchCreate(
            query="Multi-agent orchestration patterns for conversational AI systems",
            mode="deep_research",
            idea_id=idea_marketplace.id if idea_marketplace else None,
        )
    )
    await research_svc.set_result(
        r2.id,
        result=(
            "## Multi-Agent Patterns\n\n"
            "### Supervisor Pattern (Recommended)\n"
            "A central supervisor routes requests to specialist agents based on "
            "intent. Each agent exposes tool definitions that the supervisor "
            "can invoke.\n\n"
            "### Advantages\n"
            "- Clear separation of concerns\n"
            "- Easy to add/remove agents\n"
            "- Supervisor can implement cross-cutting concerns (auth, logging)\n\n"
            "### Implementation Notes\n"
            "- Function calling is the most reliable routing mechanism\n"
            "- Each agent should be stateless — use external services for "
            "persistence\n"
            "- Background tasks for long-running operations (research, code gen)\n"
        ),
        citations=[
            {
                "url": "https://learn.microsoft.com/azure/ai-services/openai/",
                "title": "Azure OpenAI Service",
            },
            {
                "url": "https://www.microsoft.com/research/blog/autogen/",
                "title": "AutoGen: Multi-Agent Framework",
            },
        ],
    )

    # ── Specs ──────────────────────────────────────────────────────
    # Mockup spec — contains a ## Mockup Description section
    mockup_spec = await spec_svc.create(
        SpecCreate(
            title="Voice Analytics Dashboard Mockup",
            content=(
                "# Voice Analytics Dashboard\n\n"
                "A real-time monitoring dashboard for voice agent sessions.\n\n"
                "## Mockup Description\n\n"
                "Create a dark-themed dashboard with the Turbo Agent brand colors "
                "(hot pink #E91E8C, cyan #00D4FF, purple #7B2FBE on dark #0F0F1A "
                "background).\n\n"
                "### Layout\n"
                "- **Top bar**: Logo, session count badge, latency indicator\n"
                "- **Main grid** (3 columns):\n"
                "  - Active Sessions card with live count and sparkline\n"
                "  - Agent Distribution pie chart (Notes, Brainstorm, Research, "
                "Dev, etc.)\n"
                "  - Avg Response Latency gauge (target < 500 ms)\n"
                "- **Bottom section**: Scrollable session log table with columns: "
                "Session ID, User, Duration, Agent, Status\n\n"
                "### Interactions\n"
                "- Click a session row to see detailed transcript\n"
                "- Toggle between 1 h / 24 h / 7 d time ranges\n"
                "- Auto-refresh every 5 seconds with smooth transitions\n"
            ),
            type="foundation",
            idea_id=idea_dashboard.id if idea_dashboard else None,
        )
    )
    if mockup_spec:
        await spec_svc.update(mockup_spec.id, SpecUpdate(status="optimized"))

    # OpenSpec spec — contains ## OpenSpec Config with ### Foundation and #### Feature
    openspec_spec = await spec_svc.create(
        SpecCreate(
            title="Skill Marketplace Platform",
            content=(
                "# Skill Marketplace Platform\n\n"
                "A platform for discovering, installing, and managing custom agent "
                "skills.\n\n"
                "## OpenSpec Config\n\n"
                "### Foundation\n\n"
                "Build a Next.js 15 application with a dark-themed UI using Turbo "
                "Agent branding. Set up the base layout with a collapsible sidebar "
                "navigation, header with search bar, and main content area. Use "
                "shadcn/ui components with the new-york style variant. Include "
                "Tailwind CSS v4 with the brand color palette: pink-500 (#E91E8C), "
                "cyan-400 (#00D4FF), purple-600 (#7B2FBE). The foundation should "
                "have responsive grid layout and dark/light mode toggle.\n\n"
                "#### Feature: Skill Discovery Grid\n\n"
                "Add a responsive grid of skill cards in the main content area. "
                "Each card shows: skill icon, name, author, short description, "
                "install count, and a rating. Cards should have hover effects with "
                "a subtle glow in the brand cyan color. Include category filter "
                "chips at the top (AI, Productivity, Integration, Analytics) and a "
                "search input that filters cards in real-time.\n\n"
                "#### Feature: Skill Detail Panel\n\n"
                "When a skill card is clicked, slide in a detail panel from the "
                "right. Show full description, version history, configuration "
                "options, required permissions, and an install/uninstall button. "
                "Include a tabbed interface for Overview, Config, and Reviews. "
                "The panel should animate smoothly with a backdrop blur effect.\n"
            ),
            type="foundation",
            idea_id=idea_marketplace.id if idea_marketplace else None,
        )
    )

    # ── Dev Tasks ──────────────────────────────────────────────────
    # Completed task linked to the mockup spec
    completed_task = await dev_svc.create(
        DevTaskCreate(
            title="Voice Analytics Dashboard — Mockup Build",
            spec_id=mockup_spec.id if mockup_spec else None,
            mode="mockup",
        )
    )
    if completed_task:
        for stage_name in ("init", "skills", "implement", "screenshots"):
            await dev_svc.set_stage_status(
                completed_task.id,
                stage_name,
                "completed",
                output=f"{stage_name.capitalize()} stage completed successfully.",
            )
        await dev_svc.set_status(completed_task.id, "completed")
        if mockup_spec:
            await spec_svc.set_dev_task_id(
                mockup_spec.id, completed_task.id, status="developed"
            )

    # Pending task linked to the sequential spec
    await dev_svc.create(
        DevTaskCreate(
            title="Skill Marketplace — Sequential Build",
            spec_id=openspec_spec.id if openspec_spec else None,
            mode="sequential",
        )
    )

    # ── Marketing Videos ───────────────────────────────────────────
    if completed_task:
        video = await marketing_svc.create(
            MarketingVideoCreate(
                title="Voice Analytics Dashboard — Product Demo",
                dev_task_id=completed_task.id,
            )
        )
        if video:
            await marketing_svc.set_status(
                video.id,
                "completed",
                script_content=(
                    "🎬 Intro: 'Meet the Turbo Voice Agent Analytics Dashboard — "
                    "your real-time window into voice AI performance.'\n\n"
                    "📊 Demo: Walk through active sessions, agent routing, "
                    "and latency metrics.\n\n"
                    "✨ Highlight: Show the dark-themed UI with brand gradient "
                    "effects.\n\n"
                    "🚀 CTA: 'Start monitoring your voice agents today with "
                    "Turbo Agent.'"
                ),
                duration_seconds=45,
            )

        await marketing_svc.create(
            MarketingVideoCreate(
                title="Skill Marketplace — Concept Teaser",
                dev_task_id=completed_task.id,
            )
        )

    logger.info("Demo data seeded successfully for user '%s'.", DEMO_USER_ID)
