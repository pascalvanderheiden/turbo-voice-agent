## Why

Users need to incrementally add features to existing specs — via voice command or the web UI — without regenerating the entire spec. When a feature is added, it should be AI-enhanced using GPT-5.2 for quality, and if the spec already has an active OpenSpec dev task with its foundation implemented, the new feature should automatically be appended to the dev task and kick off the dev pipeline for that feature alone.

## What Changes

- **New voice command & UI action**: `add_feature_to_spec` — accepts a spec ID and a feature description (brief or detailed). Works via voice ("add dark mode to my spec") or the spec detail UI.
- **GPT-5.2 enhancement**: When a feature is added, GPT-5.2 enhances the raw description into a polished feature spec (Mockup Description addition + OpenSpec Config `openspec-propose` instruction), consistent with the existing two-part spec format.
- **Auto-extend dev task**: When a spec has a linked dev task in OpenSpec mode, and the foundation iteration is already completed, the new feature is automatically added as a new iteration on the dev task.
- **Auto-trigger dev pipeline**: After appending the feature iteration, the dev pipeline is automatically triggered for that feature only (not re-running foundation or existing features). If the foundation is not yet complete, the feature is queued and will execute after foundation finishes.
- **Status tracking**: Each added feature tracks its own lifecycle: `enhancing` → `enhanced` → `dev-queued` → `dev-running` → `dev-completed`.

## Capabilities

### New Capabilities
- `feature-addition-pipeline`: End-to-end pipeline for adding a feature to an existing spec, enhancing it with GPT-5.2, auto-extending the linked dev task, and triggering incremental development. Covers the voice tool, spec update logic, dev task extension, and pipeline orchestration.

### Modified Capabilities
- `spec-service`: Add `add_feature` operation that appends a GPT-5.2-enhanced feature to an existing spec's OpenSpec Config section. New tool definition `add_feature_to_spec` exposed to voice/supervisor.
- `dev-service`: Support appending feature iterations to an in-progress OpenSpec dev task and triggering incremental pipeline execution for individual features. Foundation-completion gating logic.
- `realtime-voice`: Voice instructions updated to mention "add a feature to a spec" as an available action with proper linking rules.
- `web-app`: Spec detail page gains an "Add Feature" button/form. Dev task view shows dynamically added feature iterations with individual status tracking.

## Impact

- **Backend**: `spec_agent.py` — new `add_feature_to_spec` tool + `enhance_feature()` method using GPT-5.2. `dev_agent.py` — new `append_feature_iteration()` + incremental pipeline trigger. `session.py` — updated voice instructions.
- **Frontend**: Spec detail page — add feature UI. Dev task detail — dynamic iteration list with per-feature status.
- **APIs**: New function `add_feature_to_spec(spec_id, description)` in the supervisor tool set.
- **Models**: `Spec` model — append to features list. `DevTask` model — dynamic iteration addition. No schema-breaking changes.
