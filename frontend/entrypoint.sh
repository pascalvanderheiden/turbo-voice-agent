#!/bin/sh
# Replace build-time placeholders with runtime environment variables
if [ -n "$NEXT_PUBLIC_API_URL" ]; then
  find /app/.next -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_API_URL_PLACEHOLDER__|${NEXT_PUBLIC_API_URL}|g" {} +
  echo "Replaced API URL placeholder with: $NEXT_PUBLIC_API_URL"
fi
if [ -n "$NEXT_PUBLIC_ENTRA_CLIENT_ID" ]; then
  find /app/.next -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_ENTRA_CLIENT_ID_PLACEHOLDER__|${NEXT_PUBLIC_ENTRA_CLIENT_ID}|g" {} +
  echo "Replaced Entra Client ID placeholder"
fi
if [ -n "$NEXT_PUBLIC_ENTRA_TENANT_ID" ]; then
  find /app/.next -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_ENTRA_TENANT_ID_PLACEHOLDER__|${NEXT_PUBLIC_ENTRA_TENANT_ID}|g" {} +
  echo "Replaced Entra Tenant ID placeholder"
fi
if [ -n "$NEXT_PUBLIC_ENTRA_REDIRECT_URI" ]; then
  find /app/.next -name "*.js" -exec sed -i "s|__NEXT_PUBLIC_ENTRA_REDIRECT_URI_PLACEHOLDER__|${NEXT_PUBLIC_ENTRA_REDIRECT_URI}|g" {} +
  echo "Replaced Entra Redirect URI placeholder"
fi
exec node server.js
