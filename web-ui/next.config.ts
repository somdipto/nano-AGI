import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  reactCompiler: true,
  // Allow xterm.js and other packages that use server-only APIs
  transpilePackages: ["@xterm/xterm", "@xterm/addon-fit", "@xterm/addon-web-links"],
};

export default nextConfig;
