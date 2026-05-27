/**
 * /demo — a recordable, self-running product walkthrough of Resume Tailor.
 *
 * ISOLATED: everything the demo needs lives in this route + src/components/demo/*.
 * It IMPORTS real production components (DraftRowV2, ActionQueue, LifecycleStrip,
 * FitDiagnosisPre/PostRewritePanel, ChangeCard, Sidebar) so the visuals are 1:1
 * with the redesigned product, but it never mutates them and uses only canned,
 * deterministic data (src/components/demo/demo-data.ts) — no network, loopable.
 *
 * Recording: open /demo (auto-plays + loops). Add ?clean=1 to hide the
 * play/restart control. Framing target 1280×800; degrades gracefully at other
 * sizes via a max-width 1280 / 16:10 letterboxed stage.
 *
 * The "camera" is a single wrapping <div> whose transform: scale()+translate()
 * is animated via a CSS transition; the sequence hook only swaps the target
 * preset per beat. transform-origin is the stage centre.
 */
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import type { CSSProperties } from "react";
import { Pause, Play, RotateCcw, Languages } from "lucide-react";
import { Sidebar } from "@/components/layout/Sidebar";
import { useDemoSequence } from "@/components/demo/use-demo-sequence";
import { DemoConversation } from "@/components/demo/demo-conversation";
import { DemoInboxLeft } from "@/components/demo/demo-inbox-left";
import { DemoDiagnosis } from "@/components/demo/demo-diagnosis";
import {
  DEMO_HERO_DETAIL,
  DEMO_HERO_SUMMARY,
  DEMO_RUNS,
  DEMO_HERO_DETAIL_ZH,
  DEMO_HERO_SUMMARY_ZH,
  DEMO_RUNS_ZH,
  DEMO_JD_TEXT,
  DEMO_AGENT_REPLY,
  DEMO_JD_TEXT_ZH,
  DEMO_AGENT_REPLY_ZH,
} from "@/components/demo/demo-data";
import { LangProvider, type UILang } from "@/lib/lang-context";

export const Route = createFileRoute("/demo")({
  head: () => ({
    meta: [{ title: "Demo — Resume Tailor" }],
  }),
  validateSearch: (search: Record<string, unknown>): { clean?: boolean; lang?: UILang } => ({
    clean: search.clean === "1" || search.clean === 1 || search.clean === true,
    lang: search.lang === "zh" ? "zh" : "en",
  }),
  component: DemoPage,
});

function DemoPage() {
  const { clean, lang } = Route.useSearch();
  const zh = lang === "zh";
  const demoData = zh
    ? { jdText: DEMO_JD_TEXT_ZH, agentReply: DEMO_AGENT_REPLY_ZH }
    : { jdText: DEMO_JD_TEXT, agentReply: DEMO_AGENT_REPLY };
  const heroSummary = zh ? DEMO_HERO_SUMMARY_ZH : DEMO_HERO_SUMMARY;
  const heroDetail = zh ? DEMO_HERO_DETAIL_ZH : DEMO_HERO_DETAIL;
  const baseRuns = zh ? DEMO_RUNS_ZH : DEMO_RUNS;

  const { state, restart, pause, resume, isPaused } = useDemoSequence(true, demoData);
  const composerRef = useRef<HTMLDivElement | null>(null);

  // Restart the sequence when lang changes so the new text plays from the top.
  useEffect(() => {
    restart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);

  // Inbox list grows by the hero run once the agent finishes streaming.
  const runs = state.heroInList ? [heroSummary, ...baseRuns] : baseRuns;

  // Camera transform. transform-origin: center; positive translate pushes the
  // content right/down, so to bring the lower-right composer to centre we use
  // negative x/y (see CAM_COMPOSER in use-demo-sequence).
  const cam = state.camera;
  const cameraStyle: CSSProperties = {
    transform: `scale(${cam.scale}) translate(${cam.x}%, ${cam.y}%)`,
    transformOrigin: "center center",
    transition: "transform 700ms cubic-bezier(0.4, 0, 0.2, 1)",
    willChange: "transform",
  };

  const diagnosisVisible = state.showDiagnosis;

  return (
    <LangProvider value={lang ?? "en"}>
    {/* Outer letterbox: centres a fixed 1280×800 stage and clips overflow so a
        screen-recorder framed to the stage gets clean edges at any window size. */}
    <div className="flex min-h-screen items-center justify-center overflow-hidden bg-neutral-950 p-0">
      <div
        className="relative overflow-hidden bg-background bg-grain shadow-2xl"
        style={{ width: 1280, height: 800 }}
      >
        {/* INBOX scene — the camera stage. Cross-fades out when diagnosis mounts. */}
        <div
          className="absolute inset-0"
          style={{
            opacity: diagnosisVisible ? 0 : 1,
            transition: "opacity 600ms ease-in-out",
            pointerEvents: diagnosisVisible ? "none" : "auto",
          }}
        >
          <div className="flex h-full" style={cameraStyle}>
            {/* Real product sidebar for full-fidelity framing. */}
            <div className="h-full shrink-0">
              <Sidebar collapsed={false} onToggle={() => {}} draftsCount={runs.length} overrideName="Alina" />
            </div>
            {/* Two-pane workspace: dense list + agent conversation. */}
            <main className="relative min-w-0 flex-1">
              <div className="grid h-full min-h-0 grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
                <DemoInboxLeft runs={runs} />
                <DemoConversation state={state} composerRef={composerRef} />
              </div>
            </main>
          </div>
        </div>

        {/* DIAGNOSIS scene — cross-fades in after zoom-out. Mounted only when
            needed so the auto-scroll measurement runs against a live layout. */}
        {diagnosisVisible ? (
          <div
            className="absolute inset-0"
            style={{ opacity: 1, transition: "opacity 600ms ease-in-out" }}
          >
            <div className="flex h-full">
              <div className="h-full shrink-0">
                <Sidebar collapsed={false} onToggle={() => {}} draftsCount={runs.length} overrideName="Alina" />
              </div>
              <main className="relative min-w-0 flex-1">
                <DemoDiagnosis run={heroDetail} scroll={state.diagnosisScroll} />
              </main>
            </div>
          </div>
        ) : null}

        {/* Recording control — hidden with ?clean=1. */}
        {!clean ? (
          <div className="absolute bottom-3 right-3 z-10 flex items-center gap-1.5 rounded-full border border-border bg-card/90 px-2 py-1.5 shadow-lg backdrop-blur">
            <button
              onClick={() => (isPaused ? resume() : pause())}
              className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground transition hover:bg-accent hover:text-foreground"
              title={isPaused ? "Resume" : "Pause"}
            >
              {isPaused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            </button>
            <button
              onClick={() => restart()}
              className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground transition hover:bg-accent hover:text-foreground"
              title="Restart"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
            <a
              href={`/demo?lang=${zh ? "en" : "zh"}${clean ? "&clean=1" : ""}`}
              className="flex h-7 items-center gap-1 rounded-full px-2 text-muted-foreground transition hover:bg-accent hover:text-foreground"
              title={zh ? "Switch to English" : "切换中文"}
            >
              <Languages className="h-3.5 w-3.5" />
              <span className="font-mono text-[10px]">{zh ? "EN" : "ZH"}</span>
            </a>
            <span
              className="px-1 font-mono text-[10px] text-muted-foreground"
              style={{ minWidth: 92 }}
            >
              {state.phase}
            </span>
          </div>
        ) : null}
      </div>
    </div>
    </LangProvider>
  );
}
