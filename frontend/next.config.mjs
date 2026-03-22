/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        // Proxy live preview requests through the frontend domain
        source: "/api/dev/:taskId/preview/:path*",
        destination: `${backendUrl}/api/dev/:taskId/preview/:path*`,
      },
    ];
  },
};

export default nextConfig;
