/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emit a self-contained server bundle (.next/standalone) for a small Docker
  // runtime image — only the traced deps ship, not all of node_modules.
  output: "standalone",
  async rewrites() {
    // Proxy API calls to the FastAPI backend. BACKEND_URL is read when the
    // rewrite map is built, so Docker bakes it via a build arg.
    const backend = process.env.BACKEND_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
