import { readFileSync } from "node:fs";
import { defineConfig } from "vitest/config";

const { version } = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8"));

// One self-contained ES module, committed so HACS users need no Node.
export default defineConfig({
  define: { __CARD_VERSION__: JSON.stringify(version) },
  build: {
    lib: {
      entry: "src/card.ts",
      formats: ["es"],
      fileName: () => "jellyseerr-search-card.js",
    },
    outDir: "../custom_components/jellyseerr_search/frontend",
    emptyOutDir: true,
    target: "es2021",
    minify: true,
    sourcemap: false,
  },
  test: { environment: "node" },
});
