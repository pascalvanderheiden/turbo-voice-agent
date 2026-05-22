### 2026-05-22T15:30Z: Sandbox image build moved to preprovision (stale-image / pool-crash recovery)
**By:** Verbal (for Pascal)
**What:** Added `bash infra/scripts/build-sandbox-image.sh` to the `preprovision` hook in `azure.yaml` (in addition to the existing `postprovision` and `postdeploy` invocations).

**Why:** After the UAMI ACR-Pull fix landed (`efd6565`), `azd provision` still failed at the session pool with `pool is in bad status because pods are crashing, crashing pods count: 0` and `nodeCount: 0`. Diagnosis traced the failure to a stale ACR image:

- Image `turbo-voice-agent/sandbox:latest` in ACR was built `2026-05-22T11:17:08Z`.
- Phase 5 commit `ceae508` (adds `/health`, `/ready`, marker file) is dated `2026-05-22T11:43:04Z` — **26 minutes after** the image was built.
- The pool's Liveness probe (`GET /health`, 10s) and Startup probe (`GET /ready`, 5s × 30) hit endpoints that don't exist in the stale image → 404 → pods killed by Liveness within ~30s → pool reports "crashing" with `nodeCount: 0`.
- `build-sandbox-image.sh` was wired only to `postprovision`/`postdeploy`. Because provision aborted at the pool, the post-hooks never ran, so the image stayed stale forever — a chicken-and-egg: pool fails because image is stale, image won't rebuild because pool fails.

**Fix shape:** invoke the build script in `preprovision` as well. The script already exits 0 cleanly when `AZURE_CONTAINER_REGISTRY` is unset (first-ever run), so it is safe to add unconditionally. On every subsequent run the image is rebuilt against the current `sandbox/` source before the pool is reconciled, eliminating the staleness window. Postprovision/postdeploy stay in place (no harm — `az acr build` is idempotent against `:latest`).

**Immediate recovery applied:**
1. Manually ran `bash infra/scripts/build-sandbox-image.sh` to rebuild `:latest` with the current entrypoint.sh + server.js.
2. Deleted the failed pool: `az resource delete --ids .../sessionPools/sp-sandbox-2mta7feoalzyq`.
3. Pascal can now re-run `azd provision`; the pool will pull the fresh image, probes return 200, deployment succeeds.

**No backend / Bicep / sandbox source changes required.** The Phase 5 sandbox code is correct as written; the failure was purely a deployment-orchestration ordering bug.

**Skill update:** `.squad/skills/aca-provision-recovery/SKILL.md` gained a new section "Session Pool Variant: Stale Image Probe Mismatch (Postprovision Chicken-and-Egg)" with symptoms, diagnosis steps (image createdTime vs git log timestamp), recovery, and the preprovision-hook prevention.

**Cross-applicability:** any ACA resource (current or future) that has the shape "image build hook on success → resource create that pulls image → image rebuild on success" is latently vulnerable to the same loop. Mitigation: ensure at least one image-build invocation runs *before* the resource is reconciled.
