import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy OAuth callback to the backend.
 * Microsoft redirects here (frontend domain) after consent, but the
 * token exchange handler lives on the backend.
 */
export async function GET(request: NextRequest) {
  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const { searchParams } = request.nextUrl;
  const qs = searchParams.toString();
  const target = `${backendUrl}/api/auth/callback/microsoft-todo?${qs}`;

  try {
    const backendRes = await fetch(target, {
      redirect: "manual",
      signal: AbortSignal.timeout(25_000),
    });

    // The backend returns a 302/307 redirect to /settings?todo_connected=...
    const location = backendRes.headers.get("location");
    if (location) {
      return NextResponse.redirect(location, 307);
    }

    // Fallback: forward the response as-is
    return new NextResponse(backendRes.body, {
      status: backendRes.status,
      headers: {
        "content-type":
          backendRes.headers.get("content-type") || "text/plain",
      },
    });
  } catch {
    // Timeout or network error — redirect to settings with error
    const frontendBase = request.nextUrl.origin;
    return NextResponse.redirect(
      `${frontendBase}/settings?todo_connected=error`,
      307,
    );
  }
}
