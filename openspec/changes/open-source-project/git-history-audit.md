# Git History Audit

## Scope

Audit focused on repository history and current tracking status for:
- committed secret patterns (`AccountKey=`, API key-like strings)
- suspicious filenames (`.env`, `.env.local`, `key`, `password`, `secrets`)
- GUIDs in infrastructure and workflow files that could indicate subscription, tenant, or principal IDs

## Critical

| Commit | File | Finding | Recommendation |
| --- | --- | --- | --- |
| `4fdbe03` | `backend/key.pem` | Private key material filename was committed in the initial commit and is still tracked. | Treat the key as compromised. Rotate any certificate/keypair that used it, remove the file from the repository in a follow-up change, and strongly consider `git-filter-repo` before the public release. |

## Suspicious

| Commit | File | Finding | Recommendation |
| --- | --- | --- | --- |
| `4fdbe03` | `frontend/.!38121!.env.local` | Editor/temp variant of a local environment file was committed in the initial commit and is still tracked. | Review locally for sensitive values, remove it from git if not needed, and include it in any history-rewrite decision. |

## Clean / Informational

- No `AccountKey=` matches were returned by the history search.
- No API-key regex matches were returned by the history diff search.
- GUIDs found in `infra/` are built-in Azure role definition IDs (`AcrPull`, `Contributor`, `Storage Blob Data Reader`, etc.), not personal subscription, tenant, or principal IDs.
- The `endpoint=` history search returned an application-code hit (`3a134ce`) but did not surface a credential-bearing Azure endpoint assignment.
- Root `.gitignore` already covers `.env`, `.env.local`, and `.azure/`. Per team decision, `.squad/` remains intentionally kept in the repository.

## Summary

History is **not clean enough for OSS release yet** because a tracked private key filename exists in commit history and a suspicious local env artifact is also tracked. Pascal should decide whether to rotate only or rotate plus rewrite history; if the project is made public, assume `backend/key.pem` is already exposed.
