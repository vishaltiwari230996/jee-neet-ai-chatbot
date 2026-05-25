/**
 * Next.js configuration.
 *
 * We keep this minimal — the only non-default we need is server-side
 * rewrites to proxy `/api/*` to the FastAPI process. That avoids CORS
 * configuration entirely in dev, and gives us one URL surface
 * (`http://localhost:3000`) for everything during the demo.
 */
const API_ORIGIN = process.env.NEETAI_API_ORIGIN || "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  typedRoutes: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_ORIGIN}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
