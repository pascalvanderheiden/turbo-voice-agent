## ADDED Requirements

### Requirement: Phase-based pipeline visualization
Replace the single flat stage row with distinct phases: Foundation (all 7 stages), Features (compact propose→apply per iteration), and Screenshots (final, gated on all features complete).

#### Scenario: Foundation phase running
- **WHEN** Iteration 0 is active and not all stages are complete
- **THEN** The Foundation row shows full init→openspec→skills→squad→propose→apply→archive pipeline with running/completed/pending indicators

#### Scenario: Foundation complete, features running
- **WHEN** All iteration 0 stages are complete and feature iterations exist
- **THEN** Foundation shows a single "✓ Foundation" completed badge, each feature iteration shows its own compact propose→apply row with status

#### Scenario: All features complete, screenshots eligible
- **WHEN** All feature iterations have status complete
- **THEN** Screenshots stage appears as active/next, visible below features section

#### Scenario: Foundation still running, features queued
- **WHEN** Foundation is not yet complete and feature iterations exist
- **THEN** Feature rows show "Queued" state, screenshots not visible yet

### Requirement: Responsive stage labels
Stage labels shorten on narrow screens and wrap to continue underneath when they don't fit.

#### Scenario: Narrow viewport
- **WHEN** The pipeline visualization renders on a screen narrower than the stage row
- **THEN** Labels use abbreviated names (Init, Spec, Skills, Squad, Prop, Apply, Arch) and wrap to a second row if needed

### Requirement: Feature iteration progress tracking
Each feature iteration's pipeline status is tracked independently. When a feature's propose→apply completes, it's marked done before the next starts.

#### Scenario: Feature completes propose and apply
- **WHEN** A feature iteration finishes both propose and apply stages
- **THEN** That feature row shows "✓ Complete" with green indicator, next feature or screenshots activates
