/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        // Proxy OAuth callbacks to the backend
        source: "/api/auth/callback/:path*",
        destination: `${backendUrl}/api/auth/callback/:path*`,
      },
    ];
  },
};

export default nextConfig;
