# OSS Governance

## ADDED Requirements

### Requirement: MIT License
The repository SHALL include an MIT License in a file named `LICENSE`.

#### Scenario: License file exists
- **WHEN** the repository is published
- **THEN** a `LICENSE` file SHALL exist at the root with the full text of the MIT License

#### Scenario: License includes copyright holder
- **WHEN** the LICENSE file is created
- **THEN** it SHALL specify the copyright year and copyright holder name

#### Scenario: Package metadata reflects license
- **WHEN** `package.json` or `pyproject.toml` is inspected
- **THEN** the license field SHALL be set to "MIT"

### Requirement: Code of Conduct
The repository SHALL include a Code of Conduct that establishes community behavior expectations.

#### Scenario: Code of Conduct file exists
- **WHEN** the repository is published
- **THEN** a `CODE_OF_CONDUCT.md` file SHALL exist at the root

#### Scenario: Uses standard template
- **WHEN** selecting a Code of Conduct
- **THEN** it SHALL use the Contributor Covenant 2.1 (GitHub's standard template)

#### Scenario: Contact information provided
- **WHEN** a community member needs to report an issue
- **THEN** the Code of Conduct SHALL include contact information for reporting violations

### Requirement: Security Policy
The repository SHALL include a Security Policy that explains how to report vulnerabilities.

#### Scenario: Security policy file exists
- **WHEN** the repository is published
- **THEN** a `SECURITY.md` file SHALL exist at the root

#### Scenario: Reporting instructions clear
- **WHEN** a security researcher discovers a vulnerability
- **THEN** `SECURITY.md` SHALL explain how to report it (e.g., via GitHub Security Advisories)

#### Scenario: Supported versions documented
- **WHEN** evaluating security support
- **THEN** `SECURITY.md` SHALL indicate which versions receive security updates

### Requirement: Repository Metadata
The repository SHALL have accurate metadata in package manifests.

#### Scenario: Frontend package.json metadata
- **WHEN** `frontend/package.json` is inspected
- **THEN** author, description, and repository URL fields SHALL be generic or removed (no personal references)

#### Scenario: Backend pyproject.toml metadata
- **WHEN** `backend/pyproject.toml` is inspected
- **THEN** author, description, and repository URL fields SHALL be generic or removed (no personal references)

#### Scenario: License field consistency
- **WHEN** any package manifest declares a license
- **THEN** it SHALL be "MIT"
