## 1. Backend — Image Upload
- [ ] 1.1 Create `POST /api/upload` endpoint (accept multipart, store to `uploads/`, return URL)
- [ ] 1.2 Mount `/uploads/` as static files in FastAPI
- [ ] 1.3 Add upload size limit (10MB) and allowed types (png, jpg, jpeg, gif, webp)

## 2. Backend — Brainstorm Service
- [ ] 2.1 Create `Idea` Pydantic models (IdeaBase, IdeaCreate, IdeaUpdate, Idea) with `images: list[str]` field
- [ ] 2.2 Create `InMemoryBrainstormService` with CRUD (same pattern as notes)
- [ ] 2.3 Create `BrainstormService` Cosmos DB implementation
- [ ] 2.4 Create `POST /api/ideas`, `GET /api/ideas`, `GET /api/ideas/{id}`, `PUT /api/ideas/{id}`, `DELETE /api/ideas/{id}` REST routes
- [ ] 2.5 Create `POST /api/ideas/{id}/refine` endpoint that calls GPT-5.2 to produce a refined draft

## 3. Backend — Brainstorm Agent
- [ ] 3.1 Create `BrainstormAgent` with tool definitions: `create_idea`, `get_ideas`, `get_idea`, `update_idea`, `delete_idea`, `refine_idea`
- [ ] 3.2 Implement `handle_function_call` routing to BrainstormService
- [ ] 3.3 Implement `refine_idea` using GPT-5.2 chat completions with vision (include images if attached)

## 4. Backend — Supervisor Update
- [ ] 4.1 Register `BrainstormAgent` in supervisor
- [ ] 4.2 Add brainstorm function routing in `handle_function_call`
- [ ] 4.3 Return `"Brainstorm Agent"` as agent name for notifications

## 5. Backend — Notes Image Support
- [ ] 5.1 Add `images: list[str]` optional field to Note models
- [ ] 5.2 Update NotesService and InMemoryNotesService to persist images field
- [ ] 5.3 Update Notes REST routes to accept/return images

## 6. Backend — Voice Session Update
- [ ] 6.1 Add brainstorm tool definitions to `build_session_tools()`
- [ ] 6.2 Update voice instructions to mention brainstorm capabilities
- [ ] 6.3 Update EN/NL greetings to mention brainstorming

## 7. Frontend — Image Upload Component
- [ ] 7.1 Create reusable `ImageUpload` component (drag & drop, click to browse, camera on mobile)
- [ ] 7.2 Support preview thumbnails and removal
- [ ] 7.3 Call `POST /api/upload` and return URL array

## 8. Frontend — Brainstorm Pages
- [ ] 8.1 Create `/ideas` page with list table (title, status, image count, updated)
- [ ] 8.2 Create idea dialog with title, description, image upload
- [ ] 8.3 Create idea detail view showing refined draft (markdown rendered)
- [ ] 8.4 Add "Refine" button that calls `/api/ideas/{id}/refine` and shows result
- [ ] 8.5 Add edit and delete dialogs

## 9. Frontend — Notes Image Support
- [ ] 9.1 Add `ImageUpload` component to notes create/edit dialog
- [ ] 9.2 Display image thumbnails in notes list and detail view
- [ ] 9.3 Update API types to include `images` field

## 10. Frontend — Navigation & i18n
- [ ] 10.1 Add "Ideas" / "Ideeën" to sidebar navigation
- [ ] 10.2 Add all brainstorm-related translation keys (EN/NL)
- [ ] 10.3 Add brainstorm action labels for notifications

## 11. Frontend — Voice Mode Update
- [ ] 11.1 Add brainstorm action labels to `ACTION_LABELS` in voice page

## 12. Mobile — Brainstorm & Image Support
- [ ] 12.1 Create Ideas tab with list screen
- [ ] 12.2 Create idea form screen with image picker (camera + gallery)
- [ ] 12.3 Create idea detail screen with refined draft
- [ ] 12.4 Add image picker to notes form screen
