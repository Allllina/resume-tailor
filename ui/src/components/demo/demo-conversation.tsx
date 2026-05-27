/**
 * DemoConversation — a thin, SCRIPT-DRIVEN presentational clone of
 * InboxV2Conversation (src/components/inbox/agent-conversation.tsx).
 *
 * WHY a clone and not the real component: the production pane is wired to
 * useTailorMutation (network) + useNavigate (router) and has no token-streaming
 * path — its one-shot flow navigates to /run/{id} on send. The demo needs to
 * (a) typewriter the JD into the composer, (b) stream the agent reply
 * token-by-token, and (c) keep the camera target stable — none of which the
 * real component can do deterministically. So we re-use the EXACT same Tailwind
 * classes / tokens / lucide icons here (Msg, AttachedDraft, composer markup are
 * copied verbatim) and drive them from useDemoSequence state. Visually it's 1:1
 * with production; only the data source differs.
 */
import { ArrowUp, FileText, Loader2, Paperclip, Sparkles } from "lucide-react";
import type { ReactNode, RefObject } from "react";
import { STATUS_META } from "@/components/inbox/status-meta";
import { humanizeAge, type RunSummary } from "@/lib/api";
import type { DemoState } from "./use-demo-sequence";
import { DEMO_HERO_SUMMARY, DEMO_JD_TEXT } from "./demo-data";

const MARKETS = [
  { value: "mainland-china", label: "CN" },
  { value: "north-america", label: "NA" },
  { value: "hong-kong", label: "HK" },
] as const;

export function DemoConversation({
  state,
  composerRef,
}: {
  state: DemoState;
  composerRef: RefObject<HTMLDivElement | null>;
}) {
  const userInitials = "AL";
  const showSending = state.phase === "typing" || state.phase === "sending" || state.phase === "streaming";

  return (
    <section className="flex min-h-0 flex-col bg-card/50">
      <header className="flex items-center gap-2.5 border-b border-border px-5 py-3.5">
        <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-primary/[0.14] text-primary">
          <Sparkles className="h-3.5 w-3.5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium text-foreground">Tailoring agent</div>
          <div className="text-[10.5px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
            4 runs · last 1 min ago
          </div>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden px-5 py-5">
        {/* Seeded intro */}
        <Msg from="agent" userInitials={userInitials}>
          <p className="m-0 text-[13px] leading-relaxed">
            Paste a job description and I'll tailor your resume through the right lens, then
            surface what to verify before you submit.
          </p>
        </Msg>

        {/* User JD bubble (appears on send) */}
        {state.userSent ? (
          <Msg from="user" userInitials={userInitials}>
            <p className="m-0 whitespace-pre-wrap text-[13px] leading-relaxed">
              {DEMO_JD_TEXT}
            </p>
          </Msg>
        ) : null}

        {/* Agent thinking indicator */}
        {state.thinking ? (
          <Msg from="agent" userInitials={userInitials} thinking>
            <p className="m-0 flex items-center gap-2 text-[12.5px] italic leading-snug text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              Tailoring against your master…
            </p>
          </Msg>
        ) : null}

        {/* Agent streamed reply + attached draft */}
        {state.agentReply ? (
          <Msg from="agent" userInitials={userInitials}>
            <p className="m-0 text-[13px] leading-relaxed">
              {state.agentReply}
              {state.phase === "streaming" ? (
                <span className="ml-0.5 inline-block h-3.5 w-[2px] translate-y-0.5 animate-pulse bg-primary align-middle" />
              ) : null}
            </p>
            {state.draftAttached ? <AttachedDraft run={DEMO_HERO_SUMMARY} /> : null}
          </Msg>
        ) : null}
      </div>

      {/* Sticky composer — this is the camera zoom target. */}
      <div ref={composerRef} className="border-t border-border px-4 pb-4 pt-3">
        <div
          className="rounded-xl border bg-card p-2.5 transition-shadow"
          style={{
            borderColor: "color-mix(in oklab, var(--primary) 35%, var(--border))",
            boxShadow:
              state.phase === "zoom_composer" || state.phase === "typing"
                ? "0 0 0 3px color-mix(in oklab, var(--primary) 18%, transparent)"
                : "none",
          }}
        >
          {/* Scripted textarea — a styled div, not a real <textarea>, so we can
              render a blinking caret after the typed text. Same padding / type
              scale / placeholder color as the production composer. */}
          <div className="min-h-[60px] w-full whitespace-pre-wrap px-2 py-1 text-[12.5px] leading-relaxed">
            {state.composerText ? (
              <>
                <span className="text-foreground">{state.composerText}</span>
                {state.phase === "typing" ? (
                  <span className="ml-px inline-block h-[15px] w-[2px] translate-y-0.5 animate-pulse bg-foreground/70 align-middle" />
                ) : null}
              </>
            ) : (
              <span className="text-muted-foreground">Paste a JD or ask the agent…</span>
            )}
          </div>
          <div className="mt-1 flex items-center justify-between">
            <div className="flex items-center gap-1">
              <span className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[11px] text-muted-foreground">
                <Paperclip className="h-[11px] w-[11px]" />
                Attach
              </span>
              <span className="self-center text-[10.5px] text-muted-foreground">·</span>
              {MARKETS.map((m) => (
                <span
                  key={m.value}
                  className={`inline-flex h-7 items-center rounded-md px-2 text-[11px] font-medium ${
                    m.value === "mainland-china"
                      ? "bg-primary/[0.12] text-primary"
                      : "text-muted-foreground"
                  }`}
                >
                  {m.label}
                </span>
              ))}
            </div>
            <span
              className={`inline-flex h-7 items-center gap-1.5 rounded-md px-3 text-[11px] font-medium text-primary-foreground transition ${
                showSending && state.phase !== "typing" ? "bg-primary/90" : "bg-primary"
              }`}
            >
              {showSending && state.phase !== "typing" ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Tailoring…
                </>
              ) : (
                <>
                  <ArrowUp className="h-3 w-3" />
                  Send
                </>
              )}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---- Msg + AttachedDraft: copied verbatim from agent-conversation.tsx ---- */

function Msg({
  from,
  thinking = false,
  userInitials,
  children,
}: {
  from: "agent" | "user";
  thinking?: boolean;
  userInitials: string;
  children: ReactNode;
}) {
  const isAgent = from === "agent";
  return (
    <div className={`flex items-start gap-2.5 ${isAgent ? "flex-row" : "flex-row-reverse"}`}>
      <span
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-medium ${
          isAgent ? "bg-primary/[0.14] text-primary" : "bg-foreground/[0.08] text-foreground"
        }`}
      >
        {isAgent ? <Sparkles className="h-[11px] w-[11px]" /> : userInitials}
      </span>
      <div className={`flex max-w-[82%] flex-col ${isAgent ? "items-start" : "items-end"}`}>
        <div
          className={
            thinking
              ? "rounded-xl border border-dashed border-border px-3 py-1.5"
              : isAgent
                ? "rounded-xl border border-border bg-card px-3.5 py-2.5"
                : "rounded-xl border bg-primary/[0.08] px-3.5 py-2.5"
          }
          style={
            !thinking && !isAgent
              ? { borderColor: "color-mix(in oklab, var(--primary) 20%, var(--border))" }
              : undefined
          }
        >
          {children}
        </div>
      </div>
    </div>
  );
}

function AttachedDraft({ run }: { run: RunSummary }) {
  const meta = STATUS_META[run.ui_status];
  const title = [run.company_hint, run.role_title_hint].filter(Boolean).join(" · ") || "Draft";
  return (
    <div className="mt-2.5 block rounded-lg border border-border bg-background/80 px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="flex h-[22px] w-[22px] items-center justify-center rounded-md bg-primary/[0.12] text-primary">
          <FileText className="h-[11px] w-[11px]" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-xs font-medium text-foreground">{title}</div>
          <div className="text-[10px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
            {run.run_id.slice(0, 12)} · {humanizeAge(run.created_at)}
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium" style={{ color: meta.color }}>
          <span className="inline-block h-[7px] w-[7px] rounded-full" style={{ background: meta.color }} aria-hidden />
          {meta.label}
        </span>
      </div>
    </div>
  );
}
