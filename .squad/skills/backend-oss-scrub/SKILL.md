# Backend OSS Scrub

## When to use
Use this pattern when preparing backend code or configuration for public release and you need to remove environment-specific or personally identifying values.

## Steps
1. Search backend-owned files for maintainer identifiers (usernames, email-style names, custom domains), GUIDs, and Azure endpoint patterns.
2. Exclude local virtual environments and dependency folders from the audit so only repository artifacts are reviewed.
3. Replace real-looking endpoints, domains, emails, and IDs with neutral placeholders like `<your-openai-resource>` or `dev@example.com`.
4. In `.env.example`, add a short comment above each variable explaining what it is and where contributors can find the value.
5. Keep local-development defaults explicit when they are intentional, such as `AUTH_DISABLED=true`.
6. Re-run focused searches after edits to confirm the backend no longer contains personal or deployment-specific references.

## Output checklist
- `pyproject.toml` metadata is generic and license-aware.
- `.env.example` contains placeholders only, with no real keys or environment-specific endpoints.
- Backend code comments, mock users, and docstrings avoid custom domains or branded personal references.
- OpenSpec task checkboxes and team history are updated.
