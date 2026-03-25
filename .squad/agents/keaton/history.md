# Keaton — History

## Project Context
Turbo Voice Agent — real-time conversational AI voice agent with multi-agent orchestration.
Stack: Python 3.12/FastAPI, Next.js 15, React Native/Expo, Azure (Cosmos DB, Voice Live, Container Apps, ACI sandbox), Bicep IaC.
User: Pascal van der Heiden.

Architecture: SupervisorAgent routes to 12 specialist agents. ACI sandbox runs Copilot CLI pipelines. WebSocket voice streaming via Voice Live API.

## Learnings
