# Squad Team

> turbo-voice-agent — Real-time conversational AI voice agent with multi-agent orchestration

## Coordinator

| Name | Role | Notes |
|------|------|-------|
| Squad | Coordinator | Routes work, enforces handoffs and reviewer gates. |

## Members

| Name | Role | Charter | Status |
|------|------|---------|--------|
| Keaton | Lead | `.squad/agents/keaton/charter.md` | 🟢 Active |
| Fenster | Backend Dev | `.squad/agents/fenster/charter.md` | 🟢 Active |
| McManus | Frontend Dev | `.squad/agents/mcmanus/charter.md` | 🟢 Active |
| Hockney | Mobile Dev | `.squad/agents/hockney/charter.md` | 🟢 Active |
| Verbal | Infra/DevOps | `.squad/agents/verbal/charter.md` | 🟢 Active |
| Kobayashi | Tester | `.squad/agents/kobayashi/charter.md` | 🟢 Active |
| Redfoot | Spec Manager | `.squad/agents/redfoot/charter.md` | 🟢 Active |
| Scribe | Scribe | `.squad/agents/scribe/charter.md` | 🟢 Active |
| Ralph | Work Monitor | — | 🔄 Monitor |

## Project Context

- **Project:** turbo-voice-agent
- **User:** Project Maintainer
- **Created:** 2026-03-25
- **Stack:** Python 3.12/FastAPI backend, Next.js 15 frontend, React Native/Expo mobile, Azure (Cosmos DB, Voice Live, Container Apps, ACI sandbox), Bicep IaC
- **Architecture:** Multi-agent voice system — SupervisorAgent routes to 12 specialist agents, ACI sandbox for Copilot CLI pipelines, WebSocket voice streaming
- **Branding:** Turbo Agent — hot pink (#E91E8C), cyan (#00D4FF), purple (#7B2FBE), dark mode default
