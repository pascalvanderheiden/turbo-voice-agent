# Fenster — Sandbox token Cosmos fallback

**Date:** 2026-05-27
**Author:** Fenster
**Status:** Implemented

## Problem

After a backend redeploy, the process-local `_connection_store` is empty. `get_sandbox_user_token()` only read that cache, so the first dev-task for a user could omit `X-GH-Token` even though the user's encrypted `githubSandboxToken` was persisted in Cosmos. The sandbox then rejected prompt-based tasks with HTTP 400: `GitHub token required`.

## Fix

`get_sandbox_user_token(user_id, profile_service)` now keeps cache-first behavior, then falls back to `UserProfileService.get_profile(user_id)` on cache miss. When Cosmos contains `githubSandboxToken`, the helper warms `_connection_store`, decrypts the token, and returns it for the dev pipeline. The dev agent passes its injected profile service into this helper during `run_pipeline()`.

## Observability

When the Cosmos fallback recovers a cold cache, the backend logs structured event `sandbox.user_token.cache_miss_recovered` with `user_id` and `source: "cosmos"`.

## Verification

Added tests for cache hit/no Cosmos read, cache miss with Cosmos token/cache warm, and cache miss with no Cosmos token. Focused token tests pass. Full repo lint/test commands were also run; they currently fail on pre-existing unrelated backend formatting/lint and notes API baseline issues.
