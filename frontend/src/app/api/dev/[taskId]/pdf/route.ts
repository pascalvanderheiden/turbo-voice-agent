import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  const { taskId } = await params;
  const target = `${API_URL}/api/dev/${taskId}/pdf`;

  try {
    const fwdHeaders: Record<string, string> = {};
    const auth = request.headers.get("authorization");
    if (auth) fwdHeaders["authorization"] = auth;

    const resp = await fetch(target, { headers: fwdHeaders });
    if (!resp.ok) {
      return NextResponse.json(
        { error: `Backend returned ${resp.status}` },
        { status: resp.status }
      );
    }

    const body = await resp.arrayBuffer();
    return new NextResponse(body, {
      status: 200,
      headers: {
        "content-type": "application/pdf",
        "content-disposition": resp.headers.get("content-disposition") || "inline",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Failed to fetch PDF" },
      { status: 502 }
    );
  }
}
