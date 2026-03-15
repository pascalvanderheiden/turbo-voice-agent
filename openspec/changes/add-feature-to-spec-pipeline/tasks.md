## 1. Backend — Spec Agent: Add Feature Tool & Enhancement

- [ ] 1.1 Add `add_feature_to_spec` tool definition to `backend/app/agents/spec_agent.py` `tool_definitions` property with parameters: `spec_id` (string, required), `description` (string, required)
- [ ] 1.2 Create `enhance_feature()` method in `SpecAgent` that sends the feature description + existing spec content to GPT-5.2, producing a Mockup Description paragraph and an `openspec-propose` instruction
- [ ] 1.3 Create `add_feature_to_spec()` method that orchestrates: enhance → append to spec content → detect linked dev task → extend dev task → trigger pipeline
- [ ] 1.4 Add `add_feature_to_spec` case to `handle_function_call()` — run as background task (like `generate_spec`), return status message
- [ ] 1.5 Write GPT-5.2 system prompt for feature enhancement that includes existing spec as context and enforces two-part format consistency
- [ ] 1.6 Write tests for `enhance_feature()` — verify output format, Mockup Description word count, OpenSpec Config instruction quality
- [ ] 1.7 Write tests for `add_feature_to_spec()` — verify spec content append, dev task detection, error cases (invalid spec ID, feature-type spec)

## 2. Backend — Dev Agent: Incremental Feature Pipeline

- [ ] 2.1 Add `append_feature_iteration()` method to `DevAgent` that creates a new iteration on an existing OpenSpec dev task with the feature's `openspec-propose` instruction
- [ ] 2.2 Implement foundation-gating logic: if foundation status is `completed` → set iteration to `pending` and trigger pipeline; if `running`/`pending` → set to `queued`
- [ ] 2.3 Implement `run_incremental_feature_pipeline()` — sandbox executes `openspec-propose` + `openspec-apply` for the single feature in the existing workspace, then restarts dev server and captures screenshots
- [ ] 2.4 Add post-foundation hook: when foundation iteration completes, check for `queued` feature iterations and transition them to `pending` + trigger pipeline
- [ ] 2.5 Handle concurrent queued features: execute up to 3 in parallel after foundation completes (consistent with existing parallel feature logic)
- [ ] 2.6 Write tests for `append_feature_iteration()` — foundation complete, foundation pending, mockup mode rejection, no dev task
- [ ] 2.7 Write tests for `run_incremental_feature_pipeline()` — sandbox command sequence, screenshot capture, status updates

## 3. Backend — Integration & Voice Instructions

- [ ] 3.1 Register `add_feature_to_spec` in supervisor's function-to-agent mapping (auto-detected from spec agent's tool definitions)
- [ ] 3.2 Update English voice instructions in `backend/app/voice/session.py` to mention "you can add features to existing specs by describing the feature"
- [ ] 3.3 Update Dutch voice instructions in `backend/app/voice/session.py` with equivalent feature-addition guidance
- [ ] 3.4 Add linking rule to voice instructions: "When adding a feature to a spec, first call `get_specs()` to resolve the spec ID, then call `add_feature_to_spec` with the spec ID and feature description"
- [ ] 3.5 Write integration test: voice function call → supervisor routes to spec agent → feature enhanced → spec updated → dev task extended → pipeline triggered

## 4. Frontend — Spec Detail: Add Feature UI

- [ ] 4.1 Add "Add Feature" button to the foundation spec detail view (hidden for feature-type specs)
- [ ] 4.2 Create add-feature form component with text input for feature description and submit button
- [ ] 4.3 Wire form submission to `specApi.addFeature(specId, description)` API call
- [ ] 4.4 Add loading state ("Enhancing feature with AI...") and success/error feedback
- [ ] 4.5 Refresh spec content view after successful feature addition to show appended content
- [ ] 4.6 Add `addFeature` function to `specApi` in `frontend/src/lib/api.ts`

## 5. Frontend — Dev Task: Dynamic Iteration Display

- [ ] 5.1 Update dev task detail view to handle dynamically added iterations (poll or SSE for new iterations)
- [ ] 5.2 Add per-iteration status indicators: queued (waiting icon), pending, running (spinner), completed (check), failed (error)
- [ ] 5.3 Show "Waiting for foundation" badge on queued iterations
- [ ] 5.4 Display individual feature pipeline progress (propose → apply → screenshots) for incrementally added features

## 6. Testing & Validation

- [ ] 6.1 End-to-end test: add feature to spec with no dev task → verify spec updated, no pipeline triggered
- [ ] 6.2 End-to-end test: add feature to spec with OpenSpec dev task (foundation completed) → verify spec updated, iteration appended, pipeline triggered for feature only
- [ ] 6.3 End-to-end test: add feature to spec with OpenSpec dev task (foundation running) → verify feature queued, executes after foundation completes
- [ ] 6.4 Test error cases: invalid spec ID, feature-type spec, mockup mode dev task
- [ ] 6.5 Test voice flow: simulate voice function call for `add_feature_to_spec` through supervisor routing
