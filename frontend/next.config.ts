import path from "node:path";
import type { NextConfig } from "next";

const repoRoot = path.join(__dirname, "..");
const contractsEntry = path.join(
  repoRoot,
  "packages",
  "contracts",
  "typescript",
  "src",
  "index.ts",
);

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
      "@cuvoy/contracts": contractsEntry,
    };
    return config;
  },
};

export default nextConfig;
