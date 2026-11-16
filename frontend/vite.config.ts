/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The app calls /api/...; in development Vite forwards it to FastAPI
    // without the /api prefix, so the backend needs no CORS configuration.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    // jsdom + Node's AbortController (see the file for why).
    environment: "./src/test/jsdom-environment.ts",
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
  },
});
