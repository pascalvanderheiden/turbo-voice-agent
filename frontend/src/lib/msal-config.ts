"use client";

import { PublicClientApplication, Configuration, LogLevel } from "@azure/msal-browser";

const clientId = process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID || "";
const tenantId = process.env.NEXT_PUBLIC_ENTRA_TENANT_ID || "";
const redirectUri = process.env.NEXT_PUBLIC_ENTRA_REDIRECT_URI || "http://localhost:3000";

export const msalConfig: Configuration = {
  auth: {
    clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri,
    postLogoutRedirectUri: redirectUri,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
  system: {
    loggerOptions: {
      logLevel: LogLevel.Warning,
      loggerCallback: (level, message) => {
        if (level === LogLevel.Error) console.error("[MSAL]", message);
      },
    },
  },
};

export const loginScopes = {
  scopes: [`api://${clientId}/access`, "User.Read"],
};

export const graphScopes = {
  scopes: ["User.Read"],
};

let _msalInstance: PublicClientApplication | null = null;

export function getMsalInstance(): PublicClientApplication {
  if (!_msalInstance) {
    _msalInstance = new PublicClientApplication(msalConfig);
  }
  return _msalInstance;
}
