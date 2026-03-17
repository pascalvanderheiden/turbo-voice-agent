## 1. Infrastructure & Dependencies

- [x] 1.1 Deploy `mistral-document-ai-2512` model to Azure AI Foundry in East US 2
- [x] 1.2 Add `pymupdf` dependency to `backend/pyproject.toml` and install
- [x] 1.3 Add `MISTRAL_DOCUMENT_AI_ENDPOINT` to backend `.env.example` and Bicep env vars

## 2. Backend: Upload & Model

- [x] 2.1 Update `upload.py` to accept `application/pdf` in ALLOWED_TYPES
- [x] 2.2 Add `attachments: list[str]` field to the `Idea` model with empty list default
- [x] 2.3 Update idea routes to pass `attachments` through create/update operations

## 3. Backend: Content Extraction

- [x] 3.1 Create `backend/app/utils/extraction.py` with `extract_pdf_text(file_path) -> str` using PyMuPDF (truncate to ~4000 chars)
- [x] 3.2 Create `extract_image_description(file_path) -> str` in the same module, calling Mistral Document AI endpoint
- [x] 3.3 Add fallback in `extract_image_description` — if Mistral unavailable, return empty string (existing vision behavior used instead)

## 4. Backend: Refinement Integration

- [x] 4.1 Update `brainstorm_agent.py` `refine()` to extract PDF text from attachments and include in prompt context
- [x] 4.2 Update `brainstorm_agent.py` `refine()` to call Mistral for image descriptions and include in prompt context (replace raw base64)
- [x] 4.3 Update `brainstorm_agent.py` `refine_stream()` with the same extraction logic
- [x] 4.4 Process multiple images in parallel using `asyncio.gather`

## 5. Frontend: Upload Component

- [x] 5.1 Update `image-upload.tsx` to accept `application/pdf` alongside images
- [x] 5.2 Show PDF files with a file icon and filename instead of thumbnail preview
- [x] 5.3 Update idea create/edit forms to pass `attachments` field for PDFs separately from `images`

## 6. Testing & Verification

- [ ] 6.1 Test PDF upload via API (verify file stored and URL returned)
- [ ] 6.2 Test idea creation with PDF attachments (verify Cosmos DB persistence)
- [ ] 6.3 Test refinement with PDF — verify extracted text appears in refined output
- [ ] 6.4 Test refinement with images — verify Mistral description included (or fallback)
