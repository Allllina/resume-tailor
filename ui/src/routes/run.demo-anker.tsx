import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ChangeCard } from "@/components/change-card";
import { WhyExpand } from "@/components/why-expand";

export const Route = createFileRoute("/run/demo-anker")({
  head: () => ({
    meta: [
      { title: "Sample run · Anker AIGC 内容实习生" },
      {
        name: "description",
        content:
          "Sample tailoring run — see how Resume Tailor reads the JD and rewrites your resume. Nothing is submitted.",
      },
    ],
  }),
  component: DemoAnkerPage,
});

type Phase = "tailoring" | "ready" | "submitted";

function DemoAnkerPage() {
  const [phase, setPhase] = useState<Phase>("tailoring");
  const [channel, setChannel] = useState("安克招聘 portal");

  useEffect(() => {
    const t = setTimeout(() => setPhase("ready"), 1500);
    return () => clearTimeout(t);
  }, []);

  return (
    <>
      <header className="mx-auto max-w-2xl px-6 pt-8 pb-4 flex items-center justify-between">
        <Link
          to="/"
          className="text-sm text-muted-foreground hover:text-foreground transition"
        >
          ← Inbox
        </Link>
        <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
          Sample · not submitted
        </span>
      </header>

      <main className="mx-auto max-w-2xl px-6 pb-32">
        <div className="pb-8 border-b border-border">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Sample draft · demo-anker
          </p>
          <h1 className="mt-3 text-3xl text-foreground">Anker AIGC 内容实习生</h1>
          <p className="mt-1 text-sm text-muted-foreground">深圳 · C 产品运营 lens</p>
        </div>

        {phase === "tailoring" ? (
          <Tailoring />
        ) : (
          <>
            <div className="pt-8 pb-6">
              <p className="text-sm text-foreground leading-relaxed">
                <span className="text-primary mr-2">✦</span>I made{" "}
                <span className="font-medium">3 changes</span> from your{" "}
                <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">C 产品运营</span>{" "}
                master.
              </p>
            </div>

            <div className="space-y-3">
              <ChangeCard
                title="Skills row reordered"
                before="数据分析 · AI 工具 · Python"
                after="AI 工具 · 数据分析 · Python"
                note="AI 工具 → first (was second)"
              />
              <ChangeCard
                title="Project 2 retitled"
                before="Beauty Trend 美妆趋势分析"
                after="AIGC 内容生成原型 · Beauty Trend"
                note="Surfaced AIGC keyword for ATS match"
              />
              <ChangeCard
                title="Summary regenerated"
                before="商业分析背景,熟悉数据驱动方法..."
                after="兼具 BA 思维与 AI 工具实操,在 3 个项目中..."
                note="Tone shifted toward 内容/产品 vocabulary"
              />
            </div>

            <div className="mt-12 pt-8 border-t border-border">
              {phase === "submitted" ? (
                <div className="rounded-xl border border-border bg-card p-6 text-center">
                  <p className="text-sm text-foreground">
                    <span className="text-verified mr-2">✓</span>
                    Sample submission simulated. Nothing was actually sent.
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    On a real draft, I'd open the channel and paste in your tailored materials.
                  </p>
                  <Link
                    to="/"
                    className="mt-5 inline-block h-11 px-5 rounded-lg bg-foreground text-background text-sm font-medium hover:opacity-90 transition leading-[2.75rem]"
                  >
                    Take me to my Inbox →
                  </Link>
                </div>
              ) : (
                <>
                  <button
                    onClick={() => {
                      if (typeof window !== "undefined") {
                        window.localStorage.setItem("rt:has-drafts", "1");
                      }
                      setPhase("submitted");
                    }}
                    className="w-full h-14 rounded-xl bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition flex items-center justify-center gap-2"
                  >
                    Submit (sample) to {channel}
                    <span>→</span>
                  </button>
                  <div className="mt-3 text-center">
                    <button
                      onClick={() =>
                        setChannel(channel === "安克招聘 portal" ? "Boss 直聘" : "安克招聘 portal")
                      }
                      className="text-xs text-muted-foreground hover:text-foreground transition"
                    >
                      ⌄ change channel
                    </button>
                  </div>
                </>
              )}
            </div>

            <div className="mt-10">
              <WhyExpand />
            </div>
          </>
        )}
      </main>
    </>
  );
}

function Tailoring() {
  return (
    <div className="pt-12 pb-6 flex items-center gap-3">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
      </span>
      <p className="text-sm text-foreground/85">
        Reading the JD, scoring your experiences, drafting changes…
      </p>
    </div>
  );
}
