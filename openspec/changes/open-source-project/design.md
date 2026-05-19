## Context

This project (Turbo Voice Agent) was developed as a personal implementation and currently contains personal identifiers, Azure subscription/tenant IDs, custom domain configurations, and environment-specific parameters. Before open-sourcing, we must ensure:

1. **No security risks**: No secrets, API keys, subscription IDs, tenant IDs, or personal credentials in the repository or git history
2. **Reproducibility**: Anyone with an Azure subscription can deploy the solution following clear instructions
3. **Community readiness**: Standard OSS governance documents (License, Code of Conduct, Security Policy)
4. **Clean slate**: Existing Azure deployment decommissioned to validate that redeployment from updated docs works

**Current state:**
- Infrastructure defined in Bicep with some parameters referencing personal Azure resources
- GitHub Actions workflow uses repo variables (some potentially personal)
- README is developer-focused (copilot-instructions.md) but lacks deployment instructions for new users
- No LICENSE, CODE_OF_CONDUCT.md, or SECURITY.md
- `.squad/` folder contains local team context (not part of OSS distribution)

**Stakeholders:** Pascal van der Heiden (project owner), future open-source contributors

## Goals / Non-Goals

**Goals:**
- Remove all personal references and identifiers from code, configuration, and documentation
- Provide complete deployment instructions for both manual (`azd up`) and automated (GitHub Actions) workflows
- Add standard OSS governance documents (MIT license, Code of Conduct, Security Policy)
- Validate clean deployment by decommissioning existing environment
- Add visual documentation (screenshot) showing the application
- Ensure infrastructure parameters are fully generic and environment-agnostic

**Non-Goals:**
- Rewriting application features or functionality
- Changing the tech stack or architecture
- Migrating existing data or state
- Creating a hosted/SaaS version
- Providing Windows-specific deployment paths (Mac/Linux primary)
- Open-sourcing `.squad/` team context (local-only artifacts)

## Decisions

### D1: MIT License
**Decision:** Use MIT License for open-source distribution.

**Rationale:** MIT is permissive, widely recognized, and aligns with community expectations for reference implementations. Allows commercial and private use without copyleft restrictions.

**Alternatives considered:**
- Apache 2.0: More verbose, includes patent grant (unnecessary for this project)
- GPL: Copyleft would restrict commercial use cases
- Unlicense: Too permissive, lacks attribution requirements

### D2: Screenshot Placement
**Decision:** Place screenshot at `docs/screenshot.png` and reference in README.

**Rationale:** 
- `docs/` folder is standard for documentation assets
- PNG format balances quality and file size
- Single hero screenshot shows main UI (web app voice interface)
- Screenshot must be captured from a running local instance (no personal cloud URLs visible)

**Alternatives considered:**
- Root-level `screenshot.png`: Clutters root directory
- Multiple screenshots: Overkill for README; detailed docs can come later
- GIF/video: Larger file size, not necessary for static UI

### D3: Personal Reference Scrubbing Strategy
**Decision:** Use automated search (grep) across entire repo for common personal identifiers, then manual review of high-risk files.

**Search terms:**
- `pascalvanderheiden` (GitHub username, likely in URLs)
- `pascal.vanderheiden` (email pattern)
- Subscription IDs (GUID pattern in `infra/`, `azure.yaml`, workflows)
- Tenant IDs (GUID pattern in Entra ID configs)
- Custom domain names (e.g., specific `.azurewebsites.net` or custom domains in Bicep)
- Principal IDs (in Bicep parameters)

**High-risk files to manually audit:**
- `infra/**/*.bicep`
- `infra/**/*.bicepparam`
- `azure.yaml`
- `.github/workflows/deploy.yml`
- `backend/.env.example`
- `frontend/.env.local.example`
- `README.md`
- `package.json`, `pyproject.toml` (author fields)

**Rationale:** Automated search catches most instances; manual review ensures context-aware scrubbing (e.g., knowing which GUIDs are subscription IDs vs. random UUIDs in test data).

**Alternatives considered:**
- Rewrite git history (git-filter-repo): Risky, breaks existing clones, unnecessary if no secrets committed
- Fresh repo: Loses git history, which is valuable for understanding evolution

### D4: Decommission Existing Environment
**Decision:** Run `azd down --force --purge` to tear down Pascal's current Azure deployment before finalizing OSS release.

**Rationale:**
- Validates that redeployment from updated instructions works end-to-end
- Ensures no dangling resources with personal identifiers remain in Azure
- Provides a clean baseline for cost estimation (new deployments start fresh)
- `--purge` removes soft-deleted resources (e.g., Key Vault, ensuring no name conflicts)

**Risks:** 
- **Data loss** → Mitigated by ensuring no production data exists (this is a reference implementation)
- **Cost of redeployment** → Mitigated by decommissioning shortly before OSS release, minimizing downtime

**Alternatives considered:**
- Keep existing deployment: Leaves personal identifiers in Azure resource names, contradicts OSS goals
- Manual resource deletion: Prone to missed resources; `azd down` is comprehensive

### D5: GitHub Actions Workflow Handling
**Decision:** Keep existing `.github/workflows/deploy.yml` with all personal values extracted to repo variables. Document variable setup in README.

**Rationale:**
- Automated deployment via GitHub Actions is a key feature (OIDC federation, no secrets)
- Workflow structure is reusable; only the *values* are personal
- New users set up their own repo variables after forking

**Implementation:**
- Audit workflow for hardcoded values → ensure all come from `vars.*` or `secrets.*`
- Document required repo variables in README (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, AZURE_ENV_NAME, AZURE_LOCATION, ENTRA_TENANT_ID, ENTRA_CLIENT_ID, CUSTOM_DOMAIN_NAME, EXISTING_CERT_NAME, DEPLOYER_PRINCIPAL_ID)
- Add note that these are *user-specific* and must be configured per fork

**Alternatives considered:**
- Remove workflow: Loses automated deployment story, which is valuable for demo/reference
- Template workflow with placeholders: More confusing than clear documentation

### D6: Bicep Parameter Strategy
**Decision:** Use `azure.yaml` and `azd env` for all environment-specific parameters. No hardcoded GUIDs in Bicep files.

**Rationale:**
- `azd` convention: `azure.yaml` defines parameters, `azd env set` stores user-specific values locally (gitignored `.azure/` folder)
- Bicep receives parameters via `main.bicepparam` or command-line args
- Example parameters that must be user-provided:
  - `ENTRA_TENANT_ID`
  - `ENTRA_CLIENT_ID`
  - `CUSTOM_DOMAIN_NAME` (optional)
  - `EXISTING_CERT_NAME` (optional)
  - `DEPLOYER_PRINCIPAL_ID` (for RBAC assignments)

**Implementation:**
- Audit all Bicep files for hardcoded GUIDs or personal values
- Ensure `azure.yaml` declares all required parameters with descriptions
- Update README to explain `azd env set` commands for user-specific config

**Alternatives considered:**
- `.bicepparam` files: Less discoverable than `azure.yaml`, not standard `azd` pattern
- Prompt user during `azd up`: Not supported for all parameter types (e.g., principal IDs)

### D7: .squad/ Folder Handling
**Decision:** Leave `.squad/` folder in repository but add `.gitignore` entry to exclude it from forks, OR document that it's project-specific local context.

**Rationale:**
- `.squad/` contains local team agent history and decisions
- Not part of the OSS distribution — it's metadata about *this specific project instance*
- Other users won't have a `.squad/` folder unless they set up their own squad

**Implementation:**
- Verify `.squad/` is not referenced in deployment instructions
- If `.squad/` is committed to git: add note in README that it's optional local tooling
- If `.squad/` should be private: add to `.gitignore` and remove from git

**Alternatives considered:**
- Delete `.squad/`: Loses project context for maintainers
- Make `.squad/` part of OSS: Confusing for new users, exposes internal workflow

### D8: Code of Conduct & Security Policy
**Decision:** Use GitHub's standard templates for `CODE_OF_CONDUCT.md` and `SECURITY.md`.

**Rationale:**
- Standard templates are widely recognized and require minimal customization
- `CODE_OF_CONDUCT.md`: Use Contributor Covenant 2.1 (GitHub default)
- `SECURITY.md`: Adapt GitHub's template with instructions to report vulnerabilities via GitHub Security Advisories

**Alternatives considered:**
- Custom Code of Conduct: Unnecessary, standard templates are well-tested
- No Security Policy: Leaves contributors unclear on how to report vulnerabilities

### D9: README Structure
**Decision:** Complete rewrite of README with the following structure:

1. **Hero section**: Logo, tagline, key features, screenshot
2. **Architecture overview**: Distilled from copilot-instructions.md (diagram + bullet points)
3. **Prerequisites**: Azure subscription, azd CLI, Docker, Node, Python, GitHub account, Entra ID app registration
4. **Manual deployment** (`azd up`): Step-by-step commands
5. **Automated deployment** (GitHub Actions): Fork setup, OIDC configuration, repo variables
6. **Local development**: Backend, frontend, mobile setup (distilled from copilot-instructions.md)
7. **Contributing**: Link to CODE_OF_CONDUCT.md, PR guidelines
8. **License**: Link to LICENSE

**Rationale:**
- Deployment instructions are primary need for new users
- Architecture overview provides context without overwhelming detail
- Local development section enables contributors
- Separate sections for manual vs. automated deployment cater to different user workflows

**Alternatives considered:**
- Keep current README: Too terse, lacks deployment instructions
- Split into multiple docs (DEPLOY.md, CONTRIBUTING.md): Over-engineering for initial OSS release

### D10: Git History Audit
**Decision:** Search git history for accidentally committed secrets using `git log --all --full-history --source --pickaxe-all -S<pattern>` for common secret patterns.

**Patterns to search:**
- `COSMOS_KEY`, `AZURE_OPENAI_KEY`, `VOICE_LIVE_KEY`
- API keys (regex: `[A-Za-z0-9]{32,}`)
- Subscription IDs (GUID pattern)

**Rationale:**
- Git history is public once open-sourced
- Accidentally committed secrets must be rotated *before* OSS release
- Search is non-destructive (no history rewrite unless critical secrets found)

**If secrets found:**
- **Minor (non-functional test data)**: Document in issue, no action needed
- **Critical (live API keys)**: Rotate keys, consider `git-filter-repo` to rewrite history

**Alternatives considered:**
- Ignore git history: Risky, could expose live credentials
- Always rewrite history: Overkill if no secrets exist

## Risks / Trade-offs

### R1: Incomplete personal reference scrubbing
**Risk:** Missing a personal identifier (email, GUID) in an obscure config file.

**Mitigation:**
- Multi-pass search (automated + manual)
- Test deployment on a fresh Azure subscription before OSS release
- Encourage community PRs to report any missed references

### R2: Decommission breaks existing workflows
**Risk:** Running `azd down` on Pascal's deployment could disrupt active development or demos.

**Mitigation:**
- Schedule decommission immediately before OSS release (not during active development)
- Back up any critical data (if any exists)
- Document that this is a one-time operation for OSS preparation

### R3: Deployment instructions incomplete or incorrect
**Risk:** New users cannot deploy successfully due to missing steps or errors in README.

**Mitigation:**
- Test deployment on a fresh Azure subscription + GitHub account
- Include troubleshooting section in README for common issues
- Use GitHub Issues to collect feedback post-release

### R4: .squad/ folder confusion
**Risk:** New users are confused by `.squad/` folder or think they need to set it up.

**Mitigation:**
- Document in README that `.squad/` is optional local tooling (not required for deployment)
- OR add `.squad/` to `.gitignore` and remove from repo (if it's truly internal-only)

### R5: GitHub Actions OIDC setup complexity
**Risk:** OIDC federated credential setup is complex; users may struggle with Entra ID app registration and federation.

**Mitigation:**
- Provide step-by-step instructions with screenshots (or link to Azure docs)
- Offer manual `azd up` as simpler alternative
- Note that OIDC setup is optional (manual deployment is fully supported)

### R6: License choice misalignment
**Risk:** MIT license may not align with all contributor expectations (e.g., preference for copyleft).

**Mitigation:**
- MIT is industry standard for reference implementations
- Document license clearly in README and LICENSE file
- Accept that not all users will agree (standard OSS trade-off)

## Migration Plan

**Pre-release steps:**
1. Create OpenSpec change proposal (this document)
2. Implement all tasks (README rewrite, scrubbing, license addition, etc.)
3. Test deployment on a fresh Azure subscription + GitHub account
4. Run `azd down --force --purge` on Pascal's existing environment
5. Redeploy from scratch using updated README instructions to validate
6. Make repository public on GitHub

**Rollback strategy:**
- If critical issues found post-release: revert repository to private, fix issues, re-release
- If deployment instructions fail: collect feedback via GitHub Issues, iterate on README

**Post-release monitoring:**
- GitHub Issues for bug reports and deployment issues
- GitHub Discussions for Q&A
- Monitor initial deployments via community feedback

## Open Questions

1. **Screenshot content:** Should screenshot show voice session in progress, or just the main dashboard?
   - **Recommendation:** Main dashboard with voice button visible (shows core UX without requiring active session)

2. **.squad/ folder disposal:** Should `.squad/` be removed from repo or documented as optional?
   - **Recommendation:** Add note in README that `.squad/` is project-specific metadata (safe to ignore for new users)

3. **Custom domain handling:** Should deployment support custom domains out-of-the-box, or document as optional post-deployment step?
   - **Recommendation:** Document as optional (advanced users only); default deployment uses `*.azurewebsites.net`

4. **Entra ID app registration:** Should README include full Entra ID setup, or link to Azure docs?
   - **Recommendation:** Provide high-level steps + link to official docs (avoid duplicating Microsoft's documentation)

5. **Multi-region deployment:** Should initial OSS release support multi-region, or simplify to single region?
   - **Recommendation:** Single region for initial release (East US 2 as default); multi-region can be added later

6. **Mobile app distribution:** Should Expo build/submit be documented, or just local dev?
   - **Recommendation:** Local dev only for initial release (Expo build requires Apple Developer account, out of scope for general OSS users)
