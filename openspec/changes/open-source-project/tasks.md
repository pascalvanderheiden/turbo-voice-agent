## 1. Personal Reference Audit

- [ ] 1.1 Run grep search for "pascalvanderheiden" across entire repository
- [ ] 1.2 Run grep search for "pascal.vanderheiden" (email pattern) across entire repository
- [ ] 1.3 Run grep search for GUID patterns in infra/, azure.yaml, .github/workflows/
- [ ] 1.4 Manually audit infra/**/*.bicep for hardcoded subscription IDs, tenant IDs, principal IDs
- [ ] 1.5 Manually audit azure.yaml for personal Azure resource references
- [ ] 1.6 Manually audit .github/workflows/deploy.yml for hardcoded Azure IDs
- [ ] 1.7 Manually audit backend/.env.example for personal references
- [ ] 1.8 Manually audit frontend/.env.local.example for personal references
- [ ] 1.9 Document all found references in a scrubbing checklist

## 2. Infrastructure Parameterization

- [ ] 2.1 Replace any hardcoded subscription IDs in Bicep with parameters
- [ ] 2.2 Replace any hardcoded tenant IDs in Bicep with parameters
- [ ] 2.3 Replace any hardcoded principal IDs in Bicep with parameters
- [ ] 2.4 Replace any hardcoded custom domain names in Bicep with optional parameters
- [ ] 2.5 Replace any hardcoded certificate names in Bicep with optional parameters
- [ ] 2.6 Update azure.yaml to declare all required parameters with descriptions
- [ ] 2.7 Verify all Bicep parameters have sensible defaults or are marked as required
- [ ] 2.8 Test parameter injection via azd env set commands

## 3. GitHub Actions Cleanup

- [ ] 3.1 Audit .github/workflows/deploy.yml for hardcoded Azure IDs
- [ ] 3.2 Ensure all workflow values come from vars.* or secrets.* (no hardcoded values)
- [ ] 3.3 Document required GitHub repository variables in a checklist
- [ ] 3.4 Verify OIDC federation is used (not stored secrets)

## 4. OSS Governance Documents

- [ ] 4.1 Create LICENSE file with MIT License text
- [ ] 4.2 Update LICENSE copyright year and holder
- [ ] 4.3 Create CODE_OF_CONDUCT.md using Contributor Covenant 2.1 template
- [ ] 4.4 Add contact information to CODE_OF_CONDUCT.md
- [ ] 4.5 Create SECURITY.md with vulnerability reporting instructions
- [ ] 4.6 Document supported versions in SECURITY.md
- [ ] 4.7 Add security advisory reporting via GitHub Security Advisories

## 5. Repository Metadata

- [ ] 5.1 Update frontend/package.json author field (remove personal name)
- [ ] 5.2 Update frontend/package.json description
- [ ] 5.3 Update frontend/package.json repository URL (or remove if not yet public)
- [ ] 5.4 Set frontend/package.json license field to "MIT"
- [ ] 5.5 Update backend/pyproject.toml author field (remove personal name)
- [ ] 5.6 Update backend/pyproject.toml description
- [ ] 5.7 Update backend/pyproject.toml repository URL (or remove if not yet public)
- [ ] 5.8 Set backend/pyproject.toml license field to "MIT"

## 6. README Rewrite

- [ ] 6.1 Create new README structure outline
- [ ] 6.2 Write hero section with project tagline and key features
- [ ] 6.3 Add architecture overview (distill from copilot-instructions.md)
- [ ] 6.4 Create architecture diagram (text-based or embed image)
- [ ] 6.5 Write Prerequisites section (Azure subscription, azd, Docker, Node, Python, GitHub)
- [ ] 6.6 Write Manual Deployment section with step-by-step azd up instructions
- [ ] 6.7 Document required azd env set commands with parameter descriptions
- [ ] 6.8 Write Automated Deployment section (GitHub Actions setup)
- [ ] 6.9 Document Entra ID app registration steps for OIDC
- [ ] 6.10 Document federated credentials configuration for GitHub OIDC
- [ ] 6.11 List all required GitHub repository variables with descriptions
- [ ] 6.12 Write Local Development - Backend section
- [ ] 6.13 Write Local Development - Frontend section
- [ ] 6.14 Write Local Development - Mobile section
- [ ] 6.15 Write Contributing section with PR guidelines
- [ ] 6.16 Write License section linking to LICENSE file
- [ ] 6.17 Add placeholder for screenshot (to be added later)

## 7. Screenshot Capture

- [ ] 7.1 Create docs/ directory if it doesn't exist
- [ ] 7.2 Run the application locally (web frontend)
- [ ] 7.3 Capture screenshot of main dashboard or voice interface
- [ ] 7.4 Ensure screenshot contains no personal data, cloud URLs, or identifiable info
- [ ] 7.5 Save screenshot as docs/screenshot.png
- [ ] 7.6 Update README to reference docs/screenshot.png

## 8. .gitignore and Sensitive Files Audit

- [ ] 8.1 Verify .env is in .gitignore
- [ ] 8.2 Verify .azure/ is in .gitignore
- [ ] 8.3 Verify .env.local is in .gitignore
- [ ] 8.4 Check if .squad/ should be in .gitignore (or document as optional)
- [ ] 8.5 Search git history for accidentally committed secrets (COSMOS_KEY pattern)
- [ ] 8.6 Search git history for accidentally committed API keys (32+ char patterns)
- [ ] 8.7 Search git history for accidentally committed subscription IDs (GUID pattern)
- [ ] 8.8 If critical secrets found: rotate keys and consider git-filter-repo
- [ ] 8.9 Document git history audit results

## 9. .squad/ Folder Handling

- [ ] 9.1 Determine if .squad/ is part of OSS distribution or local-only
- [ ] 9.2 If local-only: add .squad/ to .gitignore and remove from git
- [ ] 9.3 If included: add note in README that .squad/ is project-specific metadata
- [ ] 9.4 Verify no deployment instructions reference .squad/

## 10. Environment Variable Examples

- [ ] 10.1 Review backend/.env.example for personal references
- [ ] 10.2 Remove any personal Azure endpoints or IDs from .env.example
- [ ] 10.3 Replace with placeholder comments (e.g., # Set to your Cosmos DB endpoint)
- [ ] 10.4 Review frontend/.env.local.example for personal references
- [ ] 10.5 Ensure only generic localhost URLs in frontend example

## 11. Testing and Validation

- [ ] 11.1 Run grep searches again to verify all personal references removed
- [ ] 11.2 Test azd up deployment on a fresh Azure subscription
- [ ] 11.3 Verify all parameters are prompted or documented
- [ ] 11.4 Test local development setup following new README
- [ ] 11.5 Verify backend starts without errors
- [ ] 11.6 Verify frontend starts without errors
- [ ] 11.7 Verify mobile app runs in Expo

## 12. Decommission Existing Environment

- [ ] 12.1 Verify all OSS preparation tasks are complete
- [ ] 12.2 Back up any critical data (if any exists)
- [ ] 12.3 Run azd down --force --purge on existing Azure deployment
- [ ] 12.4 Verify all Azure resources are deleted in portal
- [ ] 12.5 Verify soft-deleted resources (Key Vault) are purged
- [ ] 12.6 Document decommission completion date

## 13. Fresh Redeployment Validation

- [ ] 13.1 Clone repository to a fresh directory (or use a new machine)
- [ ] 13.2 Follow README manual deployment instructions exactly
- [ ] 13.3 Set all required azd env parameters
- [ ] 13.4 Run azd up and verify successful deployment
- [ ] 13.5 Verify application is accessible at generated Azure URL
- [ ] 13.6 Test basic functionality (web app loads, voice interface available)
- [ ] 13.7 Document any issues or missing instructions

## 14. Final Review

- [ ] 14.1 Review all governance documents (LICENSE, CODE_OF_CONDUCT.md, SECURITY.md)
- [ ] 14.2 Review README for completeness and clarity
- [ ] 14.3 Verify screenshot is present and appropriate
- [ ] 14.4 Verify no TODO or placeholder comments remain in production files
- [ ] 14.5 Run linters on all code (ruff for Python, ESLint for TypeScript)
- [ ] 14.6 Run tests to ensure no regressions
- [ ] 14.7 Create final commit with all OSS preparation changes
- [ ] 14.8 Tag commit as v1.0.0-oss-ready (or similar)

## 15. Repository Publication

- [ ] 15.1 Push all changes to main branch
- [ ] 15.2 Change repository visibility to Public on GitHub
- [ ] 15.3 Add repository description on GitHub
- [ ] 15.4 Add repository topics/tags (azure, ai, voice, openai, etc.)
- [ ] 15.5 Pin README sections or add a Quick Start guide
- [ ] 15.6 Enable GitHub Issues and Discussions
- [ ] 15.7 Announce open-source release (blog post, social media, etc.)
