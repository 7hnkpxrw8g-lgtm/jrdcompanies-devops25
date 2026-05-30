/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Server-side proxy: browser calls same-origin /api/*, Next forwards to the
  // backend. API_PROXY_TARGET is resolved at runtime in the Next.js server
  // process (same container as the backend in docker-compose), so localhost
  // works there even though it wouldn't in the user's browser.
  async rewrites() {
    const target =
      process.env.API_PROXY_TARGET ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${target}/:path*`,
      },
    ];
  },
};

export default nextConfig;
