import path from "node:path";
import type { NextConfig } from "next";

const repoRoot = path.join(__dirname, "..");

const nextConfig: NextConfig = {
  // transpilePackages natively handles linking the external monorepo folder!
  transpilePackages: ["@cuvoy/contracts", "mapbox-gl"],
  outputFileTracingRoot: repoRoot,
};

export default nextConfig;