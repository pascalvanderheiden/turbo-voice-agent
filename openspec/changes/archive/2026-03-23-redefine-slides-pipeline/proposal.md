## Why

The slides feature needs a significant overhaul. The refined draft is too extensive — it should produce concise, structured output (2 sentences per slide max). Attachments currently accept PDFs and images, but should only accept PowerPoint files (used as templates). The `create-deckio` init variables (title, subtitle, icon, theme, appearance, palette) should come from the slides spec, not be hardcoded. The slides stage should run a single Copilot CLI autopilot invocation with the refined text as prompt. PowerPoint templates should be ported via `--continue` with `/deck-port-powerpoint`. Export should take screenshots instead of PDF, and a new "Run Live" action should expose the deck via `npm run dev` from the sandbox.

## What Changes

- **Refinement**: Produce concise slide content — 2 sentences per slide, structured as title + content pairs. Separate deckio config (title, subtitle, icon, theme, appearance, palette) from slide content in the refined output.
- **Attachments**: Only accept PowerPoint files (`.pptx`), not PDFs or images. These serve as style/layout templates.
- **Init stage**: Execute `npx create-deckio <deck-name>` with variables from the slides spec (title, subtitle, icon, theme, appearance, palette).
- **Slides stage**: Single `copilot --experimental --yolo --autopilot --model claude-opus-4.6 -p "<refined slide content>"`. If a PowerPoint is attached, follow with `copilot --continue -p "/deck-port-powerpoint <blob-url>"`.
- **Export stage**: Run `npm run dev`, take screenshots of every slide (not PDF). Store screenshots on the dev-task.
- **Run Live**: New action button that starts `npm run dev` in the sandbox and exposes the endpoint so the user can view the live deck in their browser.

## Capabilities

### New Capabilities

- `slides-live-preview`: "Run Live" action that exposes the deck-engine dev server from the sandbox for browser access

### Modified Capabilities

- `slides-agent`: Concise refinement (2 sentences/slide), separate deck config, PowerPoint-only attachments
- `slides-pipeline`: Init from spec variables, single autopilot invocation for slides, PowerPoint port via --continue, screenshots instead of PDF export
- `slides-service`: Store deck config fields (theme, appearance, palette, icon, subtitle), PowerPoint-only attachments

## Impact

- Backend: `slides.py` model (deck config fields, drop images), `slides_agent.py` (new refine prompt), `dev_agent.py` (pipeline rewrite), new sandbox endpoint proxy for live preview
- Frontend: `slides/page.tsx` and `slides/[id]/page.tsx` (attachment UI, deck config fields), `development/[id]/page.tsx` (Run Live button, screenshot export)
- API: slides routes (PowerPoint upload, deck config)
