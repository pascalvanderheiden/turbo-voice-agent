### 2026-05-22T14:00Z: azure.yaml sandbox host fix — chose hook-based ACR build
**By:** Pascal (via Verbal)
**What:** Removed the `sandbox` service from `azure.yaml` entirely. The image is now built directly into ACR by `infra/scripts/build-sandbox-image.sh` (azd `postprovision` + `postdeploy` hook) using `az acr build`, producing `${ACR}/turbo-voice-agent/sandbox:latest` — the exact tag the dynamic session pool references (`infra/main.bicep:263`).

**Options considered:**
- (a) `host: containerregistry` — azd does not document this as a stable host; risk of breakage.
- (b) **Chosen** — drop service entry, build via hook. Eliminates the misleading `host: containerapp` (the `ca-sandbox-*` Container App was deleted in Phase 1 and was the historical cause of 20-min "Operation expired" failures). Also replaces the older `tag-sandbox-latest.sh` push-then-retag dance with a single direct build.

**Why:** Phase 1 deleted the sandbox Container App. With no target, azd's `containerapp` host had nothing to update and re-introduced the deployment hang we were trying to escape. The session pool consumes the image directly from ACR; we only need a build/push, not a CA revision.

**Validation:** `az bicep build --file infra/main.bicep` clean. `bash -n` on both new scripts passes. Tag matches Bicep reference.
