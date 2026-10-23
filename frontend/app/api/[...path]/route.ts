import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5000";
  const path = params.path.join("/");
  const search = request.nextUrl.search;
  const targetUrl = `${backendUrl}/api/${path}${search}`;

  try {
    const res = await fetch(targetUrl, {
      cache: "no-store",
    });

    // Pass through status and headers (e.g. text/event-stream, application/pdf, etc.)
    const responseHeaders = new Headers();
    res.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    return new NextResponse(res.body, {
      status: res.status,
      headers: responseHeaders,
    });
  } catch (err: any) {
    console.error(`[API Proxy GET Error] Failed to reach ${targetUrl}:`, err.message);
    return NextResponse.json(
      { success: false, message: `Proxy error: ${err.message}` },
      { status: 502 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const backendUrl = process.env.BACKEND_URL || "http://127.0.0.1:5000";
  const path = params.path.join("/");
  const targetUrl = `${backendUrl}/api/${path}`;

  try {
    const body = await request.text();
    const res = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });

    const responseHeaders = new Headers();
    res.headers.forEach((value, key) => {
      responseHeaders.set(key, value);
    });

    return new NextResponse(res.body, {
      status: res.status,
      headers: responseHeaders,
    });
  } catch (err: any) {
    console.error(`[API Proxy POST Error] Failed to reach ${targetUrl}:`, err.message);
    return NextResponse.json(
      { success: false, message: `Proxy error: ${err.message}` },
      { status: 502 }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type,Authorization",
    },
  });
}
