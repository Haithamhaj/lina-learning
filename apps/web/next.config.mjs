/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    // Tutor SSE is intentionally buffered until terminal validation; keep the
    // internal API proxy alive beyond Next's 30s default while Luna completes.
    proxyTimeout: 120_000,
  },
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
