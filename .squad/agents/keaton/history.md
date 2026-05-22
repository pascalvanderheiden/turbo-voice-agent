# Keaton — History

## Project Context
Turbo Voice Agent — real-time conversational AI voice agent with multi-agent orchestration.
Stack: Python 3.12/FastAPI, Next.js 15, React Native/Expo, Azure (Cosmos DB, Voice Live, Container Apps, ACI sandbox), Bicep IaC.
User: the project maintainer.

Architecture: SupervisorAgent routes to 12 specialist agents. ACI sandbox runs Copilot CLI pipelines. WebSocket voice streaming via Voice Live API.

## Team Updates

- **2026-05-22:** Verbal diagnosed and recovered failed `azd up` deployment caused by Bicep RBAC module dependency ordering issue. Backend Container App identity could not pull from ACR (401) because RBAC module never executed — it depends on backend succeeding first (circular dependency). Immediate fix: manual `az role assignment create` granted AcrPull to backend identity. **Permanent fix required:** Two-phase RBAC Bicep refactor — create `rbac-acr-only.bicep` module (AcrPull only, immediate post-identity-creation) and update main.bicep ordering to invoke it before backend health check. See `.squad/decisions/decisions.md` for full decision and implementation plan. See `.squad/skills/aca-provision-recovery/SKILL.md` for runbook.
- **2026-05-20:** Verbal deployed quota-aware region selector (`infra/scripts/select-model-regions.sh`) as `azd` preprovision hook. Three new env vars in CI/CD: `AZURE_OPENAI_LOCATION_PRIMARY`, `AZURE_OPENAI_LOCATION_VOICE`, `AZURE_OPENAI_LOCATION_RESEARCH`. Resolves fresh `azd up` quota failures on new subscriptions. See `.squad/decisions/decisions.md` for full spec.

## Learnings
- 2026-05-19: OSS anonymization pass pattern — seeded maintainer references at the top of `.squad/agents/*/history.md` can be revised for OSS readiness even when the files are otherwise append-only. Preserve later learning entries unless they contain direct personal identifiers.
- 2026-05-19: Cross-repo personal-reference audit pattern — pair automated grep sweeps for maintainer identifiers and GUIDs with manual review of high-risk config/docs files, then record both actionable findings and intentional false positives (for example Azure built-in role IDs) in a central audit document before re-running verification greps.
