## Context

The slides pipeline currently scaffolds a deck-engine project with hardcoded values (theme: shadcn/ui, appearance: dark, palette: arctic), generates an overly verbose refined draft, accepts PDFs and images as attachments, iterates slide-by-slide with Copilot CLI, and exports to PDF. The user wants a simpler, more effective approach: concise refinement, PowerPoint-only templates, single autopilot invocation, screenshot-based export, and a live preview mode.

The `create-deckio` CLI accepts: title, subtitle, icon, theme (shadcn/ui), appearance (dark/light), and aurora palette (arctic/forest/ocean/sunset/etc.). These should be user-configurable per slides spec.

## Goals / Non-Goals

**Goals:**
- Concise 2-sentence-per-slide refinement with deck config separated
- PowerPoint-only attachments as style templates
- Init with user-specified deck config (theme, appearance, palette, etc.)
- Single Copilot CLI autopilot invocation for entire slide generation
- PowerPoint template porting via `--continue` + `/deck-port-powerpoint`
- Screenshot-based export (one per slide)
- "Run Live" action exposing sandbox dev server to browser

**Non-Goals:**
- Changing the deck-engine or create-deckio tooling itself
- PDF export (replaced by screenshots)
- Multi-image or PDF attachment support (PowerPoint only)

## Decisions

### 1. Refinement output structure

The refined output will have two sections:
1. **Deck Config** (YAML block): `title`, `subtitle`, `icon`, `theme`, `appearance`, `palette`
2. **Slides** (numbered list): Each slide has a title + 2 sentences of content

This keeps the prompt to Copilot CLI focused and prevents over-generation.

### 2. Single autopilot invocation for slides stage

Instead of iterating slide-by-slide, pass the entire refined slide content as one prompt:
```
copilot --experimental --yolo --autopilot --model <model> --agent squad -p "<all slides content>"
```
This is faster and gives the agent full context to create a cohesive deck.

### 3. PowerPoint template porting

If a `.pptx` is attached, after the main slides invocation, run:
```
copilot --continue -p "/deck-port-powerpoint <blob-url>"
```
The `--continue` preserves the deck context. The sandbox can fetch the blob URL directly.

### 4. Live preview via sandbox port exposure

The sandbox already supports exposing ports. "Run Live" will:
1. Run `npm run dev` in the deck workspace (starts on port 3000)
2. Proxy the sandbox port to a public URL
3. Open/display the URL in the dev-task detail page

### 5. Screenshots replace PDF

Export stage runs `npm run dev`, navigates each slide route with Playwright, takes PNG screenshots. These are stored as dev-task screenshots (existing mechanism), not as a PDF blob.

## Risks / Trade-offs

- [Single prompt may exceed context] → The refined content is concise (2 sentences × N slides), so context limits are unlikely. Fallback: split into chunks.
- [PowerPoint port quality] → Depends on `/deck-port-powerpoint` skill quality. Non-blocking: deck works without template too.
- [Sandbox port exposure security] → Live preview URL should be scoped to the user's session. Use existing sandbox auth.
