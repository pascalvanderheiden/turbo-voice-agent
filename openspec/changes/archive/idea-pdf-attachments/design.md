## Context

Ideas currently support image attachments (`images: list[str]`) stored as local files via `/api/upload`. During refinement, images are base64-encoded and sent to GPT-5.2 via vision content parts. The user wants to add PDF support and improve image processing by extracting text descriptions via Mistral Document AI before refinement.

Current flow: Upload image → store locally → refinement reads file, base64-encodes, sends as vision input to GPT.

Target flow: Upload image/PDF → store locally → on refinement: extract PDF text (PyMuPDF), extract image descriptions (Mistral Document AI) → include extracted text in refinement prompt → GPT refines with full context.

## Goals / Non-Goals

**Goals:**
- Support PDF file uploads on ideas (alongside existing images)
- Extract text from PDFs during refinement using PyMuPDF (no AI model needed)
- Deploy Mistral Document AI (`mistral-document-ai-2512`) to Foundry East US 2
- Use Mistral Document AI to extract text descriptions from images during refinement
- Include extracted PDF text and image descriptions as context in the refinement prompt
- Update frontend to accept both images and PDFs in a unified upload component

**Non-Goals:**
- OCR on scanned PDFs (PyMuPDF handles text-based PDFs; scanned PDFs are out of scope)
- PDF rendering/preview in the frontend (just show filename + icon)
- Changing existing image display behavior (thumbnails stay as-is)
- Real-time document processing (extraction happens only during refinement)

## Decisions

1. **Separate fields for images and attachments**: Keep `images: list[str]` for backward compatibility. Add `attachments: list[str]` for PDFs. The upload endpoint accepts both types.

2. **PyMuPDF for PDF text extraction**: Use `pymupdf` (PyMuPDF) — lightweight, no external service needed, works locally and in Azure. Extracts text page-by-page.

3. **Mistral Document AI for image-to-text**: Deploy `mistral-document-ai-2512` model in Foundry. Call it during refinement to get a text description of each image. This replaces sending raw base64 images to GPT — instead, the extracted text goes into the prompt.

4. **Extraction at refinement time, not upload time**: Don't extract on upload — do it when refinement is triggered. This keeps upload fast and avoids storing extracted text separately.

5. **Text context injection**: Extracted PDF text and image descriptions are prepended to the user message in the refinement prompt, before the idea title/description. GPT sees: `[PDF extracts] + [image descriptions] + idea title + description`.

## Risks / Trade-offs

- **Large PDFs**: Text extraction could produce very large content. Mitigation: truncate extracted text to ~4000 chars per PDF, prioritize first pages.
- **Mistral latency**: Image-to-text adds latency to refinement. Mitigation: process images in parallel, cache descriptions if needed later.
- **PyMuPDF dependency**: Adds a native dependency. Low risk — well-maintained, no C++ build issues on common platforms.
