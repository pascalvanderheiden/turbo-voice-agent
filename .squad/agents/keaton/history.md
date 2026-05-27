# Keaton — History

## Project Context
Turbo Voice Agent — real-time conversational AI voice agent with multi-agent orchestration.
Stack: Python 3.12/FastAPI, Next.js 15, React Native/Expo, Azure (Cosmos DB, Voice Live, Container Apps, ACI sandbox), Bicep IaC.
User: the project maintainer.

Architecture: SupervisorAgent routes to 12 specialist agents. ACI sandbox runs Copilot CLI pipelines. WebSocket voice streaming via Voice Live API.

## Team Updates

- **2026-05-22 (3rd recovery session):** Verbal diagnosed and recovered failed `azd up` deployment caused by Bicep RBAC module dependency ordering issue. Backend Container App identity could not pull from ACR (401) because RBAC module never executed — it depends on backend succeeding first (circular dependency). Immediate fix: manual `az role assignment create` granted AcrPull to backend identity. Later, resolved RBAC module collision (deterministic naming conflict with manual role assignments from prior sessions) by deleting 3 pre-existing AcrPull assignment GUIDs. **⚠️ URGENT BLOCKER:** Two-phase RBAC Bicep refactor required before next clean deploy — single-phase module insufficient for timing-sensitive deployments. Create `rbac-acr-only.bicep` module (AcrPull only, immediate post-identity-creation) and update main.bicep ordering to invoke before backend health check. See `.squad/decisions/decisions.md` for full decision and implementation plan. See `.squad/skills/aca-provision-recovery/SKILL.md` for runbook. **Current state:** Container Apps running on cached images; user to run `azd provision` → `azd deploy`.
- **2026-05-20:** Verbal deployed quota-aware region selector (`infra/scripts/select-model-regions.sh`) as `azd` preprovision hook. Three new env vars in CI/CD: `AZURE_OPENAI_LOCATION_PRIMARY`, `AZURE_OPENAI_LOCATION_VOICE`, `AZURE_OPENAI_LOCATION_RESEARCH`. Resolves fresh `azd up` quota failures on new subscriptions. See `.squad/decisions/decisions.md` for full spec.

## Learnings
- 2026-05-19: OSS anonymization pass pattern — seeded maintainer references at the top of `.squad/agents/*/history.md` can be revised for OSS readiness even when the files are otherwise append-only. Preserve later learning entries unless they contain direct personal identifiers.
- 2026-05-19: Cross-repo personal-reference audit pattern — pair automated grep sweeps for maintainer identifiers and GUIDs with manual review of high-risk config/docs files, then record both actionable findings and intentional false positives (for example Azure built-in role IDs) in a central audit document before re-running verification greps.

- 2026-05-22: Refreshed `.github/copilot-instructions.md` for OSS readiness + dynamic sessions architecture. Surgical edits only (130 → 140 lines): added dynamic session pool to stack + Backend patterns, documented `SessionSandboxClient` with docker-compose fallback (`http://sandbox:3000`), fixed `function_handler.py` path, clarified `CUSTOM_DOMAIN_NAME`/`EXISTING_CERT_NAME` are optional with ACA default FQDN supporting auth, added Squad + OpenSpec mentions under Git workflow. Verified zero stale ACI/SANDBOX_URL/USE_ACI_SANDBOX references remain.

## Learnings
- 2026-05-22: Doc-refresh pattern for `.github/copilot-instructions.md` — file is AI-agent guidance, not full docs. Keep ~120–180 lines, preserve existing structure, surgical edits where reality drifted. Validate with grep sweep for stale terms (`ACI`, `SANDBOX_URL`, etc.) before commit. Always verify file paths actually exist (`grep -n`, `ls`) before referencing them.
- 2026-05-22: OSS readiness for instruction files — call out OPTIONAL deployment knobs explicitly (custom domain, cert) and mention the fallback path (ACA default FQDN with dynamic redirect URI). OSS readers don't share the original deployer's setup; explicit defaults beat implicit ones.

- **2026-05-22 (Scribe stamp):** `.github/copilot-instructions.md` refresh committed as `4ea10d4`. Aligned with sandbox-dynamic-sessions Phases 1–3 + 5. Phase 4/6/7/8/9 still pending; doc may need a second pass after Phase 7 (env/config) lands.

- **2026-05-27:** Redfoot archived `sandbox-dynamic-sessions` OpenSpec change (49/50 tasks complete, production verified); 7 spec deltas merged. See `.squad/decisions/decisions.md`.
