import type { NextConfig } from "next";

// Internal API target — resolved by Docker DNS inside the compose network.
// Default `http://api:8000` matches the service name in docker-compose.nas.yml.
const INTERNAL_API = process.env.INTERNAL_API_URL ?? "http://api:8000";

const nextConfig: NextConfig = {
  // Same-origin proxy: browser hits /api/* and /ws/*, Next.js forwards to
  // the API container internally. Works regardless of whether the user
  // loaded the dashboard from LAN IP or from the Cloudflare tunnel.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${INTERNAL_API}/:path*` },
      { source: "/ws/:path*", destination: `${INTERNAL_API}/ws/:path*` },
    ];
  },
};

export default nextConfig;
