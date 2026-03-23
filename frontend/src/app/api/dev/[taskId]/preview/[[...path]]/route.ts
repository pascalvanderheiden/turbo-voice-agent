import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string; path?: string[] }> }
) {
  const { taskId, path } = await params;
  const trailing = path ? path.join("/") : "";
  const search = request.nextUrl.search || "";
  const target = `${API_URL}/api/dev/${taskId}/preview/${trailing}${search}`;

  try {
    const fwdHeaders: Record<string, string> = {
      accept: request.headers.get("accept") || "*/*",
    };
    const auth = request.headers.get("authorization");
    if (auth) fwdHeaders["authorization"] = auth;

    const resp = await fetch(target, { headers: fwdHeaders });
    const body = await resp.arrayBuffer();
    const headers = new Headers();
    for (const key of ["content-type", "cache-control", "etag"]) {
      const val = resp.headers.get(key);
      if (val) headers.set(key, val);
    }
    return new NextResponse(body, { status: resp.status, headers });
  } catch {
    return NextResponse.json(
      { error: "Dev server not reachable — try again in a few seconds." },
      { status: 502 }
    );
  }
}
