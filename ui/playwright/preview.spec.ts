import { test, expect } from "@playwright/test";

// L5 — Playwright preview spec.
// Verifies that the /preview route family renders correctly against L3 fixtures.
// This catches integration regressions where a component breaks but unit tests pass.
//
// F4 wave (2026-05-11) replaced MatchMatrixPanel + DualReviewPanel with
// FitDiagnosisPreRewritePanel + FitDiagnosisPostRewritePanel. Routes
// renamed accordingly: preview/match-matrix → preview/fit-diagnosis-pre,
// preview/dual-review → preview/fit-diagnosis-post.

test.describe("Preview Routes", () => {
  test("/preview index loads + shows 3 navigation cards", async ({ page }) => {
    await page.goto("/preview");
    await expect(
      page.getByRole("heading", { name: "Component Preview" }),
    ).toBeVisible();

    await expect(page.getByText("Fit Diagnosis — Pre-rewrite")).toBeVisible();
    await expect(page.getByText("Fit Diagnosis — Post-rewrite")).toBeVisible();
    await expect(page.getByText("Run sample (composed)")).toBeVisible();
  });

  test("/preview/fit-diagnosis-pre renders the panel with matching matrix rows", async ({
    page,
  }) => {
    await page.goto("/preview/fit-diagnosis-pre");

    await expect(page.getByRole("heading", { name: "匹配矩阵" })).toBeVisible();

    // diagnoses-multi.json[0] has at least 6 matching_matrix items.
    // Verdict pills (强匹配 / 可包装 / 缺失) should be visible.
    await expect(page.getByText(/强匹配|可包装|缺失/).first()).toBeVisible();
  });

  test("/preview/fit-diagnosis-post renders the panel with 6-axis radar", async ({
    page,
  }) => {
    await page.goto("/preview/fit-diagnosis-post");

    await expect(page.getByRole("heading", { name: "双视角评估" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "招聘经理" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "人力资源" })).toBeVisible();

    // Radar section should be present (rendered as <section aria-label="6 维能力雷达">)
    await expect(page.getByRole("region", { name: /雷达|radar/i })).toBeVisible();
  });

  test("/preview/run-sample renders both panels stacked", async ({ page }) => {
    await page.goto("/preview/run-sample");
    await expect(page.getByRole("heading", { name: "匹配矩阵" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "双视角评估" })).toBeVisible();
  });
});
