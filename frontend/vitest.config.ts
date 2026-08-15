import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/tests/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@cuvoy/contracts": path.resolve(__dirname, "../packages/contracts/typescript/src/index.ts"),
    },
  },
});
