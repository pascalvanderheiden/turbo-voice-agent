# Delta Spec: agent-orchestration

## MODIFIED Requirements

### Requirement: Supervisor Agent
The Supervisor Agent SHALL route incoming function calls to the correct specialist agent based on function name. It SHALL support notes, brainstorm, research, spec, dev, skills, **and marketing** agents.

#### Scenario: Route marketing functions
- **WHEN** a function call with name matching marketing operations (create_marketing_video, get_marketing_videos, get_marketing_video, delete_marketing_video, trigger_video_generation) is received
- **THEN** the supervisor routes it to the Marketing Agent and returns the result with agent name "Marketing Agent"

## ADDED Requirements

### Requirement: Marketing Agent Registration
The Marketing Agent SHALL be registered in the agent overview with model info and tool definitions.

#### Scenario: Agent overview includes Marketing Agent
- **WHEN** `GET /api/agents/status` is called
- **THEN** the response SHALL include a marketing agent entry with model "sora-2 (Azure AI Foundry, East US 2)", scriptModel "gpt-5.2", and its tool list
- **AND** an edge from supervisor to marketing SHALL be present in the topology

### Requirement: Marketing Agent Voice Tools
The Marketing Agent's tool definitions SHALL be included in the voice WebSocket session tools.

#### Scenario: Voice session includes marketing tools
- **WHEN** a voice WebSocket session is established
- **THEN** the available tools SHALL include create_marketing_video, get_marketing_videos, get_marketing_video, delete_marketing_video, and trigger_video_generation
