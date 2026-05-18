import type { NextConfig } from "next";

// H-04: Content-Security-Policy — prevents XSS attacks
// 'unsafe-inline' for styles is required by Next.js/Tailwind CSS
// supabase.co is allowed for supabase auth flows
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-eval' 'unsafe-inline'",  // unsafe-inline and unsafe-eval required by Next.js dev mode
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data: blob: https:",
  "connect-src 'self' https://*.supabase.co wss://*.supabase.co http://localhost:8082 http://localhost:3080",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const securityHeaders = [
  { key: "X-DNS-Prefetch-Control", value: "on" },
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
  // H-04: CSP header added
  {
    key: "Content-Security-Policy",
    value: CSP,
  },
];

const nextConfig: NextConfig = {
  // P10 audit: shave bytes + drop the X-Powered-By: Next.js fingerprint.
  compress: true,
  poweredByHeader: false,
  // Silence Turbopack workspace-root warning when running from a git worktree
  // that shares a parent with the main checkout (both have package-lock.json).
  turbopack: {
    root: __dirname,
  },
  // Required for Docker standalone build
  output: process.env.DOCKER_BUILD === "1" ? "standalone" : undefined,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
