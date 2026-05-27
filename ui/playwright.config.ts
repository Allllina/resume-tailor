import { defineConfig, devices } from "@playwright/test";

// Playwright config — Layer 3 (E2E user flows).
// 3-5 tests max per docs/TESTING.md guidance — these are slow + flaky;
// don't replace unit/component coverage with E2E.
//
// Targets the Vite dev server on :8080. Backend on :8001 must be running
// separately if tests exercise real API calls (mock-mode tests don't need it).
//
// Run: `npm run test:e2e`
//
// Browsers must be installed once via `npx playwright install` after npm
// install — committed config does NOT auto-install browsers.
export default defineConfig({
  testDir: "./playwright",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "html",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:8080",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Don't auto-spawn a webServer — assume the user runs `make ui` (Vite on :8080)
  // and `make backend` (uvicorn on :8001) in separate terminals before testing.
  // CI can override via webServer config when needed.
});
