# OSS Azure Parameterization

## When to use

Use this pattern when preparing an Azure + `azd` project for open-source release and you need deployment config to work in any subscription without personal identifiers.

## Pattern

1. Keep Bicep parameters generic and environment-driven.
   - Required values should stay parameterized without baked-in tenant/client IDs.
   - Optional values should use empty-string defaults in `infra/main.parameters.json` (for example `${CUSTOM_DOMAIN_NAME=}`).
2. Put runtime deployment instructions next to `azure.yaml`.
   - Document required `azd env set` names in comments.
   - Add `pipeline.variables` / `pipeline.secrets` so `azd pipeline config` knows about custom workflow inputs.
3. Keep GitHub Actions OIDC-only.
   - Use `azure/login@v2` and `azd auth login --federated-credential-provider github`.
   - Move every environment-specific workflow value into `vars.*` or `secrets.*`.
4. Make advanced platform features optional.
   - Custom domains, certificates, and extra deployer RBAC should all be opt-in.
   - Provide safe defaults that still allow a plain `*.azurecontainerapps.io` deployment.
5. Validate both layers.
   - Run `az bicep build --file infra/main.bicep`.
   - Run local `azd env set ...` commands against a throwaway env to verify parameter injection before touching CI.
6. Audit history before release.
   - Search for tracked `.env*` files, key material filenames, and secret patterns.
   - If private key files ever landed in git, assume compromise and recommend rotation plus a history rewrite decision.

## Reusable checklist

- [ ] No personal tenant / subscription / principal IDs hardcoded in Bicep or workflow files
- [ ] Optional custom domain path works with empty env values
- [ ] `azure.yaml` documents required environment keys
- [ ] Workflow uses OIDC and generic repo vars/secrets only
- [ ] Git history audit written down before public release
