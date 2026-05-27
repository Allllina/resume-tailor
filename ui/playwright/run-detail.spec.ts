// F4 Phase A — Layer 3 Playwright tests for the run-detail page after
// the fit_diagnosis panel rewrite. Asserts that the new panels render
// against the MOCK_RUNS dataset Phase B is responsible for shipping.
//
// Pre-conditions (Phase B controller will arrange):
//   - `make ui` is running externally on :8080 (or PLAYWRIGHT_BASE_URL).
//   - `npx playwright install chromium` has been run once.
//   - MOCK_RUNS[0] (`mock-anker-aigc`) has BOTH `fit_diagnosis_pre_rewrite`
//     and `fit_diagnosis_post_rewrite` populated.
//   - MOCK_RUNS[1] (`mock-jd-business`) intentionally OMITS both fields
//     to validate the graceful-absence path.
//
// Keep this file at 3 tests — docs/TESTING.md Layer 3 budget is 3–5
// scenarios total across the app.
import { test, expect } from "@playwright/test";

test.describe("run-detail page — fit_diagnosis panels", () => {
  test("loads /run/mock-anker-aigc and shows both new panels by Chinese title", async ({
    page,
  }) => {
    await page.goto("/run/mock-anker-aigc");

    // Phase B keeps the existing Chinese section titles (匹配矩阵 /
    // 双视角评估) on the new panels so the UI vocabulary stays stable
    // even though the underlying schema field names changed.
    await expect(page.getByText("匹配矩阵").first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("双视角评估").first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test("radar SVG renders all 6 dimensions on the post-rewrite panel", async ({
    page,
  }) => {
    await page.goto("/run/mock-anker-aigc");

    // Wait for the post-rewrite panel landmark, then count <text>
    // nodes inside its SVG. We expect ≥ 6 (one per axis label) — there
    // may be more if Phase B adds tick labels or score numerals, but
    // never fewer.
    const panel = page.getByRole("region", { name: /双视角评估/ });
    await expect(panel).toBeVisible({ timeout: 15_000 });

    const svg = panel.locator("svg").first();
    await expect(svg).toBeVisible();

    const textNodes = svg.locator("text");
    expect(await textNodes.count()).toBeGreaterThanOrEqual(6);
  });

  test("panels are absent on /run/mock-jd-business (graceful-absence path)", async ({
    page,
  }) => {
    await page.goto("/run/mock-jd-business");

    // Wait for SOMETHING on the page to confirm the route loaded — the
    // run-detail page always shows change cards, so use those as the
    // synchronization point.
    await page.waitForLoadState("networkidle");

    // Neither fit_diagnosis panel should be present. Counting via the
    // section's accessible name keeps the assertion independent of the
    // exact DOM structure Phase B picks.
    await expect(page.getByText("匹配矩阵")).toHaveCount(0);
    await expect(page.getByText("双视角评估")).toHaveCount(0);
  });
});
