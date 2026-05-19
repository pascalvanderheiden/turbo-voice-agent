# OSS Readiness Audit

## Purpose
Run a maintainers-first scrub before publishing a repository, with emphasis on personal identifiers, environment-specific references, and append-only project metadata.

## Workflow
1. Run global grep sweeps for maintainer names, usernames, email local-parts, and GUID patterns.
2. Exclude generated directories (`.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, `.next`).
3. Manually inspect high-risk files such as IaC, workflow YAML, env examples, README, OpenSpec artifacts, and project metadata folders like `.squad/`.
4. Classify findings by kind (name, path, GUID, domain, endpoint) and owner (infra, backend, frontend/docs, supervisor).
5. Scrub seeded or optional metadata in place when it is safe, but preserve historical content unless it directly exposes the maintainer identity.
6. Record intentional false positives (for example Azure built-in role IDs) so later reviewers do not re-open them.
7. Re-run verification greps and capture the post-scrub result in a single audit document.

## Heuristics
- Replace direct personal references with `the maintainer`, `Project Maintainer`, or a neutral placeholder.
- Replace local absolute paths with generic placeholders such as `/path/to/<repo>`.
- For append-only logs, prefer targeted changes to maintainer-identifying lines (`Requested by`, seeded headers) over broad rewrites.
- If optional metadata stays in OSS, add a README note clarifying that it is not required for deployment.
