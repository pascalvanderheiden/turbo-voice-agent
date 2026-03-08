## 1. Project Scaffolding
- [x] 1.1 Create `backend/` Python project with FastAPI, pyproject.toml, and dependencies (azure-ai-voicelive, azure-cosmos, azure-identity, agent-framework, fastapi, uvicorn, python-dotenv)
- [x] 1.2 Create `frontend/` Next.js 15 project with TypeScript, Tailwind CSS v4, shadcn/ui (new-york style), Tabler icons, and next-themes
- [x] 1.3 Create `mobile/` Expo SDK 52+ project with React Native 0.82+, TypeScript, and New Architecture
- [x] 1.4 Create `docker-compose.yml` with Cosmos DB Linux emulator
- [x] 1.5 Create root `README.md` with setup instructions and prerequisites
- [ ] 1.6 Copy Turbo Agent logo to `frontend/public/` and `mobile/assets/`

## 2. Database Layer
- [x] 2.1 Implement Cosmos DB client module (`backend/app/db/cosmos.py`) with dual auth (DefaultAzureCredential + emulator), singleton pattern
- [x] 2.2 Define Note Pydantic models (NoteBase, NoteCreate, NoteUpdate, Note, NoteInDB) in `backend/app/models/note.py`
- [x] 2.3 Implement NotesService class (`backend/app/services/notes_service.py`) with CRUD operations, parameterized queries, graceful degradation
- [x] 2.4 Write pytest tests for NotesService (mock Cosmos container, test all CRUD paths and edge cases)
- [x] 2.5 Create database initialization script (`backend/app/db/init.py`) to ensure database and container exist on startup

## 3. REST API
- [x] 3.1 Implement notes REST routes (`backend/app/routes/notes.py`): GET /api/notes, GET /api/notes/{id}, POST /api/notes, PUT /api/notes/{id}, DELETE /api/notes/{id}
- [x] 3.2 Add CORS middleware for local development (allow frontend and mobile origins)
- [x] 3.3 Create FastAPI app entrypoint (`backend/app/main.py`) with lifespan events for Cosmos init
- [x] 3.4 Write API integration tests with httpx/TestClient

## 4. Agent Framework
- [x] 4.1 Implement Notes Agent (`backend/app/agents/notes_agent.py`) with function tools: create_note, get_notes, get_note, update_note, delete_note — all delegating to NotesService
- [x] 4.2 Implement Supervisor Agent (`backend/app/agents/supervisor.py`) using GraphWorkflow with the notes agent as a node
- [x] 4.3 Create agent configuration module (`backend/app/agents/config.py`) with model client setup and system instructions
- [x] 4.4 Write tests for agent tool functions and supervisor routing

## 5. Voice Live Integration
- [x] 5.1 Implement Voice Live session manager (`backend/app/voice/session.py`) — manages Voice Live SDK connection lifecycle, session configuration (ServerVad, noise suppression, echo cancellation, PCM16 24kHz)
- [x] 5.2 Implement function call handler (`backend/app/voice/function_handler.py`) — receives function calls from Voice Live, routes to supervisor agent, returns results
- [x] 5.3 Implement WebSocket endpoint (`backend/app/routes/voice_ws.py`): `/ws/voice` — accepts client audio, proxies to Voice Live, streams response audio back, handles function calling loop
- [x] 5.4 Write tests for function call routing and session lifecycle

## 6. Web Frontend — Branding & Layout
- [x] 6.1 Configure Turbo Agent color system (CSS variables + Tailwind v4 theme) with dark mode default
- [x] 6.2 Set up typography (Inter for UI, JetBrains Mono for code)
- [x] 6.3 Build root layout with ThemeProvider, dark mode default
- [x] 6.4 Build AppSidebar with collapsible navigation: Dashboard, Notes, Voice Mode
- [x] 6.5 Build SiteHeader with breadcrumbs and theme toggle

## 7. Web Frontend — Notes UI
- [x] 7.1 Build notes list page (`/notes`) with data table showing title, excerpt, created/updated timestamps
- [x] 7.2 Build create note dialog/page with title + content fields
- [x] 7.3 Build edit note page/dialog with pre-populated fields
- [x] 7.4 Build delete note confirmation dialog
- [x] 7.5 Implement API client module (`frontend/lib/api.ts`) for notes CRUD
- [x] 7.6 Add loading states, error handling, and toast notifications (sonner)

## 8. Web Frontend — Voice Mode
- [x] 8.1 Build voice mode page (`/voice`) with centered voice orb
- [x] 8.2 Implement voice orb component with five state animations: idle (breathing pulse), listening (audio-reactive ripples), thinking (swirl), speaking (rhythmic pulse), error (shake + red tint)
- [x] 8.3 Implement WebSocket audio client — connect to `/ws/voice`, capture microphone audio (PCM16 24kHz), send audio chunks, receive and play response audio
- [x] 8.4 Add voice activation button in the site header for quick access
- [x] 8.5 Implement transcript display showing conversation history below the orb

## 9. iOS Mobile App
- [x] 9.1 Configure Expo project with New Architecture, TypeScript strict mode
- [x] 9.2 Set up navigation (React Navigation v7) with tabs: Notes, Voice
- [x] 9.3 Apply Turbo Agent branding (dark mode default, color palette, Inter font)
- [x] 9.4 Build notes list screen with pull-to-refresh
- [x] 9.5 Build create/edit note screen with form inputs
- [x] 9.6 Build delete note with swipe action or confirmation
- [x] 9.7 Implement API client for notes CRUD (fetch from backend)
- [x] 9.8 Build voice mode screen with voice orb (matching web animations)
- [x] 9.9 Implement WebSocket audio client for iOS — microphone capture, audio streaming, playback
- [x] 9.10 Add voice activation button in tab bar or header

## 10. Integration & Polish
- [ ] 10.1 End-to-end test: create note via voice → verify in notes UI → edit via UI → verify via voice
- [ ] 10.2 End-to-end test: same flow on iOS
- [x] 10.3 Add `.env.example` files for backend, frontend, and mobile with all required variables
- [x] 10.4 Write developer setup documentation in root README
