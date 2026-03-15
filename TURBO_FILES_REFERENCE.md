# Turbo Voice Agent - File Inventory for Feature Addition

## 1. Frontend Spec Detail Component
**Full Path:** `/Users/pascalvanderheiden/Documents/GitHub/turbo-voice-agent/frontend/src/app/(app)/specs/[id]/page.tsx`

**Key Sections:**

### Current Structure (lines 1-50):
- State management for foundation spec, features list, edit/delete modals
- Loads spec by ID and features filtered by `parentId`
- Already has "Add Feature" button and dialog (line 202-206)

```typescript
const [foundation, setFoundation] = useState<Spec | null>(null);
const [features, setFeatures] = useState<Spec[]>([]);
const [addFeature, setAddFeature] = useState(false);
const [devTask, setDevTask] = useState<{ id: string; title: string; mode: string; status: string } | null>(null);
const [showDevDialog, setShowDevDialog] = useState(false);
```

### Add Feature Button (lines 201-206):
```typescript
<button
  onClick={() => setAddFeature(true)}
  className="flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-brand-cyan)] text-white text-xs font-medium hover:opacity-90 transition-opacity"
>
  <IconPlus size={14} /> Add Feature
</button>
```

### Foundation Actions (lines 150-190):
- Optimize button for drafts
- Edit button
- Delete button  
- Develop button (creates dev task)

### Add Feature Dialog (lines 399-446):
```typescript
function AddFeatureDialog({
  onClose,
  onSubmit,
}: {
  onClose: () => void;
  onSubmit: (title: string, content: string) => Promise<void>;
})
```

**Dialog creates feature with:**
- `type: "feature"`
- `parentId: id` (links to foundation)
- `ideaId` inherited from foundation if present


---

## 2. Frontend Dev Task Detail Component
**Full Path:** `/Users/pascalvanderheiden/Documents/GitHub/turbo-voice-agent/frontend/src/app/(app)/development/[id]/page.tsx`

**Key Sections:**

### Iteration Display Structure (lines 46-140):
Renders `DevIteration[]` with nested stages visualization:

```typescript
interface DevIteration {
  iterationIndex: number;
  label: string;           // e.g., "Foundation: Dashboard" or "Feature: User Auth"
  specPartId?: string;
  stages: DevStage[];
  workspacePath?: string;
}

interface DevStage {
  name: string;           // init, propose, apply, archive, screenshots
  status: string;         // pending, running, completed, failed
  output?: string;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}
```

### Iteration Stages Component (lines 46-140):
- `IterationStages({ stages })` component renders vertical pipeline visualization
- Shows stage status icons with colors
- Expandable output/error details per stage
- Connector lines between stages

### Stage Metadata (lines 31-37):
```typescript
const STAGE_META: Record<string, { Icon: typeof IconSettingsAutomation; label: string; color: string }> = {
  init:        { Icon: IconSettingsAutomation, label: "Init",        color: "var(--color-brand-purple)" },
  propose:     { Icon: IconMessageChatbot,     label: "Propose",     color: "var(--color-brand-cyan)" },
  apply:       { Icon: IconPackage,            label: "Apply",       color: "var(--color-brand-pink)" },
  archive:     { Icon: IconArchive,            label: "Archive",     color: "#F59E0B" },
  screenshots: { Icon: IconPhoto,              label: "Screenshots", color: "#22C55E" },
};
```

### Terminal View (lines 144-150+):
Streaming event source for live pipeline output via `/api/dev/{id}/stream`

**For extended iterations:** Need to display all iterations with tabs or accordion, showing current iteration stages prominently.


---

## 3. Frontend API Library
**Full Path:** `/Users/pascalvanderheiden/Documents/GitHub/turbo-voice-agent/frontend/src/lib/api.ts`

### Spec API (lines 206-252):
```typescript
export interface Spec {
  id: string;
  title: string;
  content: string;
  type: "foundation" | "feature";
  parentId: string | null;
  ideaId: string | null;
  status: "draft" | "optimized" | "in-development" | "developed";
  devTaskId?: string | null;
  createdAt: string;
  updatedAt: string;
}

export const specsApi = {
  list: () => fetchApi<Spec[]>("/api/specs"),
  get: (id: string) => fetchApi<Spec>(`/api/specs/${id}`),
  create: (data: SpecCreate) =>
    fetchApi<Spec>("/api/specs", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: SpecUpdate) =>
    fetchApi<Spec>(`/api/specs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    fetchApi<void>(`/api/specs/${id}`, { method: "DELETE" }),
  optimize: (id: string) =>
    fetchApi<Spec>(`/api/specs/${id}/optimize`, { method: "POST" }),
  generate: (ideaId: string) =>
    fetchApi<{ success: boolean; specs: Array<{ id: string; title: string; type: string }> }>(
      "/api/specs/generate",
      { method: "POST", body: JSON.stringify({ idea_id: ideaId }) }
    ),
};
```

### Dev Task API (lines 278-337):
```typescript
export interface DevIteration {
  iterationIndex: number;
  label: string;
  specPartId?: string;
  stages: DevStage[];
  workspacePath?: string;
}

export interface DevTask {
  id: string;
  title: string;
  specId?: string;
  mode: string; // mock | sequence
  status: string;
  skillIds?: string[];
  currentIteration: number;
  iterations: DevIteration[];
  stages: DevStage[]; // legacy flat view (iteration 0)
  artifacts: DevArtifact[];
  decisions?: { question: string; answer: string; stage: string; timestamp: string }[];
  createdAt: string;
  updatedAt: string;
}

export const devApi = {
  list: (): Promise<DevTask[]> => fetchApi("/api/dev"),
  get: (id: string): Promise<DevTask> => fetchApi(`/api/dev/${id}`),
  create: (data: DevTaskCreate): Promise<DevTask> =>
    fetchApi("/api/dev", { method: "POST", body: JSON.stringify(data) }),
  delete: (id: string): Promise<void> =>
    fetchApi(`/api/dev/${id}`, { method: "DELETE" }),
  trigger: (id: string, mode?: string): Promise<DevTask> =>
    fetchApi(`/api/dev/${id}/trigger`, { method: "POST", body: JSON.stringify(mode ? { mode } : {}), headers: { "Content-Type": "application/json" } }),
  downloadUrl: (id: string): string => `${API_BASE}/api/dev/${id}/download`,
};
```

### Spec-Dev Link API (lines 373-378):
```typescript
export const specDevApi = {
  getDevTask: (specId: string): Promise<{ devTask: { id: string; title: string; mode: string; status: string } | null }> =>
    fetchApi(`/api/specs/${specId}/dev-task`),
};
```

**TO EXTEND:** May need to add methods for:
- Creating multiple features from UI
- Batch operations on feature specs


---

## 4. Backend Supervisor Agent
**Full Path:** `/Users/pascalvanderheiden/Documents/GitHub/turbo-voice-agent/backend/app/agents/supervisor.py`

### Agent Registration (lines 18-55):
```python
class SupervisorAgent:
    def __init__(
        self,
        notes_agent: NotesAgent,
        brainstorm_agent: BrainstormAgent | None = None,
        research_agent: ResearchAgent | None = None,
        spec_agent: SpecAgent | None = None,
        dev_agent: DevAgent | None = None,
        skills_agent: SkillsAgent | None = None,
        marketing_agent: MarketingAgent | None = None,
        todo_agent: TodoAgent | None = None,
    ):
        self._agents: dict[str, object] = {"notes": notes_agent}
        if brainstorm_agent:
            self._agents["brainstorm"] = brainstorm_agent
        if research_agent:
            self._agents["research"] = research_agent
        if spec_agent:
            self._agents["spec"] = spec_agent
        # ... etc
```

### Function Routing (lines 64-145):
Maps function names to agents and dispatches via `handle_function_call`:

```python
async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> tuple[str, str]:
    """Route a function call to the appropriate agent.
    
    Returns (result_json, agent_name).
    """
    spec_functions = {
        "create_spec", "get_specs", "get_spec", "update_spec", "delete_spec",
        "generate_spec", "optimize_spec",
    }
    dev_functions = {
        "create_dev_task", "get_dev_tasks", "get_dev_task", "delete_dev_task",
        "trigger_dev_pipeline",
    }
    
    if function_name in spec_functions and self._spec_agent:
        logger.info("Routing '%s' to Spec Agent", function_name)
        result = await self._spec_agent.handle_function_call(function_name, arguments, user_id=user_id)
        return result, "Spec Agent"
    
    if function_name in dev_functions and self._dev_agent:
        logger.info("Routing '%s' to Turbo Dev Agent", function_name)
        result = await self._dev_agent.handle_function_call(function_name, arguments, user_id=user_id)
        return result, "Turbo Dev Agent"
```

**To extend:** Add new function names to `spec_functions` or `dev_functions` sets if needed for feature management.


---

## 5. Backend Spec Agent (Tool Definitions)
**Full Path:** `/Users/pascalvanderheiden/Documents/GitHub/turbo-voice-agent/backend/app/agents/spec_agent.py`

### Tool Definitions (lines 102-204):
Defines OpenAI-compatible function tools:

```python
@property
def tool_definitions(self) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "create_spec",
                "description": "Create a new development spec manually",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "The spec title"},
                        "content": {"type": "string", "description": "The spec content in markdown"},
                        "type": {"type": "string", "enum": ["foundation", "feature"], "description": "Spec type"},
                        "parent_id": {"type": "string", "description": "Parent foundation spec ID (for feature specs)"},
                        "idea_id": {"type": "string", "description": "Source idea ID if linked"},
                    },
                    "required": ["title", "content"],
                },
            },
        },
        # ... get_specs, get_spec, update_spec, delete_spec
        {
            "type": "function",
            "function": {
                "name": "generate_spec",
                "description": "Generate a foundation spec and minimal feature specs from an idea using AI...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "idea_id": {"type": "string", "description": "The idea ID to generate specs from"},
                        "title": {"type": "string", "description": "Idea title (if not using idea_id)"},
                        "description": {"type": "string", "description": "Idea description (if not using idea_id)"},
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "optimize_spec",
                "description": "Optimize a spec using AI to make it more concise and clear...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "spec_id": {"type": "string", "description": "The spec ID to optimize"},
                    },
                    "required": ["spec_id"],
                },
            },
        },
    ]
```

### Spec Generation Flow (lines 206-271):
1. Generate foundation spec (Mockup Description + OpenSpec Config > Foundation)
2. Generate features section (OpenSpec Config > Features)
3. Combine into single two-part spec
4. Create in database with `type="foundation"`

```python
async def generate_from_idea(self, title: str, description: str, idea_id: str | None = None, user_id: str | None = None) -> list[dict]:
    """Generate foundation + feature specs from an idea. Returns list of created spec dicts."""
    # ... LLM calls to generate foundation and features
    combined_content = foundation_content.rstrip() + "\n\n" + features_content.strip()
    
    spec = await service.create(
        SpecCreate(
            title=title,
            content=combined_content,
            type="foundation",
            ideaId=idea_id,
        )
    )
```

**NOTE:** Currently only `generate_spec` returns foundation specs. Features are embedded in the content but not created as separate specs. You may want to add parsing to extract and create feature specs individually.


---

## 6. Backend Dev Agent (Core Structure)
**Full Path:** `/Users/pascalvanderhield/Documents/GitHub/turbo-voice-agent/backend/app/agents/dev_agent.py`

### Tool Definitions (lines 76-146):
```python
@property
def tool_definitions(self) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "create_dev_task",
                "description": "Create a new development task, optionally linked to a spec",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "The task title"},
                        "spec_id": {"type": "string", "description": "Optional spec ID to develop"},
                        "mode": {"type": "string", "enum": ["mockup", "openspec"], "description": "Pipeline mode..."},
                    },
                    "required": ["title"],
                },
            },
        },
        # ... get_dev_tasks, get_dev_task, delete_dev_task, trigger_dev_pipeline
    ]
```

### Iteration Population from Spec (lines 224-258):
```python
async def _populate_iterations_from_spec(self, task_id: str, spec_id: str, mode: str, user_id: str | None = None) -> None:
    """Populate iterations from spec hierarchy."""
    spec_svc = self._spec_service.with_user(user_id) if user_id else self._spec_service
    spec = await spec_svc.get_by_id(spec_id)
    if not spec:
        return

    if mode == "mockup":
        # Single iteration for the full mockup
        full_label = f"Mockup: {spec.title}"
        iterations = [_default_iteration(0, full_label, spec_id)]
    else:
        # OpenSpec: foundation first, then each feature from spec content
        iterations = [_default_iteration(0, f"Foundation: {spec.title}", spec_id)]
        # Parse feature prompts from spec content if available
        spec_content = spec.content or ""
        for i, match in enumerate(
            re.finditer(
                r'#### Feature: (.+?)\n(.*?)(?=\n#### Feature:|\n### |\n## |\Z)',
                spec_content,
                re.DOTALL,
            )
        ):
            feature_title = match.group(1).strip()
            iterations.append(_default_iteration(i + 1, f"Feature: {feature_title}", spec_id))
        # Fallback: if no features parsed from content, use sub-specs
        if len(iterations) == 1:
            features = await spec_svc.get_features_for_foundation(spec_id)
            for i, f in enumerate(features):
                iterations.append(_default_iteration(i + 1, f"Feature: {f.title}", f.id))

    dev_svc = self._service.with_user(user_id) if user_id else self._service
    await dev_svc.set_iterations(task_id, iterations)
```

### Pipeline Execution (lines 262-400):
- Delegates to `_run_mockup_pipeline` (single iteration) or `_run_openspec_pipeline` (multiple)
- Each stage transitions: init → propose → apply → archive → screenshots
- Updates stage status via `set_iteration_stage_status`


---

## 7. Backend Dev Task Model
**Full Path:** `/Users/pascalvanderheiden/Documents/GitHub/turbo-voice-agent/backend/app/models/dev_task.py`

### Core Models (lines 1-88):

```python
class DevStage(BaseModel):
    """A single pipeline stage."""
    name: str  # plan | build | run | test
    status: str = "pending"  # pending | running | completed | failed
    output: str | None = None
    error: str | None = None
    started_at: str | None = Field(None, alias="startedAt")
    completed_at: str | None = Field(None, alias="completedAt")

class DevIteration(BaseModel):
    """A single development iteration (foundation or feature)."""
    iteration_index: int = Field(alias="iterationIndex")
    label: str  # e.g. "Foundation: Dark Cyberpunk" or "Feature: Combat System"
    spec_part_id: str | None = Field(None, alias="specPartId")
    stages: list[DevStage] = Field(default_factory=list)
    workspace_path: str | None = Field(None, alias="workspacePath")

class DevTask(BaseModel):
    """API response model for a development task."""
    id: str
    title: str
    spec_id: str | None = Field(None, alias="specId")
    mode: str = "mockup"  # mockup | openspec
    status: str = "pending"  # pending | running | completed | failed
    skill_ids: list[str] = Field(default_factory=list, alias="skillIds")
    current_iteration: int = Field(0, alias="currentIteration")
    iterations: list[DevIteration] = Field(default_factory=list)
    stages: list[DevStage] = Field(default_factory=list)  # Legacy flat stages for backward compat
    artifacts: list[DevArtifact] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
```

**Key fields for iteration support:**
- `current_iteration: int` - tracks which iteration (0-indexed) is currently active
- `iterations: list[DevIteration]` - all iterations with their stages
- `stages: list[DevStage]` - legacy field (mirrored from iterations[0] for backward compatibility)


---

## 8. Backend Dev Service
**Full Path:** `/Users/pascalvanderheiden/Documents/GitHub/turbo-voice-agent/backend/app/services/dev_service.py`

### Set Iterations (lines 97-105):
```python
async def set_iterations(self, task_id: str, iterations: list[dict]) -> DevTask | None:
    """Replace iterations on a task (used when populating from specs)."""
    doc = self._store.get(task_id)
    if not doc:
        return None
    doc["iterations"] = iterations
    doc["updatedAt"] = datetime.now(UTC).isoformat()
    self._save_to_disk()
    return self._doc_to_model(doc)
```

### Set Iteration Stage Status (lines 148-188):
```python
async def set_iteration_stage_status(
    self, task_id: str, iteration_index: int, stage_name: str,
    status: str, output: str | None = None, error: str | None = None,
) -> DevTask | None:
    """Update a stage within a specific iteration."""
    doc = self._store.get(task_id)
    if not doc:
        return None
    iterations = doc.get("iterations", [])
    for it in iterations:
        if it["iterationIndex"] == iteration_index:
            for stage in it.get("stages", []):
                if stage["name"] == stage_name:
                    stage["status"] = status
                    if status == "running":
                        stage["startedAt"] = datetime.now(UTC).isoformat()
                    if status in ("completed", "failed"):
                        stage["completedAt"] = datetime.now(UTC).isoformat()
                    if output is not None:
                        stage["output"] = output
                    if error is not None:
                        stage["error"] = error
                    break
            break
    # Also update legacy top-level stages for iteration 0
    if iteration_index == 0:
        for stage in doc.get("stages", []):
            if stage["name"] == stage_name:
                stage["status"] = status
                # ... same updates
    doc["updatedAt"] = datetime.now(UTC).isoformat()
    self._save_to_disk()
    return self._doc_to_model(doc)
```

### Set Current Iteration (lines 141-146):
```python
async def set_current_iteration(self, task_id: str, index: int) -> None:
    doc = self._store.get(task_id)
    if doc:
        doc["currentIteration"] = index
        doc["updatedAt"] = datetime.now(UTC).isoformat()
        self._save_to_disk()
```

### Other Key Methods:
- `create(data: DevTaskCreate)` - creates task with single default iteration
- `list()` - returns all user's dev tasks
- `get_by_id(task_id)` - fetches task with all iterations
- `delete(task_id)` - removes task
- `set_status(task_id, status)` - updates task status
- `add_artifact(task_id, artifact)` - appends artifact to artifacts list


---

## 9. Spec Format Tests
**Full Path:** `/Users/pascalvanderheiden/Documents/GitHub/turbo-voice-agent/backend/tests/test_spec_format.py`

### Test Coverage (lines 1-63):
Tests for the two-part spec format parsing:

```python
def test_extract_mockup_description():
    """Can extract Mockup Description from spec content."""
    # Spec with ## Mockup Description and ## OpenSpec Config sections
    # Verifies extraction of visual design brief

def test_extract_openspec_config():
    """Can extract foundation and feature prompts from OpenSpec Config."""
    # Spec with ### Foundation and #### Feature sections
    # Returns tuple of (foundation_text, features_list)

def test_extract_mockup_description_fallback():
    """Falls back to full content when no Mockup Description section."""
    # Plain spec content without section headers
```

**Used by:** `DevAgent._extract_mockup_description()` and `DevAgent._extract_openspec_config()`

---

## Summary of Extension Points

### For Adding "Add Feature" Button to Spec Detail Page:
**Already implemented!** The button and dialog exist at lines 201-206 and 399-446.

### For Extending Dev Task Iterations:
1. **Frontend:** Dev detail page already supports displaying all iterations with `DevIteration[]` model
2. **Backend:** `set_iteration_stage_status()` already supports updating any iteration's stages
3. **Service:** `set_iterations()` replaces full iteration list when spec is linked

### To Automatically Create Feature Specs:
Currently, features are embedded in foundation spec content and parsed by regex in `dev_agent._populate_iterations_from_spec()`. Could extend `spec_agent.generate_from_idea()` to:
1. Parse `### Features` section from generated content
2. Create individual feature specs for each `#### Feature: ...` block
3. Use `type="feature"` with `parentId` pointing to foundation

