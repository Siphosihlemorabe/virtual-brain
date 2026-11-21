import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Builds the extension into dist/: load that folder in chrome://extensions ("Load unpacked").
// public/manifest.json is copied as is. Two entry points: the side panel page and the background worker.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      input: { sidepanel: "sidepanel.html", background: "src/background.ts" },
      output: {
        // The manifest names "background.js", so that file must keep a fixed name.
        entryFileNames: (chunk) => (chunk.name === "background" ? "background.js" : "assets/[name]-[hash].js"),
      },
    },
  },
  test: { environment: "node" },
});
