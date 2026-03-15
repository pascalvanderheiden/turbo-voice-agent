# Quick Reference: File Paths & Key Code Locations

## Frontend Files

### 1. Spec Detail Page
**File:** `frontend/src/app/(app)/specs/[id]/page.tsx`
- **Add Feature Button:** Lines 201-206
- **Features List:** Lines 192-277
- **AddFeatureDialog:** Lines 399-446
- **Develop Button:** Lines 173-189
- **DevelopDialog:** Lines 483-510+

### 2. Dev Task Detail Page
**File:** `frontend/src/app/(app)/development/[id]/page.tsx`
- **IterationStages Component:** Lines 46-140 (displays one iteration's stages)
- **Stage Metadata:** Lines 31-37
- **Terminal View:** Lines 144-150+
- **Imports:** Lines 1-29 (DevTask, DevIteration types)

### 3. API Library
**File:** `frontend/src/lib/api.ts`
- **Spec Interface:** Lines 207-218
- **specsApi Methods:** Lines 236-252
- **DevIteration Interface:** Lines 296-302
- **DevTask Interface:** Lines 304-318
- **devApi Methods:** Lines 327-337
- **specDevApi:** Lines 375-378

---

## Backend Files

### 4. Supervisor Agent
**File:** `backend/app/agents/supervisor.py`
- **Agent Registration:** Lines 18-55
- **handle_function_call():** Lines 64-145
- **spec_functions:** Lines 78-81
- **dev_functions:** Lines 82-85

### 5. Spec Agent
**File:** `backend/app/agents/spec_agent.py`
- **Tool Definitions:** Lines 102-204
- **generate_from_idea():** Lines 206-271
- **optimize():** Lines 273-287
- **handle_function_call():** Lines 289-393
- **FOUNDATION_SYSTEM_PROMPT:** Lines 14-32
- **FEATURES_SYSTEM_PROMPT:** Lines 34-54

### 6. Dev Agent
**File:** `backend/app/agents/dev_agent.py`
- **Tool Definitions:** Lines 76-146
- **_populate_iterations_from_spec():** Lines 224-258
- **run_pipeline():** Lines 262-305
- **_run_mockup_pipeline():** Lines 306-400
- **_run_openspec_pipeline():** Lines 401+ (in second half of file)
- **_extract_mockup_description():** Used by pipeline
- **_extract_openspec_config():** Used by pipeline

### 7. Dev Task Model
**File:** `backend/app/models/dev_task.py`
- **DevStage:** Lines 19-29
- **DevIteration:** Lines 32-41
- **DevTask:** Lines 66-87
- **DevTaskCreate:** Lines 44-52

### 8. Dev Service
**File:** `backend/app/services/dev_service.py`
- **set_iterations():** Lines 97-105 (POPULATE FROM SPEC)
- **set_iteration_stage_status():** Lines 148-188 (KEY UPDATE METHOD)
- **set_current_iteration():** Lines 141-146
- **create():** Lines 72-95
- **get_by_id():** Lines 111-113
- **_default_iteration():** Lines 21-28
- **_default_stages():** Lines 17-18

### 9. Tests
**File:** `backend/tests/test_spec_format.py`
- **test_extract_mockup_description():** Lines 6-24
- **test_extract_openspec_config():** Lines 27-53
- **test_extract_mockup_description_fallback():** Lines 56-62

---

## Core Data Models

### Spec (API Response)
```typescript
// frontend/src/lib/api.ts:207-218
{
  id: string;
  title: string;
  content: string;
  type: "foundation" | "feature";
  parentId: string | null;        // If type="feature", links to foundation
  ideaId: string | null;
  status: "draft" | "optimized" | "in-development" | "developed";
  devTaskId?: string | null;      // If linked to dev task
  createdAt: string;
  updatedAt: string;
}
```

### DevTask (API Response)
```typescript
// frontend/src/lib/api.ts:304-318
{
  id: string;
  title: string;
  specId?: string;
  mode: "mockup" | "openspec";
  status: "pending" | "running" | "completed" | "failed";
  skillIds?: string[];
  currentIteration: number;       // Active iteration index (0-based)
  iterations: DevIteration[];     // All iterations (foundation + features)
  stages: DevStage[];             // Legacy: mirrors iterations[0].stages
  artifacts: DevArtifact[];
  decisions?: any[];
  createdAt: string;
  updatedAt: string;
}
```

### DevIteration
```typescript
// frontend/src/lib/api.ts:296-302
{
  iterationIndex: number;
  label: string;                  // e.g., "Foundation: Dashboard" or "Feature: Auth"
  specPartId?: string;
  stages: DevStage[];             // [init, propose, apply, archive, screenshots]
  workspacePath?: string;
}
```

### DevStage
```typescript
// frontend/src/lib/api.ts:280-287
{
  name: string;                   // init, propose, apply, archive, screenshots
  status: "pending" | "running" | "completed" | "failed";
  output?: string;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}
```

---

## Critical Methods for Extension

### Frontend
1. **specsApi.create()** - Creates new spec (feature or foundation)
   - Parameters: `{ title, content, type, parentId?, ideaId? }`
   - Used in AddFeatureDialog (line 310)

2. **devApi.create()** - Creates new dev task
   - Parameters: `{ title, specId?, mode? }`
   - Used in DevelopDialog (line 331)

3. **devApi.get()** - Fetches task with all iterations
   - Used to populate IterationStages component

### Backend
1. **dev_svc.set_iterations(task_id, iterations)** - Populates task with iterations
   - Called from `DevAgent._populate_iterations_from_spec()`
   - Parses spec content or fetches child specs

2. **dev_svc.set_iteration_stage_status()** - Updates pipeline progress
   - Called during pipeline execution
   - Updates specific iteration's specific stage status

3. **spec_agent.generate_from_idea()** - Creates foundation spec from idea
   - Calls LLM to generate Mockup Description + OpenSpec Config
   - Features embedded in content, not created as separate specs

4. **DevAgent._populate_iterations_from_spec()** - Extracts iterations from spec
   - Mode="mockup": Single iteration for full spec
   - Mode="openspec": Foundation + features as separate iterations
   - Parses `#### Feature: ...` blocks from spec.content OR fetches child specs

---

## Service Methods Needed for Dev Task Status Updates

```python
# Called during pipeline execution (dev_agent.py)
await dev_svc.set_iteration_stage_status(
    task_id=task_id,
    iteration_index=0,              # Which iteration (0=foundation, 1+=features)
    stage_name="init",              # init, propose, apply, archive, screenshots
    status="running",               # pending, running, completed, failed
    output="...",                   # Optional: stage output
    error="...",                    # Optional: error message
)
```

---

## Key Integration Points for Your Task

### Adding Features to Specs:
✅ **Already Implemented:**
- Add Feature button (line 202, spec detail page)
- AddFeatureDialog (lines 399-446)
- Creates feature spec with `type="feature"`, `parentId=foundationId`
- Shows in Features list (lines 192-277)

### Extending Dev Task Iterations:
✅ **Backend Ready:**
- `set_iterations()` populates multiple iterations
- `set_iteration_stage_status()` updates any iteration's stages
- DevTask model supports `iterations[]` array

⚠️ **Frontend Needs:**
- Tab/accordion selector to view different iterations (currently shows only iteration[0])
- Display all iterations in IterationStages component
- Track and show `currentIteration` indicator
- Separate workspace/artifacts per iteration

### Creating Feature Specs from AI Generation:
⚠️ **Currently:**
- `generate_spec()` creates ONE foundation spec with embedded features
- Features are markdown blocks in content, not separate specs

💡 **TODO:**
- Parse `### Features` section from generated content
- Create individual feature specs for each `#### Feature: ...` block
- Set `parentId` to foundation spec ID
- Update spec detail page to fetch and display these

