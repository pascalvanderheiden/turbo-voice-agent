## 1. Sandbox Dockerfile

- [x] 1.1 Add `mkdir -p /home/agent/.copilot/skills && chown agent:agent /home/agent/.copilot/skills` to `sandbox/Dockerfile`
- [x] 1.2 Create `sandbox/entrypoint.sh` that downloads skills from Blob Storage when `AZURE_STORAGE_ACCOUNT_NAME` is set, then starts the server
- [x] 1.3 Update Dockerfile `ENTRYPOINT` to use `entrypoint.sh` instead of direct `node server.js`

## 2. Docker Compose

- [x] 2.1 Add bind mount `.agents/skills/:/home/agent/.copilot/skills/:ro` to the sandbox service in `docker-compose.yml`
- [x] 2.2 Verify local dev: install a skill via the backend, restart sandbox, confirm skill is visible inside the container

## 3. Azure Infrastructure

- [x] 3.1 Add `AZURE_STORAGE_ACCOUNT_NAME` environment variable to `infra/modules/container-app-sandbox.bicep`
- [x] 3.2 Assign `Storage Blob Data Reader` role to the sandbox managed identity on the storage account
- [x] 3.3 Install `az` CLI or `azcopy` in the sandbox Dockerfile for blob download in entrypoint

## 4. Verification

- [x] 4.1 Local: rebuild sandbox (`docker compose build sandbox`), start, verify skills at `/home/agent/.copilot/skills/`
- [ ] 4.2 Azure: deploy, verify sandbox entrypoint downloads skills from Blob Storage
