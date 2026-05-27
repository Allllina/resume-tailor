/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";
import react from "@vitejs/plugin-react";

// Vitest config — Layer 1 (lib unit tests) + Layer 2 (component tests via RTL).
// Layer 3 (Playwright E2E) lives in playwright.config.ts.
//
// Inherits the same path-resolution + JSX transform the production Vite build
// uses (via tsconfig-paths + React plugin) so `@/` aliases and JSX work the
// same in tests as in `vite dev`.
//
// See docs/TESTING.md for the testing pyramid + 10 quality rules.
export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: {
    environment: "jsdom",
    environmentOptions: {
      jsdom: {
        // jsdom 29 requires a URL to enable Storage API (localStorage /
        // sessionStorage). Without this, `localStorage.clear is not a
        // function` errors in tests that touch storage.
        url: "http://localhost",
      },
    },
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", "dist", ".vinxi", "playwright"],
    // The repo path contains a space ("Side Project") AND vitest 4 +
    // Node 25 worker_threads / vm pool both fail with "Timeout waiting
    // for worker to respond" at 60s before any test loads (URL-encoded
    // path issue in vitest's worker IPC layer). Using `pool: "forks"`
    // with `singleFork: true` runs ALL tests in one subprocess —
    // bypasses the worker spawn entirely. Slowest but most reliable.
    pool: "forks",
    forks: { singleFork: true },
    isolate: false,
    coverage: {
      reporter: ["text", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/**/*.spec.{ts,tsx}",
        "src/test/**",
        "src/types/generated.ts",
        "src/router.tsx",
        "src/routeTree.gen.ts",
      ],
    },
  },
});
