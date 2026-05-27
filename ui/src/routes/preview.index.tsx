import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/preview/")({
  component: PreviewIndex,
});

const PANELS = [
  {
    href: "/preview/fit-diagnosis-pre",
    title: "Fit Diagnosis — Pre-rewrite",
    subtitle: "匹配矩阵 + 整体评估 + 优化边界",
    body: "Section 4 panel rendered against contracts/fixtures/diagnoses-multi.json[0].fit_diagnosis_pre_rewrite.",
  },
  {
    href: "/preview/fit-diagnosis-post",
    title: "Fit Diagnosis — Post-rewrite",
    subtitle: "HM / HRBP 双视角 + 6-axis radar + 改进建议",
    body: "Section 8 panel rendered against contracts/fixtures/diagnoses-multi.json[0].fit_diagnosis_post_rewrite.",
  },
  {
    href: "/preview/run-sample",
    title: "Run sample (composed)",
    subtitle: "Both panels stacked, run-detail layout",
    body: "Mock /run/<id> page composing both fit_diagnosis panels — no backend required.",
  },
] as const;

function PreviewIndex() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <header className="mb-10">
        <h1
          className="text-3xl font-bold tracking-tight text-foreground"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Component Preview
        </h1>
        <p className="mt-2 text-muted-foreground">
          Visual verification of UI panels against canonical L3 fixtures —
          no backend tailor required.
        </p>
      </header>

      <ul className="space-y-3">
        {PANELS.map((panel) => (
          <li key={panel.href}>
            <Link
              to={panel.href}
              className="block rounded-xl border border-border/60 bg-card p-5 transition hover:bg-muted/40"
            >
              <div className="flex items-baseline gap-2">
                <h2 className="text-base font-semibold text-foreground">
                  {panel.title}
                </h2>
                <span className="font-mono text-[10px] text-muted-foreground">
                  {panel.href}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-muted-foreground">
                {panel.subtitle}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-foreground/70">
                {panel.body}
              </p>
            </Link>
          </li>
        ))}
      </ul>

      <p className="mt-8 text-xs text-muted-foreground">
        Full composition: visit{" "}
        <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
          /run/mock-anker-aigc
        </code>{" "}
        for backend-driven mock data.
      </p>
    </div>
  );
}
