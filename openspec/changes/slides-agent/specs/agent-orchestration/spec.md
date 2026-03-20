## MODIFIED Requirements

### Requirement: SupervisorAgent routes to SlidesAgent
The SupervisorAgent SHALL include SlidesAgent in its agent registry and route function calls matching slides tool names to the SlidesAgent's handle_function_call method.

#### Scenario: Route slides creation
- **WHEN** a function call with name "create_slides" is received
- **THEN** SupervisorAgent identifies SlidesAgent as the handler and delegates the call

#### Scenario: Route slides refinement
- **WHEN** a function call with name "refine_slides" is received
- **THEN** SupervisorAgent delegates to SlidesAgent.handle_function_call()

#### Scenario: Existing agent routing unchanged
- **WHEN** a function call for notes, ideas, research, or other existing agents is received
- **THEN** routing behavior is unchanged, existing agents handle their respective calls
