/** @type {import('next').NextConfig} */
const clerkPublishableKey =
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ??
  process.env.CLERK_PUBLISHABLE_KEY ??
  "";

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
  },
  // Keep FastAPI private to the VM. Next's external rewrite forwards the
  // original request (including its body and headers) and streams the
  // upstream response, so uploads and Tutor SSE do not need a second public
  // origin.
  async rewrites() {
    const apiOrigin = (process.env.API_INTERNAL_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
