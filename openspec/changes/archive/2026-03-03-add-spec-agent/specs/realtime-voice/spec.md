## MODIFIED Requirements

### Requirement: Voice Live Function Calling Bridge
The voice session SHALL expose all supervisor tools including spec operations. The system instructions SHALL mention spec creation, viewing, and idea-to-spec conversion as available capabilities.

#### Scenario: Spec via voice
- **WHEN** a user says "create a spec from my last idea"
- **THEN** the voice agent triggers the generate_spec function through the supervisor

#### Scenario: List specs via voice
- **WHEN** a user asks "what specs do I have?"
- **THEN** the voice agent triggers get_specs and reads back the list

### Requirement: Voice Session Configuration
The voice greeting and system instructions SHALL mention all available capabilities including notes, ideas, research, and specs.

#### Scenario: Updated greeting
- **WHEN** a voice session starts
- **THEN** the greeting mentions the ability to manage notes, ideas, research, and development specs
