import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Loader2, Upload } from "lucide-react";
import { useTailorMutation, useUserStatus } from "@/lib/queries";
import { ApiError, type TargetMarket } from "@/lib/api";

const MARKETS: { value: TargetMarket; label: string }[] = [
  { value: "mainland-china", label: "CN" },
  { value: "north-america", label: "US" },
  { value: "hong-kong", label: "HK" },
];

/**
 * Composer pinned to the bottom-right corner. Send is always allowed at the
 * UI level (per Q4 = c), but when we know the user has no master resume we
 * proactively disable Send + show the same hint we'd surface from a 412 —
 * avoids a wasted POST round-trip.
 *
 * On a 412 (backend says "no resume uploaded"), we surface a friendly
 * inline hint with a deep-link to /setup. Other 4xx / 5xx / network errors
 * keep the existing generic error display.
 */
export function FloatingComposer() {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  const [marketOverride, setMarketOverride] = useState<TargetMarket | null>(null);
  const [localErr, setLocalErr] = useState<string | undefined>(undefined);
  const tailor = useTailorMutation();
  const { data: status } = useUserStatus();

  // Wave 2.7 P4: market defaults from user's profile setting; user can
  // override per-tailor by clicking a different pill.
  const profileMarket = (status?.profile?.target_market_default ?? "mainland-china") as TargetMarket;
  const market = marketOverride ?? profileMarket;

  const isPending = tailor.isPending;
  const hasResume = status?.has_resume ?? true; // optimistic: if we don't know yet, allow
  const knownHasNoResume = status !== undefined && status.has_resume === false;

  // 412 detection: FastAPI puts the human message in `detail`. We also
  // accept any message that mentions "resume" + "upload" as a fallback.
  const mutationErr = tailor.error;
  const is412 =
    mutationErr instanceof ApiError &&
    (mutationErr.status === 412 ||
      /no resume|upload-resume|upload your resume/i.test(mutationErr.detail ?? mutationErr.message));

  // 503 detection: Gate 2 (llm_unreachable) or Phase 2 (sub_skill_unavailable).
  const is503LlmDown =
    mutationErr instanceof ApiError &&
    mutationErr.status === 503 &&
    (mutationErr.detailObj?.code === "llm_unreachable" ||
      (mutationErr.detailObj?.code === "sub_skill_unavailable" &&
        mutationErr.detailObj?.llm_unreachable === true));
  const is503SubSkill =
    mutationErr instanceof ApiError &&
    mutationErr.status === 503 &&
    mutationErr.detailObj?.code === "sub_skill_unavailable" &&
    !mutationErr.detailObj?.llm_unreachable;

  const showResumeHint = knownHasNoResume || is412;

  function handleSend() {
    const text = value.trim();
    if (text.length < 50) {
      tailor.reset();
      setLocalErr("Paste a longer JD (at least 50 characters).");
      return;
    }
    setLocalErr(undefined);
    // Defensive: if we already know the user has no resume, short-circuit
    // and surface the hint instead of hitting the backend for a 412.
    if (knownHasNoResume) return;
    tailor.mutate({
      mode: "auto",
      jd: { source: "paste", raw_text: text },
      candidate_profile_ref: "default",
      target_market: market,
    });
  }

  const sendDisabled = isPending || knownHasNoResume;

  return (
    <div className="fixed bottom-6 right-6 z-30">
      <div
        className={`rounded-2xl border border-border bg-card/95 backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.06)] transition-all duration-200 ${
          open ? "w-[480px]" : "w-[300px] h-14"
        }`}
        style={open ? { minHeight: 160 } : undefined}
      >
        {open ? (
          <div className="h-full p-3 flex flex-col gap-2">
            <textarea
              autoFocus
              value={value}
              onChange={(e) => {
                setValue(e.target.value);
                if (localErr) setLocalErr(undefined);
              }}
              onBlur={() => !value && !showResumeHint && setOpen(false)}
              placeholder="Paste a JD…"
              className="flex-1 w-full resize-none bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none"
              rows={4}
              disabled={isPending}
            />

            {/* 412 / no-resume gate — show first, dominates other inline errors */}
            {showResumeHint ? (
              <div className="flex items-start gap-2 rounded-md border border-attention/40 bg-attention/5 px-2.5 py-2">
                <Upload className="mt-0.5 h-3.5 w-3.5 shrink-0 text-attention-foreground/80" />
                <div className="flex-1 text-[11px] leading-relaxed text-foreground/85">
                  Upload your resume to start tailoring.{" "}
                  <Link
                    to="/setup"
                    className="font-medium text-primary underline-offset-2 hover:underline"
                  >
                    Upload now →
                  </Link>
                </div>
              </div>
            ) : is503LlmDown ? (
              <div className="flex items-start gap-2 rounded-md border border-error/30 bg-error/5 px-2.5 py-2">
                <span className="mt-0.5 h-3.5 w-3.5 shrink-0 text-error text-[11px] font-bold">!</span>
                <p className="flex-1 text-[11px] leading-relaxed text-foreground/85">
                  AI service is currently unavailable. Try again in a few minutes.
                </p>
              </div>
            ) : is503SubSkill ? (
              <div className="flex items-start gap-2 rounded-md border border-error/30 bg-error/5 px-2.5 py-2">
                <span className="mt-0.5 h-3.5 w-3.5 shrink-0 text-error text-[11px] font-bold">!</span>
                <p className="flex-1 text-[11px] leading-relaxed text-foreground/85">
                  {String(
                    (mutationErr as ApiError).detailObj?.sub_skill ?? "A sub-skill"
                  )} returned unusable output. Retry or check the backend logs.
                </p>
              </div>
            ) : localErr ? (
              <p className="text-[11px] text-error">{localErr}</p>
            ) : mutationErr ? (
              <p className="text-[11px] text-error">
                {mutationErr instanceof ApiError ? (mutationErr.detail ?? mutationErr.message) : (mutationErr as Error).message}
              </p>
            ) : null}

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                {MARKETS.map((m) => (
                  <button
                    key={m.value}
                    onClick={() => setMarketOverride(m.value)}
                    disabled={isPending}
                    className={`h-7 px-2.5 rounded-md text-[11px] font-medium transition ${
                      market === m.value
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              <button
                onClick={handleSend}
                disabled={sendDisabled}
                title={knownHasNoResume ? "Upload a resume in /setup first" : undefined}
                className="h-7 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
              >
                {isPending ? (
                  <>
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Tailoring…
                  </>
                ) : (
                  <>Send ↵</>
                )}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setOpen(true)}
            className="w-full h-full px-4 flex items-center gap-3 text-left text-sm text-muted-foreground hover:text-foreground transition"
          >
            <span className="text-primary">+</span>
            Paste a JD…
            <span className="ml-auto text-[11px] font-mono opacity-60">↵</span>
          </button>
        )}
      </div>
    </div>
  );
}
