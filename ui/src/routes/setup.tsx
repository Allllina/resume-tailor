import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ResumeUpload } from "@/components/upload/ResumeUpload";
import { ExperiencesUpload } from "@/components/upload/ExperiencesUpload";
import { ScoringStatusPill } from "@/components/upload/ScoringStatusPill";
import { MasterStatusPill } from "@/components/master/MasterStatusPill";
import {
  useGenerateMaster,
  useMasters,
  usePatchUserProfile,
  useSetLensTargets,
  useUserStatus,
} from "@/lib/queries";
import {
  INDUSTRIES,
  LENS_DESCRIPTIONS_EN,
  LENS_LABELS_ZH,
  LENS_PLACEHOLDERS,
  LENSES,
  type Lens,
  type MastersResponse,
  type MasterKind,
  type TargetMarket,
} from "@/lib/api";

const MARKET_OPTIONS: Array<{ id: TargetMarket; label: string; sub: string }> = [
  {
    id: "mainland-china",
    label: "中国大陆 / Mainland China",
    sub: "Resume in 简体中文 · domestic conventions (照片, 高校排名, 政治面貌 optional)",
  },
  {
    id: "north-america",
    label: "North America (US / Canada)",
    sub: "Resume in English · 1-page convention, no photo, action-verb bullets",
  },
  {
    id: "hong-kong",
    label: "Hong Kong",
    sub: "Resume in English w/ optional 中英对照 · HK conventions",
  },
];

const INDUSTRY_STORAGE_KEY = "rt:target_industry";

function readStoredIndustry(): string {
  if (typeof window === "undefined" || typeof localStorage === "undefined") return "";
  return localStorage.getItem(INDUSTRY_STORAGE_KEY) ?? "";
}

function writeStoredIndustry(id: string): void {
  if (typeof window === "undefined" || typeof localStorage === "undefined") return;
  if (id) localStorage.setItem(INDUSTRY_STORAGE_KEY, id);
  else localStorage.removeItem(INDUSTRY_STORAGE_KEY);
}

export const Route = createFileRoute("/setup")({
  head: () => ({
    meta: [
      { title: "Get started — Resume Tailor" },
      {
        name: "description",
        content:
          "Upload your resume, pick target directions, generate per-lens masters, then add experiences. After setup, paste any JD into the floating composer for an AI-tailored draft.",
      },
    ],
  }),
  component: SetupWizard,
});

type Step = 1 | 2 | 3 | 4 | 5;

interface SetupStepState {
  n: Step;
  label: string;
  done: boolean;
}

export function getSetupStepStates({
  hasResume,
  directionDone,
  mastersDone,
  experiencesDone,
}: {
  hasResume: boolean;
  directionDone: boolean;
  mastersDone: boolean;
  experiencesDone: boolean;
}): SetupStepState[] {
  return [
    { n: 1, label: "Resume", done: hasResume },
    { n: 2, label: "Direction", done: directionDone },
    { n: 3, label: "Masters", done: mastersDone },
    { n: 4, label: "Experiences", done: experiencesDone },
    { n: 5, label: "Done", done: false },
  ];
}

function mastersReady(chosenLenses: Lens[], masters?: MastersResponse): boolean {
  return (
    chosenLenses.length > 0 &&
    chosenLenses.every((lens) => (masters?.[lens]?.status ?? "absent") === "ready")
  );
}

function SetupWizard() {
  const navigate = useNavigate();
  const { data: status } = useUserStatus();
  const { data: masters } = useMasters(true);
  const [step, setStep] = useState<Step>(1);
  const [skipScoring, setSkipScoring] = useState(false);
  const [skipGeneration, setSkipGeneration] = useState(false);

  // Step 2 form state — held locally until "Continue" submits.
  const [primary, setPrimary] = useState<Lens | null>(null);
  const [secondary, setSecondary] = useState<Lens[]>([]);
  const [masterKind, setMasterKind] = useState<MasterKind | null>(null);
  const [market, setMarket] = useState<TargetMarket | null>(null);
  const profileSeededRef = useRef(false);
  // Seed Step 2 from the existing profile once status arrives. After that,
  // user edits stay local until Continue persists them.
  useEffect(() => {
    if (profileSeededRef.current || !status?.profile) return;
    profileSeededRef.current = true;
    if (status.profile.target_market_default) {
      setMarket(status.profile.target_market_default);
    }
    if (status.profile.target_lens_default) {
      setPrimary(status.profile.target_lens_default);
    }
    if (status.profile.target_lens_secondary?.length) {
      setSecondary(status.profile.target_lens_secondary);
    }
    if (status.profile.master_kind) {
      setMasterKind(status.profile.master_kind);
    }
  }, [status?.profile]);

  const hasResume = status?.has_resume ?? false;
  const expCount = status?.experience_count ?? 0;
  const expScored = status?.experiences_scored_count ?? 0;
  const allScored = expCount > 0 && expScored === expCount;

  // Auto-advance from step 1 once a resume is uploaded
  useEffect(() => {
    if (step === 1 && hasResume) setStep(2);
  }, [hasResume, step]);

  const canFinish = hasResume && (allScored || skipScoring || expCount === 0);
  const chosenLenses: Lens[] = useMemo(
    () => (primary ? [primary, ...secondary.filter((s) => s !== primary)] : []),
    [primary, secondary],
  );
  const directionDone = primary !== null && market !== null;
  const stepStates = getSetupStepStates({
    hasResume,
    directionDone,
    mastersDone: mastersReady(chosenLenses, masters),
    experiencesDone: expCount > 0 && allScored,
  });

  return (
    <div className="min-h-screen bg-background bg-grain">
      <header className="border-b border-border bg-background/80 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <Link to="/" className="text-xs text-muted-foreground transition hover:text-foreground">
            ← Inbox
          </Link>
          <span className="text-[11.5px] text-muted-foreground">Step {step} of 5</span>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-8 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-8 lg:self-start">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              Resume Tailor
            </p>
            <h1
              className="mt-2 text-3xl leading-tight text-foreground"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              Setup
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Upload the source material once. The agent uses it to route every JD into the right
              lens and draft from the strongest evidence.
            </p>
          </div>
          <ol className="mt-7 space-y-1.5">
            {stepStates.map((s) => (
              <SetupStepButton
                key={s.n}
                n={s.n}
                label={s.label}
                active={step === s.n}
                done={s.done}
                onClick={() => setStep(s.n)}
              />
            ))}
          </ol>
        </aside>

        <main className="min-w-0 pb-20">
          <div className="rounded-lg border border-border bg-card px-6 py-6 shadow-[0_1px_0_rgba(15,23,42,0.03)]">
            {step === 1 ? <Step1 /> : null}

            {step === 2 ? (
              <Step2DirectionPicker
                primary={primary}
                secondary={secondary}
                masterKind={masterKind}
                market={market}
                setPrimary={setPrimary}
                setSecondary={setSecondary}
                setMasterKind={setMasterKind}
                setMarket={setMarket}
                onContinue={() => setStep(3)}
                onBack={() => setStep(1)}
              />
            ) : null}

            {step === 3 ? (
              <Step3MasterGen
                chosenLenses={chosenLenses}
                primary={primary}
                skipGeneration={skipGeneration}
                setSkipGeneration={setSkipGeneration}
                onContinue={() => setStep(4)}
                onBack={() => setStep(2)}
              />
            ) : null}

            {step === 4 ? (
              <Step4Experiences
                expCount={expCount}
                expScored={expScored}
                allScored={allScored}
                skipScoring={skipScoring}
                setSkipScoring={setSkipScoring}
                canContinue={canFinish}
                onContinue={() => setStep(5)}
                onBack={() => setStep(3)}
              />
            ) : null}

            {step === 5 ? (
              <Step5Done expCount={expCount} onGo={() => navigate({ to: "/" })} />
            ) : null}
          </div>
        </main>
      </div>
    </div>
  );
}

function SetupStepButton({
  n,
  active,
  done,
  label,
  onClick,
}: {
  n: Step;
  active: boolean;
  done: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={`flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-left transition ${
          active ? "bg-card text-foreground shadow-[0_1px_0_rgba(0,0,0,0.03)]" : "text-muted-foreground hover:bg-accent hover:text-foreground"
        }`}
      >
      <span
        className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-medium ${
          done
            ? "bg-verified text-verified-foreground"
            : active
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground"
        }`}
      >
        {done ? <Check className="h-3 w-3" /> : n}
      </span>
        <span className={`text-sm ${active ? "font-medium" : ""}`}>{label}</span>
      </button>
    </li>
  );
}

/* ----------------- Step 1 ----------------- */

function Step1() {
  return (
    <section>
      <h2
        className="text-xl text-foreground"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        01 · Upload your resume
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
        Required. I parse your resume into a master and use it as the starting point for every JD.
        Native <span className="font-mono text-xs">.tex</span> is best (lossless);{" "}
        <span className="font-mono text-xs">.md</span> /{" "}
        <span className="font-mono text-xs">.docx</span> /{" "}
        <span className="font-mono text-xs">.pdf</span> are converted on upload.
      </p>
      <div className="mt-4">
        <ResumeUpload />
      </div>
    </section>
  );
}

/* ----------------- Step 2 — Direction picking ----------------- */

interface Step2Props {
  primary: Lens | null;
  secondary: Lens[];
  masterKind: MasterKind | null;
  market: TargetMarket | null;
  setPrimary: (l: Lens | null) => void;
  setSecondary: (next: Lens[]) => void;
  setMasterKind: (k: MasterKind | null) => void;
  setMarket: (m: TargetMarket | null) => void;
  onContinue: () => void;
  onBack: () => void;
}

function Step2DirectionPicker({
  primary,
  secondary,
  masterKind,
  market,
  setPrimary,
  setSecondary,
  setMasterKind,
  setMarket,
  onContinue,
  onBack,
}: Step2Props) {
  const setLensTargetsMut = useSetLensTargets();
  const patchProfile = usePatchUserProfile();
  const [errMsg, setErrMsg] = useState<string | null>(null);
  const [industry, setIndustry] = useState<string>(() => readStoredIndustry());

  const toggleSecondary = (lens: Lens) => {
    if (secondary.includes(lens)) {
      setSecondary(secondary.filter((l) => l !== lens));
    } else {
      setSecondary([...secondary, lens]);
    }
  };

  const submit = () => {
    if (!primary) {
      setErrMsg("Pick a primary direction first.");
      return;
    }
    if (!market) {
      setErrMsg("Pick a target market — it controls resume language and conventions.");
      return;
    }
    setErrMsg(null);
    setLensTargetsMut.mutate(
      { primary, secondary: secondary.filter((l) => l !== primary) },
      {
        onSuccess: () => {
          // Best-effort persist master_kind + target_market — non-blocking, Step 2
          // advances regardless of patch outcome since these fields are optional metadata.
          const body: { master_kind?: MasterKind; target_market_default?: TargetMarket } = {};
          if (masterKind) body.master_kind = masterKind;
          if (market) body.target_market_default = market;
          if (Object.keys(body).length > 0) {
            patchProfile.mutate(body, { onError: () => undefined });
          }
          onContinue();
        },
        onError: (err) => setErrMsg((err as Error).message),
      },
    );
  };

  const canContinue = primary !== null && !setLensTargetsMut.isPending;

  return (
    <section>
      <h2
        className="text-xl text-foreground"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        02 · What kind of role are you targeting?
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
        Pick the market (drives resume language), industry, and a role family. I'll generate a
        tailored master per role family — applying across multiple? Pick a primary + add
        secondaries; each gets its own master.
      </p>

      {/* Target market — REQUIRED. Controls resume language and country conventions. */}
      <div className="mt-6 space-y-2">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Target market <span className="text-error">*</span>
        </p>
        <p className="text-[11px] text-muted-foreground">
          Determines resume language and country-specific conventions (photo, ranking, format).
        </p>
        <div className="space-y-2">
          {MARKET_OPTIONS.map((opt) => (
            <label
              key={opt.id}
              className={`flex items-start gap-3 rounded-lg border px-3 py-2.5 cursor-pointer transition ${
                market === opt.id
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card hover:border-foreground/20"
              }`}
            >
              <input
                type="radio"
                name="target-market"
                value={opt.id}
                checked={market === opt.id}
                onChange={() => setMarket(opt.id)}
                className="mt-1 h-3.5 w-3.5 accent-[var(--primary)]"
              />
              <span className="flex-1">
                <span className="block text-sm font-medium text-foreground">{opt.label}</span>
                <span className="block text-xs text-muted-foreground">{opt.sub}</span>
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Industry picker — v0.5 stores locally; v0.6 will sync to profile + branch playbooks. */}
      <div className="mt-6 space-y-1.5">
        <div className="flex items-baseline justify-between gap-3">
          <label
            htmlFor="industry-select"
            className="text-xs font-medium uppercase tracking-wider text-muted-foreground"
          >
            Target industry
          </label>
          <p className="text-[10px] italic text-muted-foreground/70">
            Saved locally · industry-aware playbooks land in v0.6
          </p>
        </div>
        <select
          id="industry-select"
          value={industry}
          onChange={(e) => {
            const next = e.target.value;
            setIndustry(next);
            writeStoredIndustry(next);
          }}
          className="w-full rounded-lg border border-border bg-card px-3 py-2.5 text-sm text-foreground transition hover:border-foreground/20 focus:border-primary focus:outline-none"
        >
          <option value="">— Pick an industry —</option>
          <optgroup label="Active">
            {INDUSTRIES.filter((o) => o.active).map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label_en}
              </option>
            ))}
          </optgroup>
          <optgroup label="Coming soon (v0.6)">
            {INDUSTRIES.filter((o) => !o.active).map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label_en}
              </option>
            ))}
          </optgroup>
        </select>
        {industry ? (
          (() => {
            const opt = INDUSTRIES.find((o) => o.id === industry);
            if (!opt) return null;
            return (
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                {opt.active ? opt.description_en : `${opt.description_en} · playbook in v0.6`}
              </p>
            );
          })()
        ) : (
          <p className="text-[11px] italic text-muted-foreground/70">
            Optional — pick the sector you're targeting (helps v0.6 routing).
          </p>
        )}
      </div>

      {/* Active role families (built-in playbooks). */}
      <div className="mt-6 space-y-1.5">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Role family — Active playbooks
          </p>
          <p className="text-[10px] italic text-muted-foreground/70">
            Pick one primary · others = secondary
          </p>
        </div>
        <p className="text-[11px] text-muted-foreground">
          These 5 route end-to-end (scoring · playbook · per-lens master · tailoring). Click once
          for primary; click another to add as secondary.
        </p>
        <div className="space-y-2">
          {LENSES.map((lens) => {
            const isPrimary = primary === lens;
            const isSecondary = secondary.includes(lens) && !isPrimary;
            const onClick = () => {
              if (isPrimary) {
                // Demote primary to nothing — user is unselecting.
                setPrimary(null);
              } else if (isSecondary) {
                // Remove from secondary.
                toggleSecondary(lens);
              } else if (primary === null) {
                setPrimary(lens);
              } else {
                toggleSecondary(lens);
              }
            };
            return (
              <button
                key={`active-${lens}`}
                type="button"
                onClick={onClick}
                className={`flex w-full items-start gap-3 rounded-lg border px-3 py-2.5 text-left transition ${
                  isPrimary
                    ? "border-primary bg-primary/10"
                    : isSecondary
                      ? "border-primary/60 bg-primary/5"
                      : "border-border bg-card hover:border-foreground/20"
                }`}
              >
                <span
                  className={`mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[9px] font-mono ${
                    isPrimary
                      ? "border-primary bg-primary text-primary-foreground"
                      : isSecondary
                        ? "border-primary/60 bg-primary/20 text-primary"
                        : "border-border text-muted-foreground"
                  }`}
                  aria-hidden
                >
                  {isPrimary ? "1°" : isSecondary ? "2°" : ""}
                </span>
                <span className="flex-1">
                  <span className="block text-sm font-medium text-foreground">
                    {LENS_LABELS_ZH[lens]}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {LENS_DESCRIPTIONS_EN[lens]}
                  </span>
                </span>
                {isPrimary ? (
                  <span className="rounded bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-primary">
                    primary
                  </span>
                ) : isSecondary ? (
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    secondary
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      </div>

      {/* Coming-soon role families (visual placeholders only). */}
      <div className="mt-6 space-y-1.5">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Role family — Coming soon
          </p>
          <p className="text-[10px] italic text-muted-foreground/70">
            Playbook authoring in progress
          </p>
        </div>
        <p className="text-[11px] text-muted-foreground">
          Visible so the roadmap is clear — these can't route end-to-end yet. v0.6 ships playbooks
          for the rest;{" "}
          <Link to="/" className="underline-offset-2 hover:underline">
            request a family
          </Link>{" "}
          via the inbox to bump priority.
        </p>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {LENS_PLACEHOLDERS.map((p) => (
            <div
              key={p.id}
              title="Coming in v0.6 — pick an Active option above for now"
              className="flex items-start gap-3 rounded-lg border border-dashed border-border bg-card/40 px-3 py-2.5 opacity-70"
            >
              <span
                className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-border text-muted-foreground"
                aria-hidden
              >
                <span className="h-1 w-1 rounded-full bg-muted-foreground/60" />
              </span>
              <div className="flex-1">
                <span className="block text-sm font-medium text-foreground/85">
                  {p.label_en}
                </span>
                <span className="block text-xs text-muted-foreground">{p.description_en}</span>
              </div>
              <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                soon
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Master kind */}
      <div className="mt-6 space-y-1.5">
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          About your upload <span className="text-muted-foreground/70">(optional)</span>
        </p>
        <p className="text-xs text-muted-foreground">
          我上传的简历是:
        </p>
        <div className="mt-1 space-y-2">
          {(
            [
              {
                value: "full" as MasterKind,
                label: "我的全量简历(还没为某个具体岗位改过)",
              },
              {
                value: "tailored_for_lens" as MasterKind,
                label: "之前为某个方向投递过的版本",
              },
            ]
          ).map((opt) => (
            <label
              key={opt.value}
              className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 cursor-pointer transition ${
                masterKind === opt.value
                  ? "border-primary bg-primary/5"
                  : "border-border bg-card hover:border-foreground/20"
              }`}
            >
              <input
                type="radio"
                name="master-kind"
                value={opt.value}
                checked={masterKind === opt.value}
                onChange={() => setMasterKind(opt.value)}
                className="h-3.5 w-3.5 accent-[var(--primary)]"
              />
              <span className="text-sm text-foreground">{opt.label}</span>
            </label>
          ))}
        </div>
      </div>

      {errMsg ? (
        <p className="mt-4 rounded-md border border-error/30 bg-error/5 px-3 py-2 text-xs text-error">
          {errMsg}
        </p>
      ) : null}

      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-xs text-muted-foreground transition hover:text-foreground"
        >
          ← Back
        </button>
        <button
          onClick={submit}
          disabled={!canContinue}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-xs font-medium text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="step2-continue"
        >
          {setLensTargetsMut.isPending ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Saving…
            </>
          ) : (
            <>
              Continue
              <ArrowRight className="h-3.5 w-3.5" />
            </>
          )}
        </button>
      </div>
    </section>
  );
}

/* ----------------- Step 3 — Master generation ----------------- */

interface Step3Props {
  chosenLenses: Lens[];
  primary: Lens | null;
  skipGeneration: boolean;
  setSkipGeneration: (v: boolean) => void;
  onContinue: () => void;
  onBack: () => void;
}

function Step3MasterGen({
  chosenLenses,
  primary,
  skipGeneration,
  setSkipGeneration,
  onContinue,
  onBack,
}: Step3Props) {
  const { data: masters } = useMasters(true);
  const generateMasterMut = useGenerateMaster();
  const [scheduled, setScheduled] = useState<Set<Lens>>(new Set());

  // Schedule generation for any chosen lens that's currently absent.
  // Fire-and-forget — backend returns immediately with status=scheduled and
  // the polling pulls the pill to `generating` then `ready`.
  useEffect(() => {
    if (!masters || chosenLenses.length === 0) return;
    for (const lens of chosenLenses) {
      const m = masters[lens];
      const status = m?.status ?? "absent";
      if (status === "absent" && !scheduled.has(lens)) {
        setScheduled((prev) => new Set(prev).add(lens));
        generateMasterMut.mutate(lens, {
          onError: (err) => {
            // Surface error but don't block the wizard — user can retry from Settings.
            toast.error(`Failed to schedule ${LENS_LABELS_ZH[lens]}: ${(err as Error).message}`);
          },
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [masters, chosenLenses.join(",")]);

  const readyCount = chosenLenses.filter(
    (l) => (masters?.[l]?.status ?? "absent") === "ready",
  ).length;
  const generatingCount = chosenLenses.filter(
    (l) => (masters?.[l]?.status ?? "absent") === "generating",
  ).length;
  const totalCount = chosenLenses.length;
  const allReady = totalCount > 0 && readyCount === totalCount;
  const anyInFlight = generatingCount > 0;
  const progressPct = totalCount > 0 ? Math.round((readyCount / totalCount) * 100) : 0;

  const canDone = allReady || skipGeneration;

  return (
    <section>
      <h2
        className="text-xl text-foreground"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        03 · Generating your masters…
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
        For each direction you picked, I rewrite your upload + experience bank into a tailored
        master. The primary direction goes first; secondaries queue behind it. Each takes 20–60s
        depending on how much LLM work it needs — feel free to leave the tab open.
      </p>

      {/* Global progress block — replaces the "is it stuck?" feeling. */}
      <div
        className="mt-6 rounded-xl border border-border/60 bg-card px-4 py-4"
        aria-live="polite"
        data-testid="masters-progress"
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {allReady ? (
              <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-verified/15 text-verified">
                <Check className="h-3.5 w-3.5" />
              </span>
            ) : anyInFlight ? (
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            ) : (
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-muted text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/60" />
              </span>
            )}
            <div className="flex flex-col">
              <span className="text-sm font-medium text-foreground">
                {allReady
                  ? "All masters ready"
                  : anyInFlight
                    ? `Generating — ${readyCount} of ${totalCount} ready`
                    : `Queued — ${readyCount} of ${totalCount} ready`}
              </span>
              <span className="text-xs text-muted-foreground">
                {allReady
                  ? "You can continue to the next step."
                  : "Primary first, then secondaries. ~30–60s each."}
              </span>
            </div>
          </div>
          <span className="font-mono text-xs text-muted-foreground tabular-nums">
            {readyCount}/{totalCount}
          </span>
        </div>
        {/* Animated progress bar. */}
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full bg-primary transition-[width] duration-500 ${
              anyInFlight && !allReady ? "animate-pulse" : ""
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      <ul className="mt-4 space-y-2" data-testid="masters-list">
        {chosenLenses.map((lens) => {
          const m = masters?.[lens];
          const status = m?.status ?? "absent";
          const isPrimary = lens === primary;
          const isGenerating = status === "generating";
          return (
            <li
              key={lens}
              className={`flex items-center justify-between gap-3 rounded-lg border bg-card px-3 py-2.5 transition ${
                isGenerating ? "border-primary/40 shadow-[0_0_0_3px_var(--primary)_5%]" : "border-border"
              }`}
              data-testid={`master-row-${lens}`}
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium text-foreground">
                  {LENS_LABELS_ZH[lens]}
                  {isPrimary ? (
                    <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      primary
                    </span>
                  ) : null}
                </span>
                <span className="text-xs text-muted-foreground">
                  {LENS_DESCRIPTIONS_EN[lens]}
                </span>
              </div>
              <MasterStatusPill status={status} />
            </li>
          );
        })}
      </ul>

      {chosenLenses.length === 0 ? (
        <p className="mt-4 text-xs text-muted-foreground italic">
          No directions picked yet — go back to Step 2.
        </p>
      ) : null}

      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-xs text-muted-foreground transition hover:text-foreground"
        >
          ← Back
        </button>
        <div className="flex items-center gap-3">
          {!allReady ? (
            <button
              onClick={() => {
                setSkipGeneration(true);
                onContinue();
              }}
              className="text-xs text-muted-foreground transition hover:text-foreground"
              data-testid="step3-skip"
            >
              Skip — generate later
            </button>
          ) : null}
          <button
            onClick={onContinue}
            disabled={!canDone}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-xs font-medium text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="step3-done"
          >
            Done
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </section>
  );
}

/* ----------------- Step 4 — Experiences ----------------- */

interface Step4Props {
  expCount: number;
  expScored: number;
  allScored: boolean;
  skipScoring: boolean;
  setSkipScoring: (v: boolean) => void;
  canContinue: boolean;
  onContinue: () => void;
  onBack: () => void;
}

function Step4Experiences({
  expCount,
  expScored,
  allScored,
  skipScoring,
  setSkipScoring,
  canContinue,
  onContinue,
  onBack,
}: Step4Props) {
  const { data: status } = useUserStatus();
  const items = status?.experiences ?? [];

  const scoringInProgress = expCount > 0 && !allScored && !skipScoring;

  // Track how long scoring has been in progress so we can flip from
  // "5-10s typical" copy to a stuck-warning when the LLM proxy is down
  // or otherwise slow. Resets when scoring starts (expCount > 0 first
  // time) or finishes (allScored).
  const [scoringStartedAt, setScoringStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState<number>(() => Date.now());
  useEffect(() => {
    if (scoringInProgress && scoringStartedAt === null) {
      setScoringStartedAt(Date.now());
    } else if (!scoringInProgress && scoringStartedAt !== null) {
      setScoringStartedAt(null);
    }
  }, [scoringInProgress, scoringStartedAt]);
  useEffect(() => {
    if (!scoringInProgress) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [scoringInProgress]);

  const elapsedSec = scoringStartedAt ? Math.floor((now - scoringStartedAt) / 1000) : 0;
  // Per-experience expected wall-clock: backend runs LLM calls sequentially
  // via FastAPI BackgroundTasks, each with a 60s timeout. So "stuck" kicks
  // in once we exceed ~30s × remaining without progress.
  const remaining = Math.max(expCount - expScored, 0);
  const isSlow = scoringInProgress && elapsedSec > Math.max(30, remaining * 15);
  const looksStuck = scoringInProgress && elapsedSec > Math.max(90, remaining * 45);

  return (
    <section>
      <h2
        className="text-xl text-foreground"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        04 · Add experiences
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
        Optional but recommended. Drop past role briefs, project write-ups, internship reports — the
        richer your bank, the better I can match relevant evidence to each JD. I auto-score each on
        industry recognition × lens fit × AI fluency.
      </p>

      <div className="mt-4">
        <ExperiencesUpload />
      </div>

      {items.length > 0 ? (
        <div className="mt-4 space-y-1.5">
          {items.map((it) => (
            <div
              key={it.id}
              className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2"
            >
              <span className="truncate font-mono text-xs text-foreground">{it.file_name}</span>
              <ScoringStatusPill status={it.scoring_status} />
            </div>
          ))}
        </div>
      ) : null}

      {scoringInProgress ? (
        <div
          className={`mt-4 rounded-md px-3 py-2.5 text-xs ${
            looksStuck
              ? "border border-attention/40 bg-attention/10 text-foreground"
              : isSlow
                ? "border border-border bg-muted/50 text-foreground"
                : "bg-muted/50 text-muted-foreground"
          }`}
          aria-live="polite"
        >
          <div className="flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
            <span className="font-medium">
              Scoring {expScored}/{expCount}
            </span>
            <span className="text-muted-foreground">· {elapsedSec}s elapsed</span>
          </div>
          {looksStuck ? (
            <p className="mt-1.5 leading-relaxed">
              <span className="font-medium">Scoring is taking longer than expected.</span> Usually
              5–10s per experience; the LLM may be unreachable or slow. You can continue without
              scoring — experiences will keep scoring in the background, and you can finish from
              Settings later.
            </p>
          ) : isSlow ? (
            <p className="mt-1 text-muted-foreground">
              Still working — usually 5–10s/experience but the LLM is taking longer. No need to
              wait; click below to continue.
            </p>
          ) : (
            <p className="mt-1 text-muted-foreground">
              Usually 5–10s per experience. Runs in the background — you don't have to wait.
            </p>
          )}
        </div>
      ) : null}

      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-xs text-muted-foreground transition hover:text-foreground"
        >
          ← Back
        </button>
        {scoringInProgress ? (
          // While scoring is in flight, swap the primary CTA to a Skip
          // action — the experiences keep scoring in the background after
          // setup, so blocking the user here adds zero value.
          <button
            onClick={() => {
              setSkipScoring(true);
              onContinue();
            }}
            className={`inline-flex h-10 items-center gap-2 rounded-lg px-4 text-xs font-medium transition ${
              looksStuck
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "border border-border bg-card text-foreground hover:border-foreground/30"
            }`}
            data-testid="step4-skip-and-continue"
          >
            {looksStuck ? "Continue anyway — scoring will finish in background" : "Continue without waiting"}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        ) : (
          <button
            onClick={onContinue}
            disabled={!canContinue}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-xs font-medium text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {expCount === 0 ? "Skip — I'll add experiences later" : "I'm ready"}
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </section>
  );
}

/* ----------------- Step 5 — Done ----------------- */

function Step5Done({ expCount, onGo }: { expCount: number; onGo: () => void }) {
  const summary = useMemo(() => {
    if (expCount === 0) return "Ready. You can always add experiences from /experiences later.";
    return `Ready. ${expCount} experience${expCount === 1 ? "" : "s"} scored and routed.`;
  }, [expCount]);

  return (
    <section className="text-center">
      <span className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-verified/10 text-verified">
        <Check className="h-5 w-5" />
      </span>
      <h2
        className="mt-4 text-xl text-foreground"
        style={{ fontFamily: "var(--font-serif)" }}
      >
        You're set up.
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{summary}</p>
      <button
        onClick={onGo}
        className="mt-6 inline-flex h-11 items-center gap-2 rounded-lg bg-foreground px-5 text-sm font-medium text-background transition hover:opacity-90"
      >
        Take me to my Inbox
        <ArrowRight className="h-4 w-4" />
      </button>
    </section>
  );
}
