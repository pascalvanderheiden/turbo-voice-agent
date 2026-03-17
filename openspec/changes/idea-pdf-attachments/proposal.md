## Why

Ideas currently support image attachments only. Users need to attach PDF documents (specs, research papers, wireframes) to their ideas. During refinement, the AI should extract relevant content from PDFs and use image-to-text (via Mistral Document AI) for attached pictures, embedding extracted information into the refined draft.

## What Changes

- Add PDF upload support alongside existing image uploads (backend + frontend)
- Add a new `attachments` field to the Idea model for PDFs (separate from `images`)
- Extract text from PDFs during refinement using standard PDF parsing (no AI model needed)
- Deploy `mistral-document-ai-2512` to Azure AI Foundry (East US 2) for image-to-text extraction
- During refinement, process images through Mistral Document AI to extract text descriptions before sending to GPT for refinement
- Update the frontend upload component to accept both images and PDFs
- Update the refinement prompt to incorporate extracted PDF text and image descriptions

## Capabilities

### New Capabilities
- `pdf-attachment`: PDF file upload, storage, and text extraction for idea attachments
- `image-to-text`: Image description extraction using Mistral Document AI for richer refinement context

### Modified Capabilities
- None (existing image upload and refinement are extended, not changed at spec level)

## Impact

- **Backend models**: `Idea` model gains `attachments: list[str]` field for PDF URLs
- **Backend routes**: `upload.py` accepts `application/pdf`; `ideas.py` passes attachments to agent
- **Backend agents**: `brainstorm_agent.py` extracts PDF text + calls Mistral for image descriptions before refinement
- **Frontend**: `image-upload.tsx` → `attachment-upload.tsx` supporting both images and PDFs
- **Infrastructure**: New Mistral Document AI deployment in Foundry; new env var `MISTRAL_DOCUMENT_AI_ENDPOINT`
- **Dependencies**: `PyPDF2` or `pymupdf` for PDF text extraction
