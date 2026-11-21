import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom", // a simulated browser page, so components can render in tests
    setupFiles: ["./src/test-setup.ts"],
  },
});
