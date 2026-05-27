// F4 Phase A — Layer 2 component tests for the RadarChart copy/move
// from `ui/src/components/dual-review/RadarChart.tsx` into
// `ui/src/components/fit-diagnosis/RadarChart.tsx`. The hand-rolled
// SVG implementation stays; what changes is that each Dimension now
// carries a `citation` field (per fit_diagnosis_post_rewrite schema).
//
// The chart itself need NOT render the citation visually (that's the
// PostRewritePanel's job), but it MUST accept the shape without
// type-erroring or losing the dimension.
//
// See docs/TESTING.md — Layer 2 component pyramid.
import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";

import { RadarChart } from "@/components/fit-diagnosis/RadarChart";

type Dim = {
  name: string;
  resume_score: number;
  jd_required: number;
  citation: string;
};

function makeDimension(overrides: Partial<Dim> = {}): Dim {
  return {
    name: "AI 工具",
    resume_score: 80,
    jd_required: 70,
    citation: "default citation",
    ...overrides,
  };
}

function makeSixDimensions(): Dim[] {
  const names = [
    "AI 工具",
    "内容生产",
    "产品运营",
    "数据分析",
    "行业经验",
    "沟通协作",
  ];
  return names.map((name, i) =>
    makeDimension({
      name,
      resume_score: 50 + i * 5,
      jd_required: 60 + i * 4,
      citation: `citation for ${name}`,
    }),
  );
}

describe("RadarChart", () => {
  // ─────────── 1. 6 axis labels ───────────
  it("renders all 6 dimension names as <text> labels inside the SVG", () => {
    const dims = makeSixDimensions();
    const { container } = render(<RadarChart dimensions={dims} />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    // Each name must appear as a <text> node in the SVG (axis label).
    for (const d of dims) {
      const matches = Array.from(svg!.querySelectorAll("text")).filter((el) =>
        (el.textContent ?? "").includes(d.name),
      );
      expect(matches.length).toBeGreaterThan(0);
    }
  });

  // ─────────── 2. Reference rings ───────────
  it("renders concentric reference rings (3 or 4 of them)", () => {
    // Original implementation renders 4 rings at 25/50/75/100 fractions,
    // implemented as <polygon> elements (one per ring). Phase B may keep
    // 4 or compress to 3; either count is acceptable for the visual scan
    // pattern. Anything outside {3, 4} would change the reading.
    const dims = makeSixDimensions();
    const { container } = render(<RadarChart dimensions={dims} />);
    const svg = container.querySelector("svg")!;
    const polygons = svg.querySelectorAll("polygon");
    // Each ring is a polygon; each data series (resume + jd_required)
    // is also a polygon. So total polygons = rings + 2.
    // Accept either 3 + 2 = 5 or 4 + 2 = 6.
    expect([5, 6]).toContain(polygons.length);
  });

  // ─────────── 3. Two data polygons (resume + jd_required) ───────────
  it("renders resume_score and jd_required as separate polygons", () => {
    const dims = makeSixDimensions();
    const { container } = render(<RadarChart dimensions={dims} />);
    const svg = container.querySelector("svg")!;
    const polygons = svg.querySelectorAll("polygon");
    // At least 2 polygons must exist (the rings on top of the data
    // layers). Beyond that, see test #2 for ring-count assertion.
    expect(polygons.length).toBeGreaterThanOrEqual(2);

    // The two data polygons must have DIFFERENT `points` attributes
    // (resume scores ≠ jd_required scores in our fixture, so the
    // polygons must trace different paths).
    const pointStrings = Array.from(polygons).map((p) =>
      p.getAttribute("points") ?? "",
    );
    const uniquePoints = new Set(pointStrings);
    // Rings share their point set per ring; data polygons should be
    // unique. Either way, the number of distinct point sets must be
    // ≥ 2 (the two data polygons differ).
    expect(uniquePoints.size).toBeGreaterThanOrEqual(2);
  });

  // ─────────── 4. Pads / handles fewer than 6 ───────────
  it("renders gracefully when given fewer than 6 dimensions (no throw)", () => {
    // Schema enforces exactly 6 in production, but the component
    // historically rendered defensively (see legacy
    // ui/src/components/dual-review/RadarChart.tsx — `length === 0`
    // shows a stub, otherwise just renders what it gets). Phase B can
    // either render exactly what's passed (current behavior) or pad
    // to 6 — both are acceptable; the assertion below pins only that
    // the chart does not crash and the user-visible names render.
    const partial = makeSixDimensions().slice(0, 4); // 4 dims
    const { container } = render(<RadarChart dimensions={partial} />);
    expect(container.firstChild).not.toBeNull();
    for (const d of partial) {
      expect(container.textContent ?? "").toContain(d.name);
    }
  });

  // ─────────── 5. Truncates / handles more than 6 ───────────
  it("renders gracefully when given more than 6 dimensions (no throw)", () => {
    // Same defensive contract as test #4 — the chart must not crash if
    // the backend ships an unexpectedly long radar. Phase B may
    // truncate to 6 (recommended) or render all; either is acceptable
    // so long as the first 6 names still appear and the SVG renders.
    const dims = makeSixDimensions();
    const extras: Dim[] = [
      ...dims,
      makeDimension({ name: "Extra-7" }),
      makeDimension({ name: "Extra-8" }),
    ];
    const { container } = render(<RadarChart dimensions={extras} />);
    expect(container.firstChild).not.toBeNull();
    for (const d of dims) {
      expect(container.textContent ?? "").toContain(d.name);
    }
  });

  // ─────────── 6. Accessibility ───────────
  it("exposes role=img and an aria-label describing the chart", () => {
    const dims = makeSixDimensions();
    const { container } = render(<RadarChart dimensions={dims} />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg!.getAttribute("role")).toBe("img");
    const ariaLabel = svg!.getAttribute("aria-label");
    expect(ariaLabel).toBeTruthy();
    expect(ariaLabel!.length).toBeGreaterThan(0);
  });
});
