"""FastAPI application entrypoint."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agents.brainstorm_agent import BrainstormAgent
from app.agents.dev_agent import DevAgent
from app.agents.marketing_agent import MarketingAgent
from app.agents.notes_agent import NotesAgent
from app.agents.research_agent import ResearchAgent
from app.agents.skills_agent import SkillsAgent
from app.agents.slides_agent import SlidesAgent
from app.agents.spec_agent import SpecAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.todo_agent import TodoAgent
from app.agents.work_agent import WorkAgent
from app.db.cosmos import close_cosmos_client, get_cosmos_client
from app.db.init import ensure_database_and_containers
from app.mcp.todo_mcp_client import TodoMcpClient
from app.mcp.work_mcp_client import WorkMcpClient
from app.middleware.auth_middleware import EntraAuthMiddleware
from app.routes import (
    chat,
    dev,
    ideas,
    marketing,
    notes,
    research,
    slides,
    specs,
    todos,
    upload,
    voice_ws,
)
from app.routes import sandbox as sandbox_routes
from app.routes.user import router as user_router
from app.services.brainstorm_service import BrainstormService
from app.services.slides_service import SlidesService
from app.services.cosmos_dev_service import DevService
from app.services.cosmos_marketing_service import MarketingService
from app.services.cosmos_skills_service import CosmosSkillsService
from app.services.dev_service import InMemoryDevService
from app.services.inmemory_sandbox_service import InMemorySandboxService
from app.services.memory_brainstorm_service import InMemoryBrainstormService
from app.services.memory_slides_service import InMemorySlidesService
from app.services.memory_marketing_service import InMemoryMarketingService
from app.services.memory_research_service import InMemoryResearchService
from app.services.memory_spec_service import InMemorySpecService
from app.services.notes_service import NotesService
from app.services.research_client import run_deep_research, run_web_search
from app.services.research_service import ResearchService
from app.services.sandbox_service import SandboxService as CosmosSandboxService
from app.services.skills_service import SkillsService
from app.services.spec_service import SpecService
from app.services.user_profile_service import UserProfileService

load_dotenv()

from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def _resolve_local_skills_dir() -> "Path | None":
    """Resolve the local skills directory for disk-based skill persistence.

    Precedence:
      1. ``LOCAL_SKILLS_DIR`` env var (absolute path)
      2. ``{project_root}/.agents/skills/`` derived from the backend dir

    Returns ``None`` only if the directory cannot be determined.
    """
    from pathlib import Path

    env_val = os.environ.get("LOCAL_SKILLS_DIR")
    if env_val:
        p = Path(env_val)
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Derive from backend dir: backend/app/main.py → backend → project_root
    backend_dir = Path(__file__).resolve().parent.parent  # backend/
    project_root = backend_dir.parent  # project root
    skills_dir = project_root / ".agents" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init Cosmos DB and agents. Shutdown: close client."""
    logger.info("Starting Turbo Voice Agent backend...")

    # Initialize Cosmos DB
    notes_service = None
    brainstorm_service = None
    slides_service = None
    research_service = None
    spec_service = None
    dev_service = None
    marketing_service = None
    try:
        client = await get_cosmos_client()
        await ensure_database_and_containers(client)
        notes_service = NotesService(client)
        brainstorm_service = BrainstormService(client)
        slides_service = SlidesService(client)
        research_service = ResearchService(client)
        spec_service = SpecService(client)
        dev_service = DevService(client)
        marketing_service = MarketingService(client)
        logger.info("Cosmos DB connected — using persistent storage.")
    except Exception as exc:
        logger.warning("Cosmos DB unavailable — using in-memory storage. Error: %s", exc)
        client = None

    # Initialize skills services
    cosmos_skills = None
    skills_service = SkillsService()
    if client:
        try:
            cosmos_skills = CosmosSkillsService(client)
            logger.info("Cosmos skills service initialized.")
        except Exception:
            logger.exception("Failed to init Cosmos skills service.")

    # Fallback to in-memory if Cosmos isn't available
    if cosmos_skills is None:
        from app.services.in_memory_skills_service import InMemorySkillsService

        local_skills_dir = _resolve_local_skills_dir()
        cosmos_skills = InMemorySkillsService(local_skills_dir=local_skills_dir)
        logger.warning(
            "Using in-memory skills service (data will not persist). LOCAL_SKILLS_DIR=%s",
            local_skills_dir,
        )

    # User profile service
    app.state.user_profile_service = None
    if client:
        try:
            db = client.get_database_client(os.environ.get("COSMOS_DATABASE", "turbovoice"))
            profiles_container = db.get_container_client("profiles")
            app.state.user_profile_service = UserProfileService(profiles_container)
            logger.info("User profile service initialized")
        except Exception as e:
            logger.warning("Failed to init user profile service: %s", e)

    # Fallback to in-memory if Cosmos isn't available
    if notes_service is None:
        from app.services.memory_notes_service import InMemoryNotesService

        notes_service = InMemoryNotesService()
        logger.info("In-memory notes service initialized.")

    if brainstorm_service is None:
        brainstorm_service = InMemoryBrainstormService()
        logger.info("In-memory brainstorm service initialized.")

    if slides_service is None:
        slides_service = InMemorySlidesService()
        logger.info("In-memory slides service initialized.")

    if research_service is None:
        research_service = InMemoryResearchService()
        logger.info("In-memory research service initialized.")

    if spec_service is None:
        spec_service = InMemorySpecService()
        logger.info("In-memory spec service initialized.")

    if dev_service is None:
        dev_service = InMemoryDevService()
        logger.info("In-memory dev service initialized.")

    if marketing_service is None:
        marketing_service = InMemoryMarketingService()
        logger.info("In-memory marketing service initialized.")

    # Initialize Sandbox Service
    sandbox_service = None
    if client:
        try:
            sandbox_service = CosmosSandboxService(client)
            logger.info("Cosmos sandbox service initialized.")
        except Exception:
            logger.warning("Failed to init Cosmos sandbox service — using in-memory.")
    if sandbox_service is None:
        sandbox_service = InMemorySandboxService()
        logger.info("In-memory sandbox service initialized.")

    # Initialize agents
    notes_agent = NotesAgent(notes_service)
    brainstorm_agent = BrainstormAgent(brainstorm_service, research_service=research_service)
    slides_agent = SlidesAgent(slides_service, research_service=research_service)
    research_agent = ResearchAgent(research_service)
    spec_agent = SpecAgent(
        spec_service, brainstorm_service=brainstorm_service, research_service=research_service
    )
    dev_agent = DevAgent(
        dev_service,
        spec_service=spec_service,
        skills_service=skills_service,
        cosmos_skills=cosmos_skills,
        slides_service=slides_service,
        profile_service=app.state.user_profile_service,
    )
    # Wire dev_agent into spec_agent for add_feature_to_spec pipeline
    spec_agent._dev_agent = dev_agent
    # Expose dev_service so route handlers (e.g. GitHub disconnect) can enumerate
    # a user's active dev-tasks to release per-task sandbox sessions.
    app.state.dev_service = dev_service
    skills_agent = SkillsAgent(
        skills_service,
        cosmos_skills=cosmos_skills,
        sync_sandbox=_sync_sandbox_skills,
        delete_sandbox_skill=_delete_sandbox_skill,
    )
    marketing_agent = MarketingAgent(
        marketing_service,
        dev_service=dev_service,
        spec_service=spec_service,
        profile_service=app.state.user_profile_service,
    )

    # Initialize MCP client and Todo Agent
    from app.routes.user import get_todo_user_token

    todo_mcp_client = TodoMcpClient()
    await todo_mcp_client.start()

    async def _todo_token_resolver(user_id: str) -> str | None:
        return await get_todo_user_token(user_id, app_state=app.state)

    todo_agent = TodoAgent(todo_mcp_client, get_user_token=_todo_token_resolver)

    # Initialize Work MCP client and Work Agent
    from app.routes.user import get_work_user_token

    work_mcp_client = WorkMcpClient()
    await work_mcp_client.start()

    async def _work_token_resolver(user_id: str) -> str | None:
        return await get_work_user_token(user_id, app_state=app.state)

    work_agent = WorkAgent(work_mcp_client, get_user_token=_work_token_resolver)

    supervisor = SupervisorAgent(
        notes_agent,
        brainstorm_agent,
        research_agent,
        spec_agent,
        dev_agent,
        skills_agent,
        marketing_agent=marketing_agent,
        todo_agent=todo_agent,
        slides_agent=slides_agent,
        work_agent=work_agent,
    )

    notes.set_notes_service(notes_service)
    ideas.set_brainstorm_service(
        brainstorm_service,
        refine_fn=brainstorm_agent.refine,
        refine_stream_fn=brainstorm_agent.refine_stream,
    )
    ideas.set_idea_research_service(research_service)
    slides.set_slides_service(
        slides_service,
        refine_fn=slides_agent.refine,
        refine_stream_fn=slides_agent.refine_stream,
        parse_deck_config_fn=slides_agent.parse_deck_config,
    )
    slides.set_slides_research_service(research_service)
    research.set_research_service(research_service, run_web_search, run_deep_research)
    specs.set_spec_service(
        spec_service,
        optimize_fn=spec_agent.optimize,
        generate_fn=spec_agent.generate_from_idea,
        add_feature_fn=spec_agent.add_feature_to_spec,
        brainstorm_service=brainstorm_service,
    )
    voice_ws.set_supervisor(supervisor)
    chat.set_supervisor(supervisor)
    dev.set_dev_service(
        dev_service,
        pipeline_fn=dev_agent.run_pipeline,
        skills_service=skills_service,
        cosmos_skills=cosmos_skills,
        spec_service=spec_service,
        dev_agent=dev_agent,
    )
    sandbox_routes.set_sandbox_service(sandbox_service)
    marketing.set_marketing_service(marketing_service, agent=marketing_agent)
    todos.set_todo_agent(todo_agent)
    global _skills_service, _cosmos_skills
    _skills_service = skills_service
    _cosmos_skills = cosmos_skills
    logger.info("Services and agents initialized.")

    # Seed demo data when running with in-memory services (no Cosmos DB)
    if client is None:
        from app.seed_data import seed_demo_data

        await seed_demo_data(
            notes_service=notes_service,
            brainstorm_service=brainstorm_service,
            research_service=research_service,
            spec_service=spec_service,
            dev_service=dev_service,
            marketing_service=marketing_service,
        )

    # Recovery: mark any "running" dev-tasks as failed (orphaned by container restart)
    if dev_service and hasattr(dev_service, "_container"):
        try:
            from azure.cosmos import exceptions as cosmos_exc

            query = "SELECT c.id, c.userId FROM c WHERE c.status = 'running'"
            items = dev_service._container.query_items(query, enable_cross_partition_query=True)
            recovered = 0
            async for item in items:
                uid = item.get("userId")
                tid = item.get("id")
                if uid and tid:
                    try:
                        svc = dev_service.with_user(uid)
                        await svc.set_status(tid, "failed")
                        recovered += 1
                        logger.warning("Recovered orphaned running task %s → failed", tid)
                    except Exception:
                        logger.warning("Failed to recover task %s", tid)
            if recovered:
                logger.info("Recovered %d orphaned running dev-tasks on startup", recovered)
        except Exception:
            logger.debug("Dev-task recovery skipped (non-fatal)")

    # Auto-start local Docker sandbox when running outside Azure
    # (Azure deployments use the dynamic session pool via SessionSandboxClient.)
    docker_sandbox_svc = None
    if (
        not os.getenv("SESSION_POOL_MANAGEMENT_ENDPOINT")
        and os.getenv("AUTO_START_SANDBOX", "true").lower() != "false"
    ):
        try:
            from app.services.docker_sandbox_service import DockerSandboxService

            docker_sandbox_svc = DockerSandboxService()
            if docker_sandbox_svc.available:
                healthy = await docker_sandbox_svc.start()
                if healthy:
                    logger.info("Local Docker sandbox auto-started successfully")
                else:
                    logger.warning(
                        "Local Docker sandbox failed to start — "
                        "dev pipelines will fail until sandbox is available. "
                        "Try 'docker compose up -d sandbox' manually."
                    )
            else:
                logger.debug("Docker not available — skipping sandbox auto-start")
                docker_sandbox_svc = None
        except Exception as exc:
            logger.debug("Docker sandbox auto-start skipped: %s", exc)
            docker_sandbox_svc = None

    yield

    # Shutdown
    if docker_sandbox_svc:
        await docker_sandbox_svc.stop()
    await todo_mcp_client.stop()
    await work_mcp_client.stop()
    await close_cosmos_client()
    logger.info("Backend shut down.")


app = FastAPI(
    title="Turbo Voice Agent",
    version="0.4.0",
    lifespan=lifespan,
)

# Request logging middleware (innermost — runs after auth sets user_id)
from app.middleware.logging_middleware import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)

# Auth middleware (before CORS)
app.add_middleware(EntraAuthMiddleware)

# CORS for authenticated requests
_allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8081"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploads
app.mount("/uploads", StaticFiles(directory=str(upload.UPLOAD_DIR)), name="uploads")

# Static file serving for mobile assets
from pathlib import Path

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Register routes
app.include_router(notes.router)
app.include_router(ideas.router)
app.include_router(slides.router)
app.include_router(research.router)
app.include_router(specs.router)
app.include_router(dev.router)
app.include_router(marketing.router)
app.include_router(todos.router)
app.include_router(upload.router)
app.include_router(voice_ws.router)
app.include_router(chat.router)
app.include_router(user_router)
app.include_router(sandbox_routes.router)


@app.get("/health")
async def health():
    """Health check with dependency status."""
    checks = {"cosmos": "unknown", "blob": "unknown"}
    overall = "healthy"

    # Check Cosmos DB
    try:
        client = await get_cosmos_client()
        db = client.get_database_client(os.environ.get("COSMOS_DATABASE", "turbovoice"))
        await db.read()
        checks["cosmos"] = "healthy"
    except Exception:
        checks["cosmos"] = "degraded"
        overall = "degraded"

    # Check Blob Storage
    storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME")
    if storage_account:
        checks["blob"] = "configured"
    else:
        checks["blob"] = "not_configured"

    status_code = 200 if overall == "healthy" else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks, "version": "0.4.0"},
    )


@app.get("/api/agents/status")
async def agent_status():
    """Return agent topology and live usage stats."""
    return {
        "agents": [
            {
                "id": "voice",
                "name": "Voice Live",
                "type": "gateway",
                "model": "gpt-realtime",
                "transcriptionModel": "gpt-4o-transcribe",
                "status": "online",
            },
            {
                "id": "chat",
                "name": "Chat",
                "type": "gateway",
                "model": "gpt-5.2",
                "status": "online",
            },
            {
                "id": "supervisor",
                "name": "Supervisor",
                "type": "orchestrator",
                "status": "online",
            },
            {
                "id": "notes",
                "name": "Notes Agent",
                "type": "specialist",
                "model": "gpt-5.2",
                "status": "online",
                "tools": ["create_note", "get_notes", "get_note", "update_note", "delete_note"],
            },
            {
                "id": "brainstorm",
                "name": "Brainstorm Agent",
                "type": "specialist",
                "model": "gpt-5.2 + mistral-document-ai-2512",
                "status": "online",
                "tools": [
                    "create_idea",
                    "get_ideas",
                    "get_idea",
                    "update_idea",
                    "delete_idea",
                    "refine_idea",
                ],
            },
            {
                "id": "research",
                "name": "Research Agent",
                "type": "specialist",
                "model": "gpt-4.1 / o3-deep-research",
                "status": "online",
                "tools": [
                    "web_search",
                    "deep_research",
                    "get_research_list",
                    "get_research",
                    "delete_research",
                ],
            },
            {
                "id": "spec",
                "name": "Spec Agent",
                "type": "specialist",
                "model": "gpt-5.2",
                "status": "online",
                "tools": [
                    "create_spec",
                    "get_specs",
                    "get_spec",
                    "update_spec",
                    "delete_spec",
                    "generate_spec",
                    "optimize_spec",
                ],
            },
            {
                "id": "dev",
                "name": "Turbo Dev Agent",
                "type": "specialist",
                "model": "GitHub Copilot CLI (Sandbox)",
                "status": "online",
                "tools": [
                    "create_dev_task",
                    "get_dev_tasks",
                    "get_dev_task",
                    "delete_dev_task",
                    "trigger_dev_pipeline",
                ],
                "mcpServers": ["playwright"],
            },
            {
                "id": "skills",
                "name": "Skills Agent",
                "type": "specialist",
                "model": "gpt-5.2",
                "status": "online",
                "tools": ["install_skill", "uninstall_skill", "search_skills", "list_skills"],
            },
            {
                "id": "marketing",
                "name": "Marketing Agent",
                "type": "specialist",
                "model": "sora-2",
                "scriptModel": "gpt-5.2",
                "status": "online",
                "tools": [
                    "create_marketing_video",
                    "get_marketing_videos",
                    "get_marketing_video",
                    "delete_marketing_video",
                    "trigger_video_generation",
                ],
            },
            {
                "id": "slides",
                "name": "Slides Agent",
                "type": "specialist",
                "model": "gpt-5.2",
                "status": "online",
                "tools": [
                    "create_slides",
                    "get_slides_list",
                    "get_slides",
                    "update_slides",
                    "delete_slides",
                    "refine_slides",
                ],
            },
            {
                "id": "todo",
                "name": "Todo Agent",
                "type": "specialist",
                "model": "gpt-5.2",
                "status": "online",
                "tools": [
                    "create_todo",
                    "get_todos",
                    "get_todo",
                    "update_todo",
                    "delete_todo",
                    "complete_todo",
                ],
                "mcpServers": ["microsoft-todo"],
            },
            {
                "id": "work",
                "name": "Work Agent",
                "type": "specialist",
                "model": "gpt-5.2",
                "status": "online",
                "tools": ["ask_work_question"],
                "mcpServers": ["workiq"],
            },
        ],
        "edges": [
            {"from": "voice", "to": "supervisor"},
            {"from": "chat", "to": "supervisor"},
            {"from": "supervisor", "to": "notes"},
            {"from": "supervisor", "to": "brainstorm"},
            {"from": "supervisor", "to": "research"},
            {"from": "supervisor", "to": "spec"},
            {"from": "supervisor", "to": "dev"},
            {"from": "supervisor", "to": "skills"},
            {"from": "supervisor", "to": "marketing"},
            {"from": "supervisor", "to": "slides"},
            {"from": "supervisor", "to": "todo"},
            {"from": "supervisor", "to": "work"},
        ],
    }


_skills_service: SkillsService | None = None
_cosmos_skills: CosmosSkillsService | None = None


async def _sync_sandbox_skills() -> dict | None:
    """Push skill sync to sandbox (best-effort). Returns response or None."""
    sandbox_url = os.getenv("SANDBOX_URL", "http://localhost:4000")
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{sandbox_url}/skills/sync")
            resp.raise_for_status()
            result = resp.json()
            logger.info("Sandbox skill sync: %s", result)
            return result
    except Exception as exc:
        # Suppress noisy connection errors when sandbox isn't running (local dev)
        exc_name = type(exc).__name__
        if "Connect" in exc_name:
            logger.debug("Sandbox skill sync skipped — sandbox not reachable at %s", sandbox_url)
        else:
            logger.warning("Sandbox skill sync failed (non-fatal): %s", exc)
        return None


async def _delete_sandbox_skill(name: str) -> dict | None:
    """Remove a skill from sandbox (best-effort). Returns response or None."""
    sandbox_url = os.getenv("SANDBOX_URL", "http://localhost:4000")
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(f"{sandbox_url}/skills/{name}")
            resp.raise_for_status()
            result = resp.json()
            logger.info("Sandbox skill delete '%s': %s", name, result)
            return result
    except Exception as exc:
        exc_name = type(exc).__name__
        if "Connect" in exc_name:
            logger.debug(
                "Sandbox skill delete '%s' skipped — sandbox not reachable at %s",
                name,
                sandbox_url,
            )
        else:
            logger.warning("Sandbox skill delete '%s' failed (non-fatal): %s", name, exc)
        return None


@app.get("/api/agents/skills")
async def list_installed_skills(request: Request):
    """List activated skills for the current user."""
    user_id = getattr(request.state, "user_id", "default-user")
    if _cosmos_skills:
        svc = _cosmos_skills.with_user(user_id)
        skills = await svc.list_activated()
        return {"skills": skills}
    return {"skills": []}


@app.get("/api/agents/skills/search")
async def search_marketplace_skills(q: str = ""):
    """Proxy to skills.sh marketplace search."""
    svc = _skills_service or SkillsService()
    results = await svc.search_marketplace(q)
    return {"results": results}


class SkillInstallRequest(BaseModel):
    repo: str
    skillName: str
    npxCommand: str | None = None
    description: str | None = None


@app.post("/api/agents/skills/install")
async def activate_skill(body: SkillInstallRequest, request: Request):
    """Activate a skill — store metadata and upload files to blob storage."""
    user_id = getattr(request.state, "user_id", "default-user")
    if not _cosmos_skills:
        return {"error": "Skills service not available"}
    svc = _cosmos_skills.with_user(user_id)
    is_local = body.repo == "local"
    npx_cmd = body.npxCommand or (
        "__local__"
        if is_local
        else f"npx -y degit {body.repo}/{body.skillName} .github/skills/{body.skillName}"
    )
    result = await svc.activate_skill(body.skillName, body.description or "", body.repo, npx_cmd)

    # For marketplace skills, download from GitHub and upload to blob storage
    # so they're pre-synced like local skills (no slow npx install at pipeline time)
    blob_uploaded = 0
    if not is_local and body.repo:
        uploaded = await svc.upload_skill_from_github_to_blob(body.skillName, body.repo)
        if uploaded:
            blob_uploaded = len(uploaded)
            # Mark as blob-stored — runtime treats it like a local skill (no npx needed)
            await svc.activate_skill(
                body.skillName,
                body.description or "",
                body.repo,
                "__local__",
            )
            logger.info(
                "Marketplace skill '%s' uploaded to blob (%d files)",
                body.skillName,
                blob_uploaded,
            )

    logger.info("Activated skill '%s' for user=%s", body.skillName, user_id)

    # Hot-reload: push to running sandbox immediately
    await _sync_sandbox_skills()

    return {"name": result["name"], "success": True, "blobFiles": blob_uploaded}


@app.delete("/api/agents/skills/{name}")
async def deactivate_skill(name: str, request: Request):
    """Deactivate a skill by name."""
    user_id = getattr(request.state, "user_id", "default-user")
    if not _cosmos_skills:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Skills service not available")
    svc = _cosmos_skills.with_user(user_id)
    await svc.deactivate_skill(name)
    logger.info("Deactivated skill '%s' for user=%s", name, user_id)

    # Hot-reload: remove from running sandbox immediately
    await _delete_sandbox_skill(name)

    return {"name": name, "success": True}


@app.get("/api/specs/{spec_id}/dev-task")
async def get_spec_dev_task(spec_id: str, request: Request):
    """Get the dev task linked to a spec."""
    user_id = getattr(request.state, "user_id", "default-user")
    spec_svc = specs._spec_service
    if not spec_svc:
        return {"devTask": None}
    spec = await spec_svc.with_user(user_id).get_by_id(spec_id)
    if not spec or not spec.dev_task_id:
        return {"devTask": None}
    dev_svc = dev._dev_service
    if not dev_svc:
        return {"devTask": None}
    task = await dev_svc.with_user(user_id).get_by_id(spec.dev_task_id)
    if not task:
        return {"devTask": None}
    return {
        "devTask": {"id": task.id, "title": task.title, "mode": task.mode, "status": task.status}
    }
