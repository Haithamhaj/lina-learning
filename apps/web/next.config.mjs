/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
