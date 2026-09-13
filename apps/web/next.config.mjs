/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
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
