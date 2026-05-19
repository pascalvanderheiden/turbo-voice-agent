## Why

This project is ready to be shared with the developer community as an open-source reference implementation. By open-sourcing Turbo Voice Agent, we enable developers to learn from a production-grade real-time conversational AI application built on Azure, while ensuring the codebase contains no personal credentials, subscriptions, or identifiable information that could pose security risks.

## What Changes

- Rewrite README with comprehensive deployment instructions (manual azd + automated GitHub Actions)
- Add project screenshot showcasing the running application
- Remove all personal references (names, emails, Azure subscription/tenant IDs, custom domains, principal IDs)
- Add MIT license
- Decommission existing Azure deployment to enable clean redeployment from updated instructions
- Audit and genericize GitHub Actions workflow and Bicep parameters
- Add CODE_OF_CONDUCT.md and SECURITY.md following GitHub standard templates
- Audit .gitignore and git history for accidentally committed secrets
- Update package.json and pyproject.toml metadata to remove personal references

## Capabilities

### New Capabilities
- `oss-documentation`: Complete documentation for deploying and contributing to an open-source project (prerequisites, deployment steps, local development, contribution guidelines)
- `oss-governance`: Community governance documents (Code of Conduct, Security Policy, License)
- `deployment-decommission`: Instructions and commands for tearing down existing Azure environment before recreating from clean state

### Modified Capabilities
- `azure-infrastructure`: Infrastructure parameters must be fully generic with no hardcoded personal values (subscription IDs, tenant IDs, custom domains, principal IDs). All environment-specific config flows through `azd env` or gitignored parameter files.

## Impact

- **Documentation**: Complete rewrite of README.md, addition of CODE_OF_CONDUCT.md, SECURITY.md, LICENSE
- **Infrastructure**: Generic Bicep parameter handling in `infra/`, audit of `azure.yaml`, `.github/workflows/deploy.yml`
- **Code**: Audit of `backend/.env.example`, `frontend/.env.local.example` for personal references
- **Repository metadata**: Updates to `frontend/package.json`, `backend/pyproject.toml` author/repository fields
- **Assets**: New `docs/screenshot.png` (or similar path)
- **Deployment**: Requires running `azd down --force --purge` on existing environment before redeployment
- **.squad/ folder**: Local team context files (.squad/) are NOT part of the OSS distribution — they contain local agent history and should be gitignored or clarified as project-specific artifacts
