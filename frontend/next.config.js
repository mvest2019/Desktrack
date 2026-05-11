/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://69.62.76.202:8000"}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
