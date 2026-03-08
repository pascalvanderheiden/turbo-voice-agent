# Proposal: Add Entra ID Authentication

## Why
The application currently has no authentication - all routes are public and data is not isolated per user. Adding Microsoft Entra ID SSO restricts access to the turboagent.nl domain and enables per-user data isolation across all services.

## What Changes
- Add MSAL.js (@azure/msal-react) to the Next.js frontend for Entra ID SSO login/logout
- Add backend middleware to validate Entra ID access tokens (JWT) on all API routes using public JWKS keys (no client secret needed)
- Restrict access to users in the **turboagent.nl** tenant domain
- Add user profile UI in the site header (avatar, name, logout, language preference)
- Move language selector from header actions into the profile dropdown menu
- Store language preference per user in Cosmos DB instead of localStorage
- Scope all data (notes, ideas, research, specs, dev tasks, marketing videos) to the authenticated user's ID via Cosmos DB `/userId` partition key
- Authenticate WebSocket connections (voice) via token query parameter
- Pass user context through supervisor agent to all specialist agents
- Update Bicep infrastructure to pass Entra env vars to container apps
- Update CORS to use specific origins (not wildcard) to support credentials
- Configure custom domain `voice.turboagent.nl` for the frontend Container App with managed TLS certificate

## Impact
- Affected specs: `web-app`, `agent-orchestration`, `realtime-voice`, `azure-infrastructure`
- Affected services: All services gain userId scoping (notes, brainstorm, research, spec, dev, marketing)
- New dependency: `@azure/msal-react`, `@azure/msal-browser` (frontend), `python-jose[cryptography]` (backend)
- New env vars: `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `NEXT_PUBLIC_ENTRA_CLIENT_ID`, `NEXT_PUBLIC_ENTRA_TENANT_ID`
- New Bicep params: `entraTenantId`, `entraClientId`, `customDomainName` (voice.turboagent.nl)
- **BREAKING**: All API calls now require a Bearer token; unauthenticated requests return 401

## Entra ID Manual Setup Guide

### Step 1: Register the Application in Azure Portal
1. Go to [Azure Portal](https://portal.azure.com) > **Microsoft Entra ID** > **App registrations** > **New registration**
2. Name: `Turbo Voice Agent`
3. Supported account types: **Accounts in this organizational directory only (turboagent.nl - Single tenant)**
4. Redirect URI: **Single-page application (SPA)** - `http://localhost:3000`
5. Click **Register**

### Step 2: Configure Authentication
1. Go to **Authentication** tab
2. Under **Single-page application** redirect URIs, add:
   - `http://localhost:3000` (local development)
   - `https://voice.turboagent.nl` (production custom domain)
   - `https://ca-frontend-2mta7feoalzyq.icymoss-114d3a42.eastus2.azurecontainerapps.io` (Azure default domain, as fallback)
3. Under **Implicit grant and hybrid flows**: leave unchecked (MSAL.js uses auth code flow with PKCE)
4. Under **Advanced settings**: set **Allow public client flows** to **No**

### Step 3: API Permissions
1. Go to **API permissions** tab
2. Ensure **Microsoft Graph > User.Read** (delegated) is present (added by default)
3. Click **Grant admin consent for turboagent.nl**

### Step 4: Expose an API (Backend Token Validation)
1. Go to **Expose an API** tab
2. Set **Application ID URI**: `api://<client-id>`
3. Add a scope: `api://<client-id>/access` with admin consent display name "Access Turbo Voice Agent"

### Step 5: Domain Restriction
- The app registration is set to **Single tenant** (turboagent.nl only)
- No additional configuration needed - only users with @turboagent.nl accounts can authenticate

### Step 6: Configure DNS for Custom Domain
1. Go to your DNS provider for `turboagent.nl`
2. Add a **CNAME** record:
   - Name: `voice`
   - Value: `ca-frontend-2mta7feoalzyq.icymoss-114d3a42.eastus2.azurecontainerapps.io`
3. Add a **TXT** record for domain verification (value provided by Azure during custom domain binding):
   - Name: `asuid.voice`
   - Value: `<verification-id from Azure>`

### Environment Variables (.env)

**Backend (.env)**:
```
ENTRA_TENANT_ID=<your-tenant-id>           # From Entra ID > Overview > Tenant ID
ENTRA_CLIENT_ID=<your-client-id>           # From App registration > Overview > Application (client) ID
AUTH_DISABLED=true                          # Set to true for local dev without Entra (optional)
```

**Frontend (.env)**:
```
NEXT_PUBLIC_ENTRA_CLIENT_ID=<your-client-id>     # Same client ID as backend
NEXT_PUBLIC_ENTRA_TENANT_ID=<your-tenant-id>     # Same tenant ID as backend
NEXT_PUBLIC_ENTRA_REDIRECT_URI=http://localhost:3000
```

**Bicep parameters (main.parameters.json)**:
```json
{
  "entraTenantId": { "value": "<your-tenant-id>" },
  "entraClientId": { "value": "<your-client-id>" },
  "customDomainName": { "value": "voice.turboagent.nl" }
}
```
