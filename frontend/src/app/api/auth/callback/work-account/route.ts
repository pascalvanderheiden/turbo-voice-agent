import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy OAuth callback to the backend for Work Account (WorkIQ).
 */
export async function GET(request: NextRequest) {
  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const { searchParams } = request.nextUrl;
  const qs = searchParams.toString();
  const target = `${backendUrl}/api/auth/callback/work-account?${qs}`;

  try {
    const backendRes = await fetch(target, {
      redirect: "manual",
      signal: AbortSignal.timeout(25_000),
    });

    const location = backendRes.headers.get("location");
    if (location) {
      return NextResponse.redirect(location, 307);
    }

    return new NextResponse(backendRes.body, {
      status: backendRes.status,
      headers: {
        "content-type":
          backendRes.headers.get("content-type") || "text/plain",
      },
    });
  } catch {
    const frontendBase = request.nextUrl.origin;
    return NextResponse.redirect(
      `${frontendBase}/settings?work_connected=error`,
      307,
    );
  }
}
