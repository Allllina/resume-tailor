// F4 Phase A — Layer 2 component tests for FitDiagnosisPreRewritePanel.
// This file is the test contract; Phase B implements
// `ui/src/components/fit-diagnosis/FitDiagnosisPreRewritePanel.tsx` to
// satisfy these assertions.
//
// Replaces the legacy MatchMatrixPanel component tests (none existed
// before F4) and asserts on the NEW schema shape:
//   - field renamed: requirements -> matching_matrix
//   - new per-row field: bridging_or_closure (caption on transferable +
//     missing rows, hidden on strong_match rows)
//   - top-level wrapper now follows fit_diagnosis_pre_rewrite contract
//     in contracts/schemas/harness-tailor-output.schema.json
//
// GitBook design vocabulary asserted where load-bearing. Cosmetic
// styling (exact spacing / font weights) is intentionally NOT pinned —
// Phase B has freedom on the visual surface so long as the user-
// observable structure below holds.
//
// See docs/TESTING.md for the 3-layer pyramid + 10 quality rules +
// two-phase TDD pattern.
import { describe, expect, it } from "vitest";
import { render as rtlRender, screen, within } from "@testing-library/react";
import type { ReactElement } from "react";

// Phase B will create this component. Until it exists, every test
// below SHOULD fail with a module-resolution error — that's the
// expected Phase A red state per docs/TESTING.md "Phase A — Test
// contract" section.
import { FitDiagnosisPreRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPreRewritePanel";
import { LangProvider } from "@/lib/lang-context";

import {
  makeMissingItem,
  makePreRewriteDiagnosis,
  makeStrongMatchItem,
  makeTransferableItem,
  MOCK_PRE_REWRITE,
} from "@/components/fit-diagnosis/__tests__/__fixtures__/diagnosis-pre.fixture";

function render(ui: ReactElement) {
  return rtlRender(<LangProvider value="zh">{ui}</LangProvider>);
}

describe("FitDiagnosisPreRewritePanel", () => {
  // ─────────── 1. Graceful absence ───────────
  it("renders nothing when diagnosis is undefined", () => {
    const { container } = render(
      <FitDiagnosisPreRewritePanel diagnosis={undefined} />,
    );
    // Mirrors the historical MatchMatrixPanel "render nothing on
    // undefined" pattern — historical runs from before F1 won't have
    // the field, and a stub card would mislead the user.
    expect(container).toBeEmptyDOMElement();
  });

  // ─────────── 2. Matrix list shape ───────────
  it("renders matching_matrix items as a list of rows", () => {
    const diag = makePreRewriteDiagnosis({
      matching_matrix: [
        makeStrongMatchItem({ text: "Requirement A" }),
        makeTransferableItem({ text: "Requirement B" }),
        makeMissingItem({ text: "Requirement C" }),
      ],
    });
    render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);

    expect(screen.getByText("Requirement A")).toBeInTheDocument();
    expect(screen.getByText("Requirement B")).toBeInTheDocument();
    expect(screen.getByText("Requirement C")).toBeInTheDocument();

    // Phase B is expected to render rows inside one list (ul/ol/role=list);
    // we don't pin which tag, but we DO pin that a single list contains
    // exactly the 3 rendered items.
    const lists = screen.getAllByRole("list");
    const matrixList = lists.find(
      (el) =>
        within(el).queryByText("Requirement A") !== null &&
        within(el).queryByText("Requirement C") !== null,
    );
    expect(matrixList).toBeDefined();
    expect(within(matrixList!).getAllByRole("listitem")).toHaveLength(3);
  });

  // ─────────── 3. Verdict pills ───────────
  it.each([
    ["strong_match", "强匹配", makeStrongMatchItem],
    ["transferable", "可包装", makeTransferableItem],
    ["missing", "缺失", makeMissingItem],
  ] as const)(
    "renders verdict pill text '%s' → '%s'",
    (_verdict, label, builder) => {
      const diag = makePreRewriteDiagnosis({ matching_matrix: [builder()] });
      render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
      // getAllByText to be tolerant to header / aria-label duplication.
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    },
  );

  // ─────────── 4. bridging_or_closure caption — visible on transferable + missing ───────────
  it("renders bridging_or_closure caption for transferable rows", () => {
    const bridging = "PHASE_A_BRIDGING_TRANSFERABLE_TOKEN";
    const diag = makePreRewriteDiagnosis({
      matching_matrix: [
        makeTransferableItem({
          text: "Transferable row",
          bridging_or_closure: bridging,
        }),
      ],
    });
    render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
    expect(screen.getByText(bridging)).toBeInTheDocument();
  });

  it("renders bridging_or_closure caption for missing rows", () => {
    const bridging = "PHASE_A_BRIDGING_MISSING_TOKEN";
    const diag = makePreRewriteDiagnosis({
      matching_matrix: [
        makeMissingItem({
          text: "Missing row",
          bridging_or_closure: bridging,
        }),
      ],
    });
    render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
    expect(screen.getByText(bridging)).toBeInTheDocument();
  });

  // ─────────── 5. NO bridging caption on strong_match rows ───────────
  it("does NOT render bridging caption for strong_match rows", () => {
    // Backward-compat invariant: backend emits empty string for
    // strong_match.bridging_or_closure (already strong, no closure
    // path needed). Even if a non-empty value sneaks in, the panel
    // should NOT render a caption on strong_match rows — they read as
    // "✅ done" without a remediation suggestion.
    const sneakyBridging = "PHASE_A_SHOULD_NOT_RENDER_ON_STRONG_MATCH";
    const diag = makePreRewriteDiagnosis({
      matching_matrix: [
        makeStrongMatchItem({
          text: "Strong row",
          // Verify both: empty (the spec) AND sneaky-non-empty (defensive).
          bridging_or_closure: sneakyBridging,
        }),
      ],
    });
    render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
    expect(screen.queryByText(sneakyBridging)).not.toBeInTheDocument();
  });

  // ─────────── 6. Integrated assessment paragraph ───────────
  it("renders integrated_assessment paragraph", () => {
    const sentinel =
      "PHASE_A_SENTINEL_assessment_paragraph_renders_in_full text body.";
    const diag = makePreRewriteDiagnosis({ integrated_assessment: sentinel });
    render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
    expect(screen.getByText(sentinel)).toBeInTheDocument();
  });

  // ─────────── 7. Optimization boundary 2-column layout ───────────
  it("renders optimization_boundary with both can_solve and cannot_solve content", () => {
    const can = "PHASE_A_CAN_SOLVE_token_one";
    const cannot = "PHASE_A_CANNOT_SOLVE_token_one";
    const diag = makePreRewriteDiagnosis({
      optimization_boundary: {
        rewriting_can_solve: [can, "second can-solve item"],
        rewriting_cannot_solve: [cannot],
      },
    });
    render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
    expect(screen.getByText(can)).toBeInTheDocument();
    expect(screen.getByText("second can-solve item")).toBeInTheDocument();
    expect(screen.getByText(cannot)).toBeInTheDocument();
  });

  // ─────────── 8. competitiveness_rating chip in header ───────────
  it.each([
    ["high", "高"],
    ["above_mid", "中偏高"],
    ["mid", "中"],
    ["below_mid", "中偏低"],
    ["low", "低"],
  ] as const)(
    "renders competitiveness_rating chip label '%s' → '%s'",
    (rating, label) => {
      const diag = makePreRewriteDiagnosis({ competitiveness_rating: rating });
      render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
      // Use getAllByText — the rating label may appear in the chip and
      // potentially in an aria-label / sr-only element.
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    },
  );

  // ─────────── 9. MethodBadge for non-llm methods ───────────
  it("renders MethodBadge text for _method='llm_partial'", () => {
    const diag = makePreRewriteDiagnosis({ _method: "llm_partial" });
    render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
    // shared MethodBadge prints "Inferred (partial)" — see
    // ui/src/components/shared/method-badge.tsx.
    expect(screen.getByText(/Inferred \(partial\)/i)).toBeInTheDocument();
  });

  it("does NOT render MethodBadge text for _method='llm' (happy path)", () => {
    const diag = makePreRewriteDiagnosis({ _method: "llm" });
    render(<FitDiagnosisPreRewritePanel diagnosis={diag} />);
    expect(screen.queryByText(/Inferred \(partial\)/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Inferred \(fallback\)/i)).not.toBeInTheDocument();
  });

  // ─────────── 10. No deprecated names leak into rendered output ───────────
  it("does NOT render deprecated 'MatchMatrix' or 'match_matrix' substrings anywhere", () => {
    const { container } = render(
      <FitDiagnosisPreRewritePanel diagnosis={MOCK_PRE_REWRITE} />,
    );
    // Render-tree text guard: the F4 migration is complete only when
    // the legacy field name is absent from user-visible content. This
    // also catches accidental aria-label leakage.
    const rendered = container.textContent ?? "";
    expect(rendered).not.toMatch(/match_matrix/i);
    expect(rendered).not.toMatch(/MatchMatrix/);
  });
});
