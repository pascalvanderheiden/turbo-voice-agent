# Turbo Voice Agent - Architecture Flow for Specs & Dev Tasks

## 1. SPEC HIERARCHY & UI FLOW

```
IDEA (frontend/src/lib/api.ts:Idea)
  ↓ [User clicks "Generate Specs" via Supervisor → Spec Agent]
  ↓
FOUNDATION SPEC (type="foundation")
  ├── Content: Two-part spec
  │   ├── ## Mockup Description (visual design brief)
  │   └── ## OpenSpec Config
  │       ├── ### Foundation (openspec-propose instruction)
  │       └── ### Features (multiple #### Feature: blocks)
  │
  ├── UI Location: /specs/[id] - Foundation header (lines 125-147)
  ├── Optimize Button: Lines 150-160 (calls specsApi.optimize)
  ├── Edit Button: Line 162-166 (modifies title/content)
  ├── Delete Button: Line 168-171
  ├── Dev Button: Lines 173-189 (creates dev task, links spec)
  │
  └── FEATURE SPECS (type="feature", parentId=foundationId)
      ├── Created via "Add Feature" button (lines 201-206)
      ├── Displayed in Features section (lines 192-277)
      ├── Each feature is expandable card (lines 220-273)
      ├── Can be optimized, edited, deleted individually
      │
      └── Usage for Dev:
          └── If dev task mode="openspec" with multiple iterations,
              features are either:
              a) Parsed from spec.content via regex (#### Feature: ...)
              b) Fetched as child specs via spec_svc.get_features_for_foundation()
```

## 2. DEV TASK ITERATION FLOW

```
DEV TASK (frontend/src/lib/api.ts:DevTask)
  id, title, specId, mode ("mockup" | "openspec"), status
  
  ├── SINGLE ITERATION (mode="mockup")
  │   └── iterations[0]:
  │       ├── label: "Mockup: {spec title}"
  │       ├── stages: [init, propose, apply, archive, screenshots]
  │       └── Current UI: /development/[id] shows single iteration pipeline
  │
  └── MULTIPLE ITERATIONS (mode="openspec")
      ├── iterations[0]:
      │   ├── label: "Foundation: {spec title}"
      │   ├── specPartId: spec_id
      │   └── stages: [init, propose, apply, archive, screenshots]
      │
      ├── iterations[1...N]:
      │   ├── label: "Feature: {feature name 1}"
      │   ├── specPartId: spec_id (or feature spec id)
      │   └── stages: [init, propose, apply, archive, screenshots]
      │
      ├── iterations[2]:
      │   ├── label: "Feature: {feature name 2}"
      │   └── stages: [init, propose, apply, archive, screenshots]
      │
      └── Current UI limitation:
          - Frontend shows only iterations[0] stages currently
          - Need to add tab/accordion selector for other iterations
          - currentIteration field tracks active iteration
```

## 3. SUPERVISOR ROUTING

```
User (via Voice or UI)
  ↓
Frontend API Call
  ↓
Backend HTTP → /api/...
  ↓
SupervisorAgent.handle_function_call()
  ├─ spec_functions (spec_agent):
  │  ├─ create_spec
  │  ├─ get_specs
  │  ├─ get_spec
  │  ├─ update_spec
  │  ├─ delete_spec
  │  ├─ generate_spec (from idea, creates foundation + embedded features)
  │  └─ optimize_spec
  │
  └─ dev_functions (dev_agent):
     ├─ create_dev_task (optionally linked to spec)
     ├─ get_dev_tasks
     ├─ get_dev_task
     ├─ delete_dev_task
     └─ trigger_dev_pipeline (runs mockup or openspec mode)
```

## 4. SERVICE LAYER

```
InMemorySpecService (backend/app/services/memory_spec_service.py)
  ├─ create(spec: SpecCreate) → Spec
  ├─ list() → Spec[]
  ├─ get_by_id(spec_id) → Spec | None
  ├─ update(spec_id, update: SpecUpdate) → Spec | None
  ├─ delete(spec_id) → bool
  ├─ set_optimized(spec_id, optimized_content) → Spec | None
  ├─ set_dev_task_id(spec_id, dev_task_id, status) → Spec | None
  └─ get_features_for_foundation(spec_id) → Spec[]

InMemoryDevService (backend/app/services/dev_service.py)
  ├─ create(task: DevTaskCreate) → DevTask
  ├─ list() → DevTask[]
  ├─ get_by_id(task_id) → DevTask | None
  ├─ delete(task_id) → bool
  ├─ set_iterations(task_id, iterations: list[dict]) → DevTask | None  ← POPULATES FROM SPEC
  ├─ set_status(task_id, status) → DevTask | None
  ├─ set_current_iteration(task_id, index) → None
  ├─ set_iteration_stage_status(task_id, iteration_index, stage_name, status, output?, error?) → DevTask | None
  ├─ set_stage_status(...) → DevTask | None  [Legacy, wraps set_iteration_stage_status for iter 0]
  ├─ set_skill_ids(task_id, skill_ids) → DevTask | None
  ├─ add_artifact(task_id, artifact) → DevTask | None
  └─ set_iteration_workspace(task_id, iteration_index, path) → None
```

## 5. PIPELINE EXECUTION PATH

```
DevAgent.trigger_dev_pipeline(task_id)
  ↓
DevAgent.run_pipeline(task_id, user_id)
  ├─ IF mode="mockup" and len(iterations)==1:
  │  └─ _run_mockup_pipeline(task_id, user_id)
  │     └─ Stages: init → propose → apply → archive → screenshots
  │        (All work on single iteration[0])
  │
  └─ ELSE (mode="openspec" and len(iterations)>1):
     └─ _run_openspec_pipeline(task_id, user_id)
        ├─ For each iteration:
        │  └─ Run stages: init → propose → apply → archive
        │     Each stage calls dev_svc.set_iteration_stage_status(task_id, iter_index, stage_name, ...)
        │
        └─ Final stage: _collect_screenshots(task_id)
           └─ Takes screenshots for each iteration separately
```

## 6. FRONTEND POLLING & DISPLAY

```
/development/[id] page
  ├─ Initial load:
  │  └─ devApi.get(id) → DevTask with all iterations
  │
  ├─ Live updates during pipeline:
  │  └─ EventSource to /api/dev/{id}/stream
  │     └─ Terminal view streams stdout/stderr in real-time
  │
  ├─ Current display (IterationStages component, lines 46-140):
  │  └─ Shows iteration.stages with visual pipeline
  │     ├─ SVG nodes for each stage
  │     ├─ Connector lines between stages
  │     ├─ Expandable output/error sections
  │     └─ Status icons (pending, running, completed, failed)
  │
  └─ NEED TO EXTEND:
     ├─ Tab/accordion selector for which iteration to view
     ├─ Show currentIteration indicator
     ├─ Parallel display of multiple iterations
     └─ Iteration-specific workspace/artifacts
```

## 7. DATA PERSISTENCE

```
JSON Files (backend/data/):
  ├─ specs.json
  │  └─ [{id, userId, title, content, type, parentId, ideaId, status, devTaskId, createdAt, updatedAt}, ...]
  │
  └─ dev_tasks.json
     └─ [{id, userId, title, specId, mode, status, skillIds, currentIteration, iterations:[...], stages:[...], artifacts:[...], createdAt, updatedAt}, ...]
```

## 8. KEY INTEGRATION POINTS

### Creating Feature Specs from UI:
- User clicks "Add Feature" button (spec detail page line 202)
- Opens AddFeatureDialog (lines 399-446)
- Calls specsApi.create({ title, content, type: "feature", parentId: id })
- Dialog shows in Features section immediately

### Creating Feature Specs from Generation:
- `spec_agent.generate_from_idea()` currently creates only ONE foundation spec
- Features are embedded in content as `#### Feature: ...` blocks
- TODO: Parse these blocks and create individual feature specs

### Creating Dev Task with Multiple Iterations:
- User clicks "Develop" button on foundation (line 175)
- Opens DevelopDialog, selects mode ("mockup" | "openspec")
- Calls devApi.create({ title, specId: id, mode })
- DevAgent._populate_iterations_from_spec() extracts features and creates iterations
- Either from spec.content regex or from child specs (get_features_for_foundation)

### Running Pipeline:
- User clicks trigger on dev task detail page
- devApi.trigger(task_id) → DevAgent.trigger_dev_pipeline()
- Pipeline runs sandbox commands via Sandbox service
- Updates stage status via dev_svc.set_iteration_stage_status()
- Frontend polls /dev/{id}/stream for real-time output

