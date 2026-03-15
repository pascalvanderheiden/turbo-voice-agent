## MODIFIED Requirements

### Requirement: Spec generation output format
The system SHALL generate specs in a two-part format: (1) **Mockup Description** — a concise description of the frontend design demonstrating key features (~200 words, covering layout, components, interactions, and visual style), and (2) **OpenSpec Config** — a series of focused prompt instructions, starting with one `openspec-propose` instruction for the foundation and one `openspec-propose` instruction per feature.

#### Scenario: Generate spec from idea
- **WHEN** a user requests spec generation from an idea (via voice or UI)
- **THEN** the system SHALL produce a spec with exactly two sections: a `## Mockup Description` section containing a concise frontend design brief, and a `## OpenSpec Config` section containing structured `openspec-propose` prompt instructions

#### Scenario: Mockup Description content
- **WHEN** a spec is generated
- **THEN** the Mockup Description SHALL include: app name, layout structure, key UI components, primary user interactions, color scheme/visual identity, and a list of demonstrated features — all in ~200 words maximum

#### Scenario: OpenSpec Config content
- **WHEN** a spec is generated
- **THEN** the OpenSpec Config SHALL contain a `### Foundation` subsection with a single `openspec-propose` prompt instruction covering the app's core architecture, and a `### Features` subsection with one `openspec-propose` prompt instruction per feature, each focused and self-contained

#### Scenario: OpenSpec Config prompt quality
- **WHEN** the OpenSpec Config is consumed by the Copilot CLI
- **THEN** each `openspec-propose` instruction SHALL be a clear, focused prompt that can be directly used as input to the `openspec-propose` CLI command without further editing

### Requirement: Spec optimization
The system SHALL optimize specs while preserving the two-part format structure.

#### Scenario: Optimize preserves format
- **WHEN** a user requests spec optimization
- **THEN** the optimized spec SHALL retain both the Mockup Description and OpenSpec Config sections, refining content for clarity and conciseness within each section
