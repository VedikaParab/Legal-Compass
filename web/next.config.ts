import type { NextConfig } from "next";

// Browser calls /api/* on the same origin; Next forwards them to the FastAPI orchestrator.
const BACKEND = process.env.BACKEND_URL || "http://localhost:8100";

const nextConfig: NextConfig = {
  output: "standalone",
  // the first analysis can take a while if the IL-TUR models are still loading
  experimental: { proxyTimeout: 180_000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND}/api/:path*` }];
  },
};
export default nextConfig;
