import { createFileRoute, Link } from "@tanstack/react-router";
import diagnosesMulti from "../../../contracts/fixtures/diagnoses-multi.json";
import { FitDiagnosisPostRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPostRewritePanel";
import type { FitDiagnosisPostRewrite } from "@/types/generated";

export const Route = createFileRoute("/preview/fit-diagnosis-post")({
  component: PreviewFitDiagnosisPost,
});

function PreviewFitDiagnosisPost() {
  const fixture = (diagnosesMulti as Array<{
    scenario_id: string;
    fit_diagnosis_post_rewrite: FitDiagnosisPostRewrite;
  }>)[0];

  return (
    <div className="mx-auto max-w-2xl px-6 py-12 space-y-6">
      <header>
        <Link
          to="/preview"
          className="text-sm text-muted-foreground hover:text-foreground transition"
        >
          ← Preview index
        </Link>
        <h1
          className="mt-2 text-2xl font-bold tracking-tight text-foreground"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Fit Diagnosis — Post-rewrite
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Scenario: <code className="font-mono text-xs">{fixture.scenario_id}</code>
        </p>
      </header>

      <FitDiagnosisPostRewritePanel diagnosis={fixture.fit_diagnosis_post_rewrite} />
    </div>
  );
}
