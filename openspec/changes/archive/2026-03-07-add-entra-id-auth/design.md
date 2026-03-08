# Design: Add Entra ID Authentication

## Context
The app has no authentication. All REST endpoints and WebSocket connections are public. Data services use Cosmos DB with a `/userId` partition key pattern but it is not enforced because there is no authenticated user identity. The frontend stores locale in localStorage with no user association. The app runs both locally (Docker Compose / direct) and in Azure (Container Apps with managed identity). The frontend is accessed via a Container Apps auto-generated FQDN but should use a custom domain for production.

## Goals
- Single sign-on via Microsoft Entra ID for all users in turboagent.nl
- Per-user data isolation enforced at the backend service layer using Cosmos DB partition keys
- Profile UI with avatar, name, logout, and language preference
- Minimal disruption to existing agent orchestration and voice flows
- Works in both Azure Container Apps and local development
- Production-ready custom domain `voice.turboagent.nl` with managed TLS

## Non-Goals
- Role-based access control (RBAC) - all authenticated users have equal access
- Multi-tenant support - single tenant (turboagent.nl) only
- Mobile app auth (separate concern)
- Refresh token rotation or advanced token caching strategies

## Decisions

### Frontend Auth: MSAL.js with Auth Code Flow + PKCE
- **What**: Use `@azure/msal-react` with `PublicClientApplication` for SPA login
- **Why**: Microsoft's official library for Entra ID in React/Next.js SPAs; supports silent token renewal, popup/redirect login, and PKCE (no client secret needed on frontend)
- **Alternatives**: NextAuth.js (adds server-side complexity), custom OAuth flow (reinventing the wheel)

### Backend Auth: JWT Validation via JWKS (No Client Secret)
- **What**: FastAPI middleware that extracts Bearer token from `Authorization` header, validates JWT signature against Entra ID JWKS endpoint (`https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys`), and extracts `oid` (object ID) as user ID
- **Why**: Stateless validation using Entra's public keys; no client secret needed since the backend only validates tokens issued by the SPA (not exchanging auth codes)
- **Token claims used**: `oid` (user ID), `preferred_username` (email), `name` (display name), `tid` (tenant ID for domain check), `aud` (audience = `api://<client-id>`)
- **Library**: `python-jose[cryptography]` for JWT decode + `httpx` for JWKS fetch (cached 24h)

### User ID Strategy
- **What**: Use the Entra `oid` (Object ID, a GUID) as the universal user ID across all services
- **Why**: Stable, unique per user, doesn't change if email changes; maps directly to Cosmos DB `/userId` partition key
- **Flow**: Token -> middleware extracts `oid` -> injects into `request.state.user_id` -> routes pass to services -> Cosmos DB queries filter by partition key

### WebSocket Auth
- **What**: Pass access token as query parameter `?token=...` on WebSocket upgrade
- **Why**: WebSocket protocol doesn't support custom headers during handshake; query param is the standard pattern for SPA WebSocket auth
- **Validation**: Same JWT validation as REST middleware, applied before accepting the upgrade

### Language Preference Storage
- **What**: Store `locale` preference in a user profile document in Cosmos DB (same database, new `profiles` container with `/userId` partition key)
- **Why**: Enables language to persist across devices/browsers; leverages existing Cosmos DB infrastructure
- **Migration**: On first login, if localStorage has a locale, send it to backend to seed the profile

### Profile Picture
- **What**: Fetch from Microsoft Graph API (`/me/photo/$value`) using the user's access token
- **Why**: Entra tokens for Graph include the user's profile photo; no need for custom avatar upload
- **Fallback**: Show initials avatar when no photo is available

### CORS Configuration
- **What**: Replace wildcard `*` CORS origins with specific allowed origins
- **Why**: `credentials: include` (needed for auth tokens) is incompatible with wildcard origins
- **Origins**: `http://localhost:3000` (local dev) + `https://voice.turboagent.nl` (production) + Azure default FQDN (fallback)
- **Implementation**: Bicep passes `ALLOWED_ORIGINS` env var to backend container app; backend reads and splits on comma

### Custom Domain: voice.turboagent.nl
- **What**: Bind `voice.turboagent.nl` as a custom domain on the frontend Container App with Azure-managed TLS certificate
- **Why**: Professional URL for production use; avoids exposing the auto-generated Container Apps FQDN to end users
- **DNS**: CNAME `voice` -> Container App default FQDN + TXT `asuid.voice` for domain verification
- **TLS**: Azure Container Apps managed certificate (auto-provisioned and renewed)
- **Implementation**: Add custom domain binding + managed certificate in `container-app-frontend.bicep`; MSAL redirect URI uses `https://voice.turboagent.nl`

### NEXT_PUBLIC_ Environment Variables in Docker
- **What**: Use Docker build ARGs to inject `NEXT_PUBLIC_ENTRA_*` values at build time
- **Why**: Next.js inlines `NEXT_PUBLIC_*` variables at build time; they are not available at runtime
- **Implementation**: Add `ARG NEXT_PUBLIC_ENTRA_CLIENT_ID` and `ARG NEXT_PUBLIC_ENTRA_TENANT_ID` to frontend Dockerfile; azd passes these during remote build via `docker.buildArgs` in azure.yaml
- **Local dev**: `.env` file provides these variables to `next dev` directly (no Docker needed)
- **Redirect URI**: Build ARG `NEXT_PUBLIC_ENTRA_REDIRECT_URI` set to `https://voice.turboagent.nl` for Azure builds, `http://localhost:3000` for local

### Auth Bypass for Local Development
- **What**: `AUTH_DISABLED=true` env var skips JWT validation and uses a mock user
- **Why**: Allows local development and testing without Entra ID configuration
- **Guard**: Only works when `AUTH_DISABLED=true` is explicitly set; never in Azure (not in Bicep env vars)

## Risks / Trade-offs
- **Risk**: JWKS endpoint dependency - if Entra's key endpoint is unreachable, no auth possible -> Mitigation: cache JWKS keys with 24h TTL
- **Risk**: Token expiry during long voice sessions (1h default) -> Mitigation: MSAL silent token renewal + reconnect on 401
- **Risk**: Breaking change for all API consumers -> Mitigation: `AUTH_DISABLED=true` for local dev
- **Risk**: DNS propagation delay for custom domain -> Mitigation: keep Azure default FQDN as fallback redirect URI
- **Trade-off**: Query param token for WebSocket is visible in server logs -> acceptable for internal app; use short-lived tokens
- **Trade-off**: NEXT_PUBLIC_ baked at build time means changing Entra config requires rebuild -> acceptable since Entra config rarely changes

## Open Questions
- None - single tenant, no RBAC, standard MSAL pattern
