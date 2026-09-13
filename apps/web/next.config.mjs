/** @type {import('next').NextConfig} */
const clerkPublishableKey =
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ??
  process.env.CLERK_PUBLISHABLE_KEY ??
  "";
const rawClerkProxyUrl =
  process.env.NEXT_PUBLIC_CLERK_PROXY_URL ??
  process.env.CLERK_PROXY_URL ??
  "";

// Clerk's Next.js package eagerly resolves its conventional proxy variables
// while prerendering. Replit supplies a relative same-origin path, whose
// browser-only resolution touches window and breaks SSR. Preserve that path
// under Lina's public build variable, then prevent the SDK from auto-reading
// the relative value; Providers passes an absolute same-origin URL in-browser.
if (rawClerkProxyUrl.startsWith("/")) {
  delete process.env.NEXT_PUBLIC_CLERK_PROXY_URL;
  delete process.env.CLERK_PROXY_URL;
}

if (process.env.APP_ENV === "production" && !clerkPublishableKey) {
  throw new Error(
    "Production requires CLERK_PUBLISHABLE_KEY or NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.",
  );
}

const nextConfig = {
  reactStrictMode: true,
  env: {
    // Replit-managed Clerk provisions CLERK_PUBLISHABLE_KEY. Clerk's Next.js
    // client reads the conventional public name; publishable keys are intended
    // to be embedded in browser bundles.
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: clerkPublishableKey,
    // Replit supplies its managed Clerk proxy as a same-origin path in
    // production. Keep it relative here so a development hostname can never be
    // baked into the published client bundle.
    NEXT_PUBLIC_LINA_CLERK_PROXY_PATH: rawClerkProxyUrl,
  },
  // Keep FastAPI private to the VM. Next's external rewrite forwards the
  // original request (including its body and headers) and streams the
  // upstream response, so uploads and Tutor SSE do not need a second public
  // origin.
  async rewrites() {
    const apiOrigin = (process.env.API_INTERNAL_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

    return [
      {
        source: "/api/:path((?!__clerk(?:/|$)).*)",
        destination: `${apiOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
