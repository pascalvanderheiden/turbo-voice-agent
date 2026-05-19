# Keaton — History

## Project Context
Turbo Voice Agent — real-time conversational AI voice agent with multi-agent orchestration.
Stack: Python 3.12/FastAPI, Next.js 15, React Native/Expo, Azure (Cosmos DB, Voice Live, Container Apps, ACI sandbox), Bicep IaC.
User: the project maintainer.

Architecture: SupervisorAgent routes to 12 specialist agents. ACI sandbox runs Copilot CLI pipelines. WebSocket voice streaming via Voice Live API.

## Learnings
- 2026-05-19: OSS anonymization pass pattern — seeded maintainer references at the top of `.squad/agents/*/history.md` can be revised for OSS readiness even when the files are otherwise append-only. Preserve later learning entries unless they contain direct personal identifiers.
- 2026-05-19: Cross-repo personal-reference audit pattern — pair automated grep sweeps for maintainer identifiers and GUIDs with manual review of high-risk config/docs files, then record both actionable findings and intentional false positives (for example Azure built-in role IDs) in a central audit document before re-running verification greps.
