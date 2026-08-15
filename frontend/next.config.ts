import path from "node:path";
import type { NextConfig } from "next";

const repoRoot = path.join(__dirname, "..");
/** Must stay relative. Turbopack treats "/vercel/..." as a server-relative import. */
const contractsEntry = "../packages/contracts/typescript/src/index.ts";

const nextConfig: NextConfig = {
  transpilePackages: ["@cuvoy/contracts", "mapbox-gl"],
  outputFileTracingRoot: repoRoot,
  turbopack: {
    resolveAlias: {
      "@cuvoy/contracts": contractsEntry,
    },
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "@cuvoy/contracts": path.join(__dirname, contractsEntry),
    };
    return config;
  },
};

export default nextConfig;