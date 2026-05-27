# HTTPX Transient Retry Pattern

Use this pattern when an HTTPX call has known transient failure modes but non-transient 4xx responses must fail fast.

## Pattern

1. Keep retry scope narrow: wrap only the operation that benefits from retry, not every endpoint by default.
2. Define explicit transient predicates:
   - status code allowlist/ranges (for example, 429 and 5xx),
   - known provider body substrings,
   - specific transport exceptions (`ConnectError`, `ReadTimeout`, `PoolTimeout`).
3. Use a small bounded attempt count and exponential backoff with jitter.
4. Log every retryable failed attempt internally with structured fields: event, identifier, attempt, max attempts, status code, and latency.
5. Do not emit user-facing errors on retryable attempts; emit once after exhaustion using the existing terminal-error shape.
6. Never retry ordinary 4xx responses unless explicitly listed.

## Test notes

- `respx` can model repeated outcomes with `side_effect=[httpx.Response(...), ..., httpx.Response(...)]`.
- Transport exceptions can be mixed into `side_effect` before a final success response.
- Patch sleeps to a no-op in unit tests so retry coverage stays fast.
