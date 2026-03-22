## MODIFIED Requirements

### Requirement: Supervisor routes work agent function calls
The supervisor SHALL route the `ask_work_question` function call to the Work Agent's `handle_function_call` method, making it accessible from both voice and chat gateways.

#### Scenario: Voice user asks work question
- **WHEN** a voice session triggers a function call with name `ask_work_question`
- **THEN** the supervisor SHALL route it to `work_agent.handle_function_call()` with the user's context

#### Scenario: Chat user asks work question
- **WHEN** a chat session triggers a function call with name `ask_work_question`
- **THEN** the supervisor SHALL route it to `work_agent.handle_function_call()` with the user's context

### Requirement: Supervisor constructor accepts work agent
The supervisor constructor SHALL accept an optional `work_agent` parameter and include `ask_work_question` in its routing table when provided.
