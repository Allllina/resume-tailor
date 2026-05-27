/**
 * InboxV2Conversation — the AI-native right pane.
 *
 * IMPORTANT — conversation-vs-one-shot gap: the real backend has NO chat
 * agent (no streaming, no multi-turn history endpoint). This pane *reframes*
 * the existing one-shot tailor flow as a conversation surface:
 *
 *   - A static/seeded agent intro message.
 *   - Recent real runs surfaced as agent "messages" with attached-draft cards
 *     that link to /run/{run_id} (the "result-as-message").
 *   - The composer posts a JD via the SAME useTailorMutation the old composer
 *     used. On send we optimistically render the JD as a user message + a
 *     "thinking" message; useTailorMutation's onSuccess already navigates to
 *     /run/{id}, so the result is shown on the run-detail page (no invented
 *     chat endpoint, streaming, or persisted history).
 *
 * Onboarding gate preserved: when has_resume === false we disable Send and
 * surface the same "Upload your resume" hint + /setup deep-link the real
 * FloatingComposer shows; a 412 from the backend triggers the same hint.
 */
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowUp, FileText, Loader2, Paperclip, Sparkles, Upload } from "lucide-react";
import { useTailorMutation, useUserStatus } from "@/lib/queries";
import {
  ApiError,
  humanizeAge,
  type RunSummary,
  type TargetMarket,
} from "@/lib/api";
import { STATUS_META } from "./status-meta";

const MARKETS: { value: TargetMarket; label: string }[] = [
  { value: "mainland-china", label: "CN" },
  { value: "north-america", label: "NA" },
  { value: "hong-kong", label: "HK" },
];

interface ChatMessage {
  id: string;
  from: "agent" | "user";
  text: string;
  thinking?: boolean;
}

export function InboxV2Conversation({
  runs,
  userInitials,
}: {
  runs: RunSummary[];
  userInitials: string;
}) {
  const [value, setValue] = useState("");
  const [marketOverride, setMarketOverride] = useState<TargetMarket | null>(null);
  const [localErr, setLocalErr] = useState<string | undefined>(undefined);
  const [pendingMsgs, setPendingMsgs] = useState<ChatMessage[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const tailor = useTailorMutation();
  const { data: status } = useUserStatus();

  const profileMarket = (status?.profile?.target_market_default ?? "mainland-china") as TargetMarket;
  const market = marketOverride ?? profileMarket;
  const isPending = tailor.isPending;
  const knownHasNoResume = status !== undefined && status.has_resume === false;

  const mutationErr = tailor.error;
  const is412 =
    mutationErr instanceof ApiError &&
    (mutationErr.status === 412 ||
      /no resume|upload-resume|upload your resume/i.test(mutationErr.detail ?? mutationErr.message));
  const showResumeHint = knownHasNoResume || is412;
  const sendDisabled = isPending || knownHasNoResume;

  // Keep the thread scrolled to the newest message.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [pendingMsgs.length, isPending]);

  function handleSend() {
    const text = value.trim();
    if (text.length < 50) {
      tailor.reset();
      setLocalErr("Paste a longer JD (at least 50 characters).");
      return;
    }
    setLocalErr(undefined);
    // Optimistically render the JD as a user message + an agent "thinking"
    // bubble. On success useTailorMutation navigates to /run/{id}.
    setPendingMsgs((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, from: "user", text },
      { id: `t-${Date.now()}`, from: "agent", text: "Tailoring against your master…", thinking: true },
    ]);
    setValue("");
    if (knownHasNoResume) return; // short-circuit; hint is already shown
    tailor.mutate({
      mode: "auto",
      jd: { source: "paste", raw_text: text },
      candidate_profile_ref: "default",
      target_market: market,
    });
  }

  // Recent runs become agent "messages" (newest 3), oldest-first so they read
  // top-to-bottom like a thread.
  const recent = runs.slice(0, 3).slice().reverse();

  return (
    <section className="flex min-h-0 flex-col bg-card/50">
      <header className="flex items-center gap-2.5 border-b border-border px-5 py-3.5">
        <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-primary/[0.14] text-primary">
          <Sparkles className="h-3.5 w-3.5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium text-foreground">Tailoring agent</div>
          <div className="text-[10.5px] text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
            {recent.length > 0
              ? `${runs.length} run${runs.length === 1 ? "" : "s"} · last ${humanizeAge(runs[0].created_at)}`
              : "Paste a JD to start your first run"}
          </div>
        </div>
      </header>

      <div ref={scrollRef} className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto px-5 py-5">
        {/* Seeded intro */}
        <Msg from="agent" userInitials={userInitials}>
          <p className="m-0 text-[13px] leading-relaxed">
            Paste a job description and I'll tailor your resume through the right lens, then
            surface what to verify before you submit.
          </p>
        </Msg>

        {/* Recent runs as result-messages */}
        {recent.map((run) => (
          <Msg key={run.run_id} from="agent" userInitials={userInitials}>
            <p className="m-0 text-[13px] leading-relaxed">
              {run.narration?.trim()
                ? run.narration
                : `Tailored ${[run.company_hint, run.role_title_hint].filter(Boolean).join(" · ") || "your draft"}.`}
            </p>
            <AttachedDraft run={run} />
          </Msg>
        ))}

        {/* Optimistic user + thinking messages from the current send */}
        {pendingMsgs.map((m) =>
          m.thinking ? (
            <Msg key={m.id} from="agent" userInitials={userInitials} thinking>
              <p className="m-0 text-[12.5px] italic leading-snug text-muted-foreground">{m.text}</p>
            </Msg>
          ) : (
            <Msg key={m.id} from="user" userInitials={userInitials}>
              <p className="m-0 whitespace-pre-wrap text-[13px] leading-relaxed">
                {m.text.length > 280 ? `${m.text.slice(0, 280)}…` : m.text}
              </p>
            </Msg>
          ),
        )}
      </div>

      {/* Sticky composer */}
      <div className="border-t border-border px-4 pb-4 pt-3">
        {showResumeHint ? (
          <div className="mb-2 flex items-start gap-2 rounded-md border border-attention/40 bg-attention/5 px-2.5 py-2">
            <Upload className="mt-0.5 h-3.5 w-3.5 shrink-0 text-attention-foreground/80" />
            <div className="flex-1 text-[11px] leading-relaxed text-foreground/85">
              Upload your resume to start tailoring.{" "}
              <Link to="/setup" className="font-medium text-primary underline-offset-2 hover:underline">
                Upload now →
              </Link>
            </div>
          </div>
        ) : localErr ? (
          <p className="mb-2 text-[11px] text-error">{localErr}</p>
        ) : mutationErr && !showResumeHint ? (
          <p className="mb-2 text-[11px] text-error">
            {mutationErr instanceof ApiError
              ? (mutationErr.detail ?? mutationErr.message)
              : (mutationErr as Error).message}
          </p>
        ) : null}

        <div className="rounded-xl border bg-card p-2.5" style={{ borderColor: "color-mix(in oklab, var(--primary) 35%, var(--border))" }}>
          <textarea
            ref={textareaRef}
            rows={3}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              if (localErr) setLocalErr(undefined);
            }}
            placeholder="Paste a JD or ask the agent…"
            disabled={isPending}
            className="w-full resize-none bg-transparent px-2 py-1 text-[12.5px] leading-relaxed placeholder:text-muted-foreground focus:outline-none"
          />
          <div className="mt-1 flex items-center justify-between">
            <div className="flex items-center gap-1">
              <button
                type="button"
                disabled
                title="Attachments arrive later — paste JD text for now"
                className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-[11px] text-muted-foreground transition hover:text-foreground disabled:opacity-50"
              >
                <Paperclip className="h-[11px] w-[11px]" />
                Attach
              </button>
              <span className="self-center text-[10.5px] text-muted-foreground">·</span>
              {MARKETS.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  onClick={() => setMarketOverride(m.value)}
                  disabled={isPending}
                  className={`h-7 rounded-md px-2 text-[11px] font-medium transition ${
                    market === m.value ? "bg-primary/[0.12] text-primary" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={handleSend}
              disabled={sendDisabled}
              title={knownHasNoResume ? "Upload a resume in /setup first" : undefined}
              className="inline-flex h-7 items-center gap-1.5 rounded-md bg-primary px-3 text-[11px] font-medium text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isPending ? (
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
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

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
          style={!thinking && !isAgent ? { borderColor: "color-mix(in oklab, var(--primary) 20%, var(--border))" } : undefined}
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
    <Link
      to="/run/$id"
      params={{ id: run.run_id }}
      className="mt-2.5 block rounded-lg border border-border bg-background/80 px-3 py-2.5 no-underline transition hover:border-foreground/15"
    >
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
    </Link>
  );
}
