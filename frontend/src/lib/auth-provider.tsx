"use client";

import { ReactNode, useEffect, useState } from "react";
import { MsalProvider, useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { getMsalInstance, loginScopes } from "./msal-config";

function AuthGate({ children }: { children: ReactNode }) {
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (inProgress !== InteractionStatus.None) return;

    if (!isAuthenticated) {
      instance.loginRedirect(loginScopes).catch((err) => {
        console.error("Login redirect failed:", err);
      });
    } else {
      setReady(true);
    }
  }, [isAuthenticated, inProgress, instance]);

  if (!ready) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full mx-auto" />
          <p className="text-sm text-muted-foreground">Signing in...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Auth provider that wraps the app with MSAL.
 * When NEXT_PUBLIC_ENTRA_CLIENT_ID is not set, auth is disabled (local dev).
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const clientId = process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID;

  // No Entra config = skip auth (local dev)
  if (!clientId) {
    return <>{children}</>;
  }

  const msalInstance = getMsalInstance();

  return (
    <MsalProvider instance={msalInstance}>
      <AuthGate>{children}</AuthGate>
    </MsalProvider>
  );
}
