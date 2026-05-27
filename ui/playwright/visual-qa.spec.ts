// Visual QA walkthrough — captures full-page screenshots of every reachable
// route in the app so the controller can review UI state without a manual
// click-through. Two passes:
//
//   1. Static / mock-driven routes (always runnable):
//      /, /preview, /preview/fit-diagnosis-pre, /preview/fit-diagnosis-post,
//      /preview/run-sample, /run/mock-anker-aigc, /run/mock-jd-business
//
//   2. Real-backend routes (require harness on :8001 + at least one user
//      profile to exist — defaults to default which is seeded):
//      /resume, /experiences, /settings, /setup
//
// Screenshots are written to playwright/screenshots/<route-slug>.png and
// also attached to the HTML report. Each assertion is lenient (just
// confirms the route loaded) — this spec is a snapshot capture tool, not
// a content correctness check (those live in preview.spec.ts and
// run-detail.spec.ts).
//
// Run: `npx playwright test playwright/visual-qa.spec.ts --reporter=line`
// Review: `npx playwright show-report`
import { test, expect } from "@playwright/test";

const VIEWPORT = { width: 1440, height: 900 };

test.use({
  viewport: VIEWPORT,
  // Hardcoded to a known seeded user so /resume + /settings render real data.
  // The localStorage key matches ui/src/lib/user.ts:USER_ID_KEY. Without this,
  // each fresh Playwright context generates a new UUID and the backend sees
  // an empty profile for that user (404 / "No resume uploaded yet" state).
  // Override with PLAYWRIGHT_USER_ID env var if needed.
  storageState: {
    cookies: [],
    origins: [
      {
        origin: "http://127.0.0.1:8080",
        localStorage: [
          {
            name: "rt:user_id",
            value: process.env.PLAYWRIGHT_USER_ID ?? "default",
          },
        ],
      },
    ],
  },
});

interface VisualRoute {
  path: string;
  slug: string;
  // A selector that confirms the route actually loaded (not just rendered
  // the app shell). If absent, we just wait for networkidle.
  loadedWhen?: string;
  // Hard timeout for the loadedWhen check (some pages are slow on first
  // mount because they fetch real data). Default 10s.
  timeout?: number;
}

const STATIC_ROUTES: VisualRoute[] = [
  { path: "/", slug: "01-inbox", loadedWhen: "Inbox" },
  { path: "/preview", slug: "02-preview-index", loadedWhen: "Component Preview" },
  {
    path: "/preview/fit-diagnosis-pre",
    slug: "03-preview-fit-pre",
    loadedWhen: "匹配矩阵",
  },
  {
    path: "/preview/fit-diagnosis-post",
    slug: "04-preview-fit-post",
    loadedWhen: "双视角评估",
  },
  {
    path: "/preview/run-sample",
    slug: "05-preview-run-sample",
    loadedWhen: "匹配矩阵",
  },
  {
    path: "/run/mock-anker-aigc",
    slug: "06-run-mock-anker",
    loadedWhen: "匹配矩阵",
    timeout: 15_000,
  },
  {
    path: "/run/mock-jd-business",
    slug: "07-run-mock-business",
    timeout: 15_000,
  },
];

const REAL_BACKEND_ROUTES: VisualRoute[] = [
  { path: "/resume", slug: "08-resume", loadedWhen: "Resume" },
  { path: "/experiences", slug: "09-experiences", loadedWhen: "Experiences" },
  { path: "/settings", slug: "10-settings", loadedWhen: "Settings" },
  { path: "/setup", slug: "11-setup", loadedWhen: "Drop a JD" },
];

async function captureRoute(
  page: import("@playwright/test").Page,
  route: VisualRoute,
  testInfo: import("@playwright/test").TestInfo,
) {
  await page.goto(route.path);
  if (route.loadedWhen) {
    await expect(page.getByText(route.loadedWhen).first()).toBeVisible({
      timeout: route.timeout ?? 10_000,
    });
  } else {
    await page.waitForLoadState("networkidle", { timeout: route.timeout ?? 10_000 });
  }
  // Give layout/animations one settle frame before capture.
  await page.waitForTimeout(300);
  const buf = await page.screenshot({ fullPage: true });
  await testInfo.attach(`${route.slug}.png`, { body: buf, contentType: "image/png" });
}

test.describe("Visual QA walkthrough", () => {
  for (const route of STATIC_ROUTES) {
    test(`static: ${route.path}`, async ({ page }, testInfo) => {
      await captureRoute(page, route, testInfo);
    });
  }

  for (const route of REAL_BACKEND_ROUTES) {
    test(`backend: ${route.path}`, async ({ page }, testInfo) => {
      await captureRoute(page, route, testInfo);
    });
  }

  test("/resume shows Per-direction masters section (new in 98365d7)", async ({
    page,
  }) => {
    await page.goto("/resume");
    await expect(
      page.getByRole("heading", { name: "Per-direction masters" }),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("/setup Step 2 shows broad family labels (no A/B/C/D prefixes)", async ({
    page,
  }) => {
    await page.goto("/setup");
    // default has has_resume=true, so /setup auto-advances to Step 2.
    await expect(page.getByText("What kind of role")).toBeVisible({
      timeout: 10_000,
    });
    // The new labels (no letter prefix).
    await expect(page.getByText("Strategy & Research")).toBeVisible();
    await expect(page.getByText("Data & Analytics")).toBeVisible();
    // The v0.6 explainer note.
    await expect(page.getByText(/v0\.6 roadmap/i)).toBeVisible();
    // Critical: A/B/C/D letter prefixes must NOT appear in any visible label.
    await expect(page.getByText(/^A 战略研究$/)).toHaveCount(0);
    await expect(page.getByText(/^B 数据分析$/)).toHaveCount(0);
  });
});
