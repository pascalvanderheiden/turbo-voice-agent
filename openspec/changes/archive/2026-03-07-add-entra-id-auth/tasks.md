# Tasks: Add Entra ID Authentication

## Phase 1: Backend Auth Middleware
- [x] Install `python-jose[cryptography]` dependency
- [x] Create `backend/app/auth.py` - JWT validation module: fetch Entra JWKS keys (cached 24h), validate Bearer token signature against public keys, extract user claims (oid, name, preferred_username, tid), validate `aud` matches `api://<client-id>`, reject non-turboagent.nl tenant
- [x] Create `backend/app/middleware/auth_middleware.py` - FastAPI middleware that validates Authorization header on all `/api/*` routes, injects `request.state.user_id` and `request.state.user_claims`, skips health/docs endpoints; when `AUTH_DISABLED=true`, use mock user with fixed oid
- [x] Wire auth middleware in `backend/app/main.py`
- [x] Update CORS in `backend/app/main.py` to use specific origins from `ALLOWED_ORIGINS` env var (comma-separated) instead of wildcard `*`, with `allow_credentials=True`

## Phase 2: User Profile Service
- [x] Create `backend/app/models/user_profile.py` - UserProfile model (userId, displayName, email, locale, avatarUrl, lastLoginAt)
- [x] Create `backend/app/services/user_profile_service.py` - Cosmos DB-backed user profile service using `profiles` container with `/userId` partition key; upsert on login, get/update profile
- [x] Create `backend/app/routes/user.py` - `GET /api/me` (profile), `PATCH /api/me` (update locale), `GET /api/me/photo` (proxy to Graph API for profile photo using user's access token from request)
- [x] Wire user service and routes in `backend/app/main.py`
- [x] Add `profiles` container to Cosmos DB Bicep module (`infra/modules/cosmos-db.bicep`)

## Phase 3: Per-User Data Scoping
- [x] Update all service methods to accept and filter by `user_id` parameter: notes, brainstorm (ideas), research, specs, dev tasks, marketing videos
- [x] Update all route handlers to pass `request.state.user_id` to service calls
- [x] Ensure Cosmos DB queries use `userId` as partition key filter for efficient lookups

## Phase 4: WebSocket Auth
- [x] Update `backend/app/routes/voice_ws.py` - extract `token` query parameter from WebSocket upgrade, validate JWT (reuse auth.py), reject unauthenticated connections, pass user_id to voice session and supervisor agent; when `AUTH_DISABLED=true`, use mock user

## Phase 5: Frontend MSAL Integration
- [x] Install `@azure/msal-react` and `@azure/msal-browser`
- [x] Create `frontend/src/lib/msal-config.ts` - MSAL PublicClientApplication config with tenant ID, client ID, redirect URI, scopes (`api://<client-id>/access`, `User.Read`)
- [x] Create `frontend/src/components/providers/auth-provider.tsx` - MsalProvider wrapper with login redirect on unauthenticated
- [x] Update `frontend/src/app/layout.tsx` - wrap app with AuthProvider (outermost provider)
- [x] Update `frontend/src/lib/api.ts` - add `getAccessToken()` helper using MSAL, attach Bearer token to all fetch calls

## Phase 6: Profile UI
- [x] Create `frontend/src/components/layout/user-menu.tsx` - dropdown menu with profile photo (or initials fallback), display name, email, language selector (en/nl), and logout button
- [x] Update `frontend/src/components/layout/site-header.tsx` - replace language toggle with UserMenu component in top-right position
- [x] Update `frontend/src/lib/i18n.tsx` - on locale change, persist to backend via `PATCH /api/me`; on init, fetch locale from `/api/me` instead of localStorage
- [x] Add profile photo fetch from `/api/me/photo` with fallback to initials avatar

## Phase 7: Voice Session Auth
- [x] Update `frontend/src/lib/voice-context.tsx` (or voice provider) - attach access token as query param when connecting to `/ws/voice?token=...`
- [x] Handle 401/disconnect on token expiry - silent renew + reconnect

## Phase 8: Azure Infrastructure Updates
- [x] Add `entraTenantId`, `entraClientId`, and `customDomainName` params to `infra/main.bicep`
- [x] Add `ENTRA_TENANT_ID` and `ENTRA_CLIENT_ID` env vars to `infra/modules/container-app-backend.bicep`
- [x] Add `ALLOWED_ORIGINS` env var to backend container app (set to `https://voice.turboagent.nl,https://<default-fqdn>`)
- [x] Update `infra/modules/container-app-backend.bicep` CORS policy: replace `allowedOrigins: ['*']` with specific frontend URLs (custom domain + default FQDN), add `allowCredentials: true`
- [x] Add custom domain binding to `infra/modules/container-app-frontend.bicep` for `voice.turboagent.nl` with Azure-managed TLS certificate
- [x] Add `NEXT_PUBLIC_ENTRA_CLIENT_ID`, `NEXT_PUBLIC_ENTRA_TENANT_ID`, `NEXT_PUBLIC_ENTRA_REDIRECT_URI` as Docker build ARGs in `frontend/Dockerfile`
- [x] Update `azure.yaml` frontend service to pass `docker.buildArgs` for NEXT_PUBLIC vars (redirect URI = `https://voice.turboagent.nl`)
- [x] Add `profiles` container to Cosmos DB Bicep module
- [x] Update `infra/main.parameters.json` with `entraTenantId`, `entraClientId`, and `customDomainName` placeholder values

## Phase 9: DNS Configuration (Manual)
- [ ] Add CNAME record: `voice` -> `ca-frontend-2mta7feoalzyq.icymoss-114d3a42.eastus2.azurecontainerapps.io`
- [ ] Add TXT record: `asuid.voice` -> verification ID from Azure custom domain binding
- [ ] Verify custom domain is bound and TLS certificate is provisioned in Azure Portal

## Phase 10: Documentation & Config
- [x] Update `backend/.env.example` with `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `AUTH_DISABLED`, `ALLOWED_ORIGINS`
- [x] Update `frontend/.env.example` with `NEXT_PUBLIC_ENTRA_CLIENT_ID`, `NEXT_PUBLIC_ENTRA_TENANT_ID`, `NEXT_PUBLIC_ENTRA_REDIRECT_URI`
- [x] Update `README.md` - add Entra ID setup instructions (reference proposal.md setup guide), custom domain setup, new environment variables, auth bypass for local dev
