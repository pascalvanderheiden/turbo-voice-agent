# Decision Drop: Transient Pool Allocation Retry Shipped

**Agent:** Fenster  
**Status:** Shipped  
**Commit:** `986f326392de2da95eb8e1109a4fd1e54ead3608`

## Retry parameters

- Scope: backend `_sandbox_exec` POST `/tasks` only.
- Attempts: 3 total attempts.
- Backoff: exponential 1s → 2s → 4s policy with ±25% jitter. With 3 total attempts, sleeps occur before retry attempts using the 1s and 2s slots; the 4s slot is retained as the next value for the same policy shape.
- User stderr: emitted only after final failure, preserving the existing terminal error schema.
- Internal observability: retryable attempts log `sandbox.session.transient_retry` with identifier, attempt, max attempts, status code, and latency.

## Trigger conditions

Retry is enabled for:

- HTTP 5xx from the session pool.
- HTTP 429.
- Response body containing `Error happened when allocating pod` regardless of status.
- Response body containing `sessionpool` with status >= 500.
- `httpx.ConnectError`, `httpx.ReadTimeout`, and `httpx.PoolTimeout`.

Do not retry:

- HTTP 4xx except 429, including auth/bad-request failures such as `400 missing token`.
