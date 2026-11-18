/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The app calls /api/... on its own origin; in development Vite forwards
    // it as is to FastAPI, which serves the API under /api (same path as in
    // production), so the backend needs no CORS configuration.
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    // jsdom + Node's AbortController (see the file for why).
    environment: "./src/test/jsdom-environment.ts",
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
    // `pnpm test:coverage`: the equivalent of pytest-cov.
    coverage: {
      provider: "v8",
      // Every source file, so that code no test touches shows at 0 %.
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/api/schema.d.ts", // generated
        "src/test/**",
        "src/**/*.test.{ts,tsx}",
        "src/main.tsx", // startup only
        "src/vite-env.d.ts",
      ],
      // A table in the terminal, and coverage/index.html to see the lines.
      reporter: ["text", "html"],
      // `pnpm test:coverage` fails below 95 % (`pnpm test` does not measure).
      thresholds: { lines: 95, statements: 95, functions: 95, branches: 95 },
    },
  },
});
