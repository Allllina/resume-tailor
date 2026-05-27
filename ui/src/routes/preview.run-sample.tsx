import { createFileRoute, Link } from "@tanstack/react-router";
import diagnosesMulti from "../../../contracts/fixtures/diagnoses-multi.json";
import { FitDiagnosisPreRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPreRewritePanel";
import { FitDiagnosisPostRewritePanel } from "@/components/fit-diagnosis/FitDiagnosisPostRewritePanel";
import type {
  FitDiagnosisPreRewrite,
  FitDiagnosisPostRewrite,
} from "@/types/generated";

export const Route = createFileRoute("/preview/run-sample")({
  component: PreviewRunSample,
});

function PreviewRunSample() {
  const fixture = (diagnosesMulti as Array<{
    scenario_id: string;
    fit_diagnosis_pre_rewrite: FitDiagnosisPreRewrite;
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
          Run sample (composed)
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Scenario: <code className="font-mono text-xs">{fixture.scenario_id}</code>
          {" — both fit_diagnosis panels stacked in run-detail layout."}
        </p>
      </header>

      <FitDiagnosisPreRewritePanel diagnosis={fixture.fit_diagnosis_pre_rewrite} />
      <FitDiagnosisPostRewritePanel diagnosis={fixture.fit_diagnosis_post_rewrite} />
    </div>
  );
}
