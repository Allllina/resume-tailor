// F4 Phase A — Layer 2 component tests for FitDiagnosisPostRewritePanel.
// This file is the test contract; Phase B implements
// `ui/src/components/fit-diagnosis/FitDiagnosisPostRewritePanel.tsx` to
// satisfy these assertions.
//
// Replaces the legacy DualReviewPanel (no component tests previously
// existed) and asserts on the NEW schema shape:
//   - top-level wrapper now follows fit_diagnosis_post_rewrite contract
//     in contracts/schemas/harness-tailor-output.schema.json
//   - radar.dimensions[*].citation is a NEW per-dim caption that must
//     surface on each axis (the F4 addition)
//   - improvement_suggestions still carries effort tags (wording /
//     supplement_project / long_term)
//
// GitBook design vocabulary asserted where load-bearing. Cosmetic
// styling (exact spacing, color shades) is intentionally NOT pinned —
// Phase B has freedom on the visual surface so long as the user-
// observable structure below holds.
//
// See docs/TESTING.md for the 3-layer pyramid + 10 quality rules +
// two-phase TDD pattern.
import { describe, expect, it } from "vitest";
import { render as rtlRender, screen, within } from "@testing-library/react";
import type { ReactElement } from "react";

import { FitDiagnosisPostRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPostRewritePanel";
import { LangProvider } from "@/lib/lang-context";

import {
  makePostRewriteDiagnosis,
  MOCK_POST_REWRITE,
} from "@/components/fit-diagnosis/__tests__/__fixtures__/diagnosis-post.fixture";

function render(ui: ReactElement) {
  return rtlRender(<LangProvider value="zh">{ui}</LangProvider>);
}

describe("FitDiagnosisPostRewritePanel", () => {
  // ─────────── 1. Graceful absence ───────────
  it("renders nothing when diagnosis is undefined", () => {
    const { container } = render(
      <FitDiagnosisPostRewritePanel diagnosis={undefined} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  // ─────────── 2. HM card content ───────────
  it("renders HM card with highlights / concerns / comparison_risk", () => {
    const highlightSentinel = "PHASE_A_HM_HIGHLIGHT_token";
    const concernSentinel = "PHASE_A_HM_CONCERN_token";
    const riskSentinel = "PHASE_A_HM_COMPARISON_RISK_token";
    const diag = makePostRewriteDiagnosis({
      hm: {
        highlights: [highlightSentinel, "另一个亮点"],
        concerns: [concernSentinel],
        comparison_risk: riskSentinel,
      },
    });
    render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
    expect(screen.getByText(highlightSentinel)).toBeInTheDocument();
    expect(screen.getByText("另一个亮点")).toBeInTheDocument();
    expect(screen.getByText(concernSentinel)).toBeInTheDocument();
    expect(screen.getByText(riskSentinel)).toBeInTheDocument();
  });

  // ─────────── 3. HRBP keyword_hit_rate as % ───────────
  it("renders HRBP keyword_hit_rate as a percentage (0.74 → 74%)", () => {
    const diag = makePostRewriteDiagnosis({
      hrbp: {
        keyword_hit_rate: 0.74,
        hard_filter_match: { 学历: "match" },
        advance_decision: "push_direct",
        decision_rationale: "rationale",
      },
    });
    render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
    // "74%" must appear at least once. Use a flexible regex so Phase B
    // can choose to render it as "74%" or "74 %" or wrapped in tabular
    // numerals; whitespace tolerance kept loose on purpose.
    expect(screen.getByText(/74\s*%/)).toBeInTheDocument();
  });

  // ─────────── 4. hard_filter_match pills ───────────
  it("renders one pill per hard_filter_match entry with the expected labels", () => {
    const diag = makePostRewriteDiagnosis({
      hrbp: {
        keyword_hit_rate: 0.5,
        hard_filter_match: {
          PHASE_A_FILTER_KEY_match: "match",
          PHASE_A_FILTER_KEY_uncertain: "uncertain",
          PHASE_A_FILTER_KEY_mismatch: "mismatch",
        },
        advance_decision: "push_direct",
        decision_rationale: "rationale",
      },
    });
    render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
    expect(screen.getByText(/PHASE_A_FILTER_KEY_match/)).toBeInTheDocument();
    expect(screen.getByText(/PHASE_A_FILTER_KEY_uncertain/)).toBeInTheDocument();
    expect(screen.getByText(/PHASE_A_FILTER_KEY_mismatch/)).toBeInTheDocument();
    // Status label vocabulary — at least one of each expected zh label.
    expect(screen.getAllByText("符合").length).toBeGreaterThan(0);
    expect(screen.getAllByText("待定").length).toBeGreaterThan(0);
    expect(screen.getAllByText("不符").length).toBeGreaterThan(0);
  });

  // ─────────── 5. advance_decision pill ───────────
  it.each([
    ["push_direct", "直接推进"],
    ["push_with_note", "附注推进"],
    ["screen_out", "筛除"],
  ] as const)(
    "renders advance_decision pill label '%s' → '%s'",
    (decision, label) => {
      const diag = makePostRewriteDiagnosis({
        hrbp: {
          keyword_hit_rate: 0.6,
          hard_filter_match: {},
          advance_decision: decision,
          decision_rationale: "rationale",
        },
      });
      render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    },
  );

  // ─────────── 6. 6-axis radar SVG ───────────
  it("renders a 6-axis radar SVG with all dimension names visible as labels", () => {
    const diag = makePostRewriteDiagnosis();
    const { container } = render(
      <FitDiagnosisPostRewritePanel diagnosis={diag} />,
    );
    // Pin: at least one <svg> exists in the tree.
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    // Each dimension name must be readable somewhere in the panel
    // (axis label, citation block, or sr-only fallback — Phase B picks).
    for (const dim of diag.radar.dimensions) {
      expect(screen.getAllByText(dim.name).length).toBeGreaterThan(0);
    }
    // Pin: exactly 6 dimensions (schema enforces this; UI must not drop any).
    expect(diag.radar.dimensions).toHaveLength(6);
  });

  // ─────────── 7. radar dimension citations (NEW in F4) ───────────
  it("renders the per-dimension citation as visible caption", () => {
    const citationSentinels = [
      "PHASE_A_CITATION_axis_one",
      "PHASE_A_CITATION_axis_two",
      "PHASE_A_CITATION_axis_three",
      "PHASE_A_CITATION_axis_four",
      "PHASE_A_CITATION_axis_five",
      "PHASE_A_CITATION_axis_six",
    ];
    const diag = makePostRewriteDiagnosis({
      radar: {
        dimensions: citationSentinels.map((cite, i) => ({
          name: `Dim ${i + 1}`,
          resume_score: 70,
          jd_required: 80,
          citation: cite,
        })),
      },
    });
    render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
    // Every citation must be findable somewhere in the rendered tree.
    // Phase B may surface them inline next to each axis label, in a
    // sub-list below the radar, or via a tooltip whose text is in the
    // accessible name. Either way they must be in the DOM as text.
    for (const cite of citationSentinels) {
      expect(screen.getByText(cite)).toBeInTheDocument();
    }
  });

  // ─────────── 8. improvement_suggestions list ───────────
  it("renders one entry per improvement_suggestion with effort label", () => {
    const diag = makePostRewriteDiagnosis({
      improvement_suggestions: [
        { text: "PHASE_A_SUGGESTION_one", effort: "wording" },
        { text: "PHASE_A_SUGGESTION_two", effort: "supplement_project" },
        { text: "PHASE_A_SUGGESTION_three", effort: "long_term" },
      ],
    });
    render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
    expect(screen.getByText("PHASE_A_SUGGESTION_one")).toBeInTheDocument();
    expect(screen.getByText("PHASE_A_SUGGESTION_two")).toBeInTheDocument();
    expect(screen.getByText("PHASE_A_SUGGESTION_three")).toBeInTheDocument();
    // Effort labels — current product vocabulary:
    // wording → 措辞调整, supplement_project → 补充项目, long_term → 长期规划.
    expect(screen.getAllByText("措辞调整").length).toBeGreaterThan(0);
    expect(screen.getAllByText("补充项目").length).toBeGreaterThan(0);
    expect(screen.getAllByText("长期规划").length).toBeGreaterThan(0);
  });

  // ─────────── 9. Suggestion cap (≤5) ───────────
  it("caps improvement_suggestions at 5 even if more are passed", () => {
    // The schema declares maxItems: 5 for improvement_suggestions, but
    // the UI must enforce this defensively — partial / fallback paths
    // could ship more. Assert that only the first 5 sentinels render.
    const diag = makePostRewriteDiagnosis({
      improvement_suggestions: [
        { text: "PHASE_A_CAP_one", effort: "wording" },
        { text: "PHASE_A_CAP_two", effort: "wording" },
        { text: "PHASE_A_CAP_three", effort: "wording" },
        { text: "PHASE_A_CAP_four", effort: "wording" },
        { text: "PHASE_A_CAP_five", effort: "wording" },
        { text: "PHASE_A_CAP_six_should_NOT_render", effort: "wording" },
        { text: "PHASE_A_CAP_seven_should_NOT_render", effort: "wording" },
      ],
    });
    render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
    expect(screen.getByText("PHASE_A_CAP_one")).toBeInTheDocument();
    expect(screen.getByText("PHASE_A_CAP_five")).toBeInTheDocument();
    expect(
      screen.queryByText("PHASE_A_CAP_six_should_NOT_render"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("PHASE_A_CAP_seven_should_NOT_render"),
    ).not.toBeInTheDocument();
  });

  // ─────────── 10. competitiveness_rating chip ───────────
  it.each([
    ["high", "高"],
    ["above_mid", "中偏高"],
    ["mid", "中"],
    ["below_mid", "中偏低"],
    ["low", "低"],
  ] as const)(
    "renders competitiveness_rating chip label '%s' → '%s'",
    (rating, label) => {
      const diag = makePostRewriteDiagnosis({ competitiveness_rating: rating });
      render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    },
  );

  // ─────────── 11. MethodBadge non-llm ───────────
  it("renders MethodBadge text for _method='fallback_no_llm'", () => {
    const diag = makePostRewriteDiagnosis({ _method: "fallback_no_llm" });
    render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
    expect(screen.getByText(/Inferred \(fallback\)/i)).toBeInTheDocument();
  });

  it("does NOT render MethodBadge text for _method='llm' (happy path)", () => {
    const diag = makePostRewriteDiagnosis({ _method: "llm" });
    render(<FitDiagnosisPostRewritePanel diagnosis={diag} />);
    expect(screen.queryByText(/Inferred \(partial\)/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Inferred \(fallback\)/i)).not.toBeInTheDocument();
  });

  // ─────────── 12. No deprecated names leak ───────────
  it("does NOT render deprecated 'DualReview' or 'dual_review' substrings anywhere", () => {
    const { container } = render(
      <FitDiagnosisPostRewritePanel diagnosis={MOCK_POST_REWRITE} />,
    );
    const rendered = container.textContent ?? "";
    expect(rendered).not.toMatch(/dual_review/i);
    expect(rendered).not.toMatch(/DualReview/);
  });

  // ─────────── 13. Smoke render against full mock ───────────
  it("renders against MOCK_POST_REWRITE without throwing", () => {
    // Belt-and-suspenders: confirms the realistic Anker / AIGC narrative
    // doesn't crash the panel (catches schema-shape regressions early).
    const { container } = render(
      <FitDiagnosisPostRewritePanel diagnosis={MOCK_POST_REWRITE} />,
    );
    expect(container.firstChild).not.toBeNull();
    // Spot-check a dimension name from the realistic mock.
    const radarDim = MOCK_POST_REWRITE.radar.dimensions[0];
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(within(container as HTMLElement).getAllByText(radarDim.name).length).toBeGreaterThan(0);
  });
});
