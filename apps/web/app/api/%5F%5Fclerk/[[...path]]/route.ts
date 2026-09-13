import type { NextRequest } from "next/server";

const CLERK_FRONTEND_API = "https://frontend-api.clerk.dev";
const CLERK_PROXY_PATH = "/api/__clerk";
const BODYLESS_STATUSES = new Set([204, 304]);

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function publicHost(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-host");
  return forwarded?.split(",")[0]?.trim() || request.headers.get("host") || "";
}

async function proxyClerk(request: NextRequest): Promise<Response> {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) {
    return new Response("Clerk proxy is unavailable.", { status: 503 });
  }

  const incomingUrl = new URL(request.url);
  const upstreamPath = incomingUrl.pathname.slice(CLERK_PROXY_PATH.length) || "/";
  const upstreamUrl = new URL(`${upstreamPath}${incomingUrl.search}`, CLERK_FRONTEND_API);
  const headers = new Headers(request.headers);
  const protocol = request.headers.get("x-forwarded-proto") || "https";
  const host = publicHost(request);

  headers.delete("host");
  headers.delete("content-length");
  headers.delete("connection");
  headers.set("accept-encoding", "identity");
  headers.set("Clerk-Proxy-Url", `${protocol}://${host}${CLERK_PROXY_PATH}`);
  headers.set("Clerk-Secret-Key", secretKey);

  const upstream = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body:
      request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer(),
    redirect: "manual",
  });

  const responseHeaders = new Headers(upstream.headers);
  responseHeaders.delete("connection");
  responseHeaders.delete("keep-alive");
  responseHeaders.delete("transfer-encoding");
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");

  const bodyless =
    request.method === "HEAD" ||
    upstream.status < 200 ||
    BODYLESS_STATUSES.has(upstream.status);
  const body = bodyless ? null : await upstream.arrayBuffer();
  if (body) {
    responseHeaders.set("content-length", String(body.byteLength));
  }

  return new Response(body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = proxyClerk;
export const POST = proxyClerk;
export const PUT = proxyClerk;
export const PATCH = proxyClerk;
export const DELETE = proxyClerk;
export const OPTIONS = proxyClerk;
export const HEAD = proxyClerk;