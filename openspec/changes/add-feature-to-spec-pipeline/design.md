## Context

The Turbo Voice Agent platform has a Spec Agent that generates two-part specs (Mockup Description + OpenSpec Config) from brainstormed ideas, and a Dev Agent that executes these specs through a sandboxed GitHub Copilot CLI. Currently, specs are generated as a complete unit — there is no way to incrementally add a feature to an existing spec. Users must regenerate the entire spec to include new ideas, losing any manual edits and forcing dev tasks to restart from scratch.

The redesign-dev-spec-agents change (in progress) establishes the sandbox-based dev pipeline with OpenSpec mode, where the foundation is built first and features are executed in parallel. This creates a natural extension point: if the foundation is already implemented, new features can be appended and built incrementally without restarting the pipeline.

**Stakeholders**: End users (voice-driven spec iteration), Spec Agent (generation), Dev Agent (pipeline execution), Supervisor (routing).

## Goals / Non-Goals

**Goals:**
- Allow users to add individual features to existing specs via voice or UI
- Enhance raw feature descriptions with GPT-5.2 into polished, two-part-format-compliant feature content
- Auto-detect linked dev tasks and append new feature iterations when the foundation is complete
- Trigger incremental dev pipeline execution for newly added features only
- Support both voice ("add dark mode to my spec") and manual (UI button) workflows

**Non-Goals:**
- Rewriting or regenerating the entire spec when a feature is added
- Removing or reordering existing features in a spec
- Supporting feature addition to Mockup mode dev tasks (only OpenSpec mode)
- Multi-spec feature propagation (feature is added to one spec at a time)
- Editing the foundation via this flow — foundation changes require spec regeneration

## Decisions

### 1. Feature enhancement via GPT-5.2 before storage

**Decision**: When a user provides a feature description (via voice or UI), GPT-5.2 enhances it into two artifacts: (a) a Mockup Description paragraph to append to the spec's existing Mockup Description section, and (b) a self-contained `openspec-propose` instruction to append to the OpenSpec Config's Features subsection.

**Rationale**: Raw voice descriptions are typically informal and incomplete ("add dark mode"). GPT-5.2 expansion ensures the feature is detailed enough to drive the sandbox CLI effectively. Using the same model already used for spec generation ensures consistency.

**Alternatives considered**:
- *Store raw description, enhance at dev-time*: Loses the user's chance to review before dev. Rejected.
- *Use a lighter model*: Quality of propose instructions directly impacts sandbox output. GPT-5.2 is already deployed. Rejected.

### 2. Single tool `add_feature_to_spec` exposed to voice and UI

**Decision**: A single new function `add_feature_to_spec(spec_id, description)` handles the full pipeline: enhance → append to spec → detect dev task → append iteration → trigger pipeline.

**Rationale**: Keeping it as one atomic operation simplifies the voice flow — the user says one thing, everything happens. The function runs as a background task (like `generate_spec`) since GPT-5.2 enhancement takes a few seconds.

**Alternatives considered**:
- *Two-step: enhance then add*: Extra voice round-trip, more complex UX. Rejected.
- *Separate add-to-spec and trigger-dev tools*: Forces user to remember two commands. Rejected.

### 3. Foundation-gating for dev task extension

**Decision**: When adding a feature to a spec with a linked OpenSpec dev task:
- If the foundation iteration status is `completed` → immediately append feature iteration and trigger pipeline.
- If the foundation is still `running` or `pending` → append the feature iteration with status `queued` and let the existing pipeline pick it up after foundation completes.
- If there is no dev task → only update the spec, do not create a dev task.

**Rationale**: Features depend on the foundation code. Building a feature before the foundation exists would fail. Queuing handles the race condition cleanly.

### 4. Incremental pipeline execution (feature-only)

**Decision**: When a feature iteration is triggered, the sandbox executes only that feature's `openspec-propose` + `openspec-apply` in the existing project workspace — not a fresh `openspec init`. The dev server restart and Playwright screenshots run after the feature is applied.

**Rationale**: The foundation and previously applied features already exist in the sandbox workspace. Re-initializing would destroy them. The incremental approach mirrors how a developer would add a feature to an existing codebase.

### 5. Spec model append (not replace)

**Decision**: The `add_feature` operation appends to the spec's content string — adding a paragraph to the Mockup Description section and a new `### Feature: <name>` block to the OpenSpec Config Features subsection. The spec's `updatedAt` timestamp is updated.

**Rationale**: Preserves all existing content. The two-part format is designed to be additive — each feature is a self-contained block.

## Risks / Trade-offs

- **[Feature quality variance]** → Voice descriptions may be too vague for GPT-5.2 to produce good propose instructions. Mitigation: The enhancement prompt includes the existing spec context for coherence; the user can review via `get_spec` before triggering dev.
- **[Sandbox workspace state]** → If a previous dev task failed mid-pipeline, the workspace may be in a broken state when a new feature is appended. Mitigation: Check iteration statuses before appending; warn if any prior iteration failed.
- **[Concurrent feature additions]** → Two rapid voice commands could create race conditions on spec content. Mitigation: Spec updates are serialized per-user via the service layer's `with_user()` scoping.
- **[OpenSpec Config format drift]** → If GPT-5.2 produces propose instructions in a slightly different format than the original generation, the sandbox may behave inconsistently. Mitigation: Use a system prompt that includes the existing spec as context and enforces format consistency.

## Open Questions

- Should the user be able to preview the enhanced feature before it's appended, or is immediate append acceptable? (Current decision: immediate append, reviewable after via `get_spec`.)
- Should there be a limit on features per spec to prevent bloat?
