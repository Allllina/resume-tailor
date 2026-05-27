import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw, Sparkles, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MasterStatusPill } from "@/components/master/MasterStatusPill";
import {
  useDeleteMaster,
  useDeleteUser,
  useGenerateMaster,
  useMasters,
  usePatchUserProfile,
  useSetLensTargets,
  useUserStatus,
} from "@/lib/queries";
import { resetUserId } from "@/lib/user";
import {
  LENSES,
  LENS_LABELS_ZH,
  LENS_PLACEHOLDERS,
  type Lens,
  type TargetMarket,
} from "@/lib/api";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [{ title: "Settings — Resume Tailor" }],
  }),
  component: SettingsPage,
});

const MARKET_OPTIONS: { value: TargetMarket; label: string }[] = [
  { value: "mainland-china", label: "CN — Mainland China" },
  { value: "north-america", label: "US — North America" },
  { value: "hong-kong", label: "HK — Hong Kong" },
];

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso.slice(0, 10);
  }
}

function SettingsPage() {
  const { data: status, isLoading } = useUserStatus();
  const profile = status?.profile;
  const patch = usePatchUserProfile();
  const del = useDeleteUser();
  const navigate = useNavigate();

  const [names, setNames] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [market, setMarket] = useState<TargetMarket>("mainland-china");
  const [confirmClear, setConfirmClear] = useState(false);

  // Sync local state with fetched profile
  useEffect(() => {
    if (!profile) return;
    setNames(profile.candidate_names ?? []);
    if (profile.target_market_default) setMarket(profile.target_market_default);
  }, [profile?.candidate_names, profile?.target_market_default]);

  const dirty =
    JSON.stringify(names) !== JSON.stringify(profile?.candidate_names ?? []) ||
    market !== (profile?.target_market_default ?? "mainland-china");

  const save = () => {
    patch.mutate(
      { candidate_names: names, target_market_default: market },
      {
        onSuccess: () => toast.success("Settings saved"),
        onError: (err) => toast.error((err as Error).message),
      },
    );
  };

  const addName = () => {
    const v = draft.trim();
    if (!v) return;
    if (!names.includes(v)) setNames((p) => [...p, v]);
    setDraft("");
  };

  const removeName = (n: string) => setNames((p) => p.filter((x) => x !== n));

  const clearAll = () => {
    del.mutate(undefined, {
      onSuccess: () => {
        // Wipe local user_id so the next /api/users/me hits a fresh user dir
        resetUserId();
        toast.success("All your data was deleted. Starting fresh.");
        setConfirmClear(false);
        navigate({ to: "/setup" });
      },
      onError: (err) => toast.error((err as Error).message),
    });
  };

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <header>
        <h1
          className="text-3xl text-foreground"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          Settings
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Profile + targeting defaults. Local-first — nothing leaves your machine without an LLM call.
        </p>
      </header>

      {isLoading && !profile ? (
        <div className="mt-8 h-32 animate-pulse rounded-xl bg-card/50" />
      ) : (
        <div className="mt-8 space-y-6">
          {/* Candidate names */}
          <Section
            label="Candidate names"
            help="Used by the PII filter so I don't redact your own name in the resume."
          >
            <ul className="mb-2 space-y-1.5">
              {names.length === 0 ? (
                <li className="text-xs text-muted-foreground">No names yet.</li>
              ) : (
                names.map((n) => (
                  <li
                    key={n}
                    className="flex items-center justify-between gap-3 rounded-md border border-border bg-card px-3 py-2"
                  >
                    <span className="text-sm text-foreground">{n}</span>
                    <button
                      onClick={() => removeName(n)}
                      className="text-muted-foreground transition hover:text-error"
                      aria-label={`Remove ${n}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))
              )}
            </ul>
            <div className="flex gap-2">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addName();
                  }
                }}
                placeholder="Alina"
                className="h-9 flex-1 rounded-md border border-border bg-card px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring/40"
              />
              <button
                onClick={addName}
                className="h-9 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
              >
                Add
              </button>
            </div>
          </Section>

          {/* Target market */}
          <Section
            label="Target market default"
            help="Applied as the default when you paste a JD. You can override per-run."
          >
            <Select value={market} onValueChange={(v) => setMarket(v as TargetMarket)}>
              <SelectTrigger className="h-10 w-full bg-card">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MARKET_OPTIONS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Section>

          {/* Save button */}
          <div className="flex items-center gap-3">
            <button
              onClick={save}
              disabled={!dirty || patch.isPending}
              className="h-10 rounded-md bg-foreground px-4 text-sm font-medium text-background transition hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {patch.isPending ? "Saving…" : dirty ? "Save changes" : "Saved"}
            </button>
            {dirty ? (
              <span className="text-xs text-muted-foreground">Unsaved changes</span>
            ) : null}
          </div>

          {/* Target Directions */}
          <TargetDirectionsSection />

          {/* Per-Direction Masters */}
          <PerDirectionMastersSection />

          {/* User ID */}
          <Section
            label="User ID"
            help="Stored in your browser localStorage. Used for support / debugging."
          >
            <code className="block rounded-md border border-border bg-muted/40 px-3 py-2 font-mono text-xs text-foreground/80">
              {status?.user_id}
            </code>
          </Section>

          {/* Danger zone */}
          <div className="mt-10 rounded-xl border border-error/30 bg-error/5 px-4 py-4">
            <h3 className="text-sm font-medium text-foreground">Danger zone</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Wipe everything: your master, experience bank, profile, and tailoring runs. This cannot be undone.
            </p>
            <button
              onClick={() => setConfirmClear(true)}
              className="mt-3 inline-flex h-9 items-center gap-1.5 rounded-md border border-error/40 bg-card px-3 text-xs font-medium text-error transition hover:bg-error/10"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear my data
            </button>
          </div>
        </div>
      )}

      <AlertDialog open={confirmClear} onOpenChange={setConfirmClear}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Clear all your data?</AlertDialogTitle>
            <AlertDialogDescription>
              Master resume, experience bank, profile, and tailoring runs will be permanently deleted. You'll start over from /setup.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={clearAll}
              className="bg-error text-error-foreground hover:bg-error/90"
            >
              {del.isPending ? "Deleting…" : "Yes, delete everything"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function Section({
  label,
  help,
  children,
}: {
  label: string;
  help: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-sm font-medium text-foreground">{label}</h2>
      <p className="mt-0.5 text-xs text-muted-foreground">{help}</p>
      <div className="mt-2.5">{children}</div>
    </section>
  );
}

/* ============= Target Directions ============= */

function TargetDirectionsSection() {
  const { data: status } = useUserStatus();
  const setLensTargetsMut = useSetLensTargets();
  const profile = status?.profile;

  const primary = profile?.target_lens_default ?? null;
  const secondary = profile?.target_lens_secondary ?? [];

  const [editing, setEditing] = useState<null | { primary: Lens | null; secondary: Lens[] }>(null);

  const startEdit = () => setEditing({ primary, secondary: [...secondary] });
  const cancelEdit = () => setEditing(null);

  const saveEdit = () => {
    if (!editing?.primary) {
      toast.error("Pick a primary direction.");
      return;
    }
    setLensTargetsMut.mutate(
      {
        primary: editing.primary,
        secondary: editing.secondary.filter((l) => l !== editing.primary),
      },
      {
        onSuccess: () => {
          toast.success("Target directions saved.");
          setEditing(null);
        },
        onError: (err) => toast.error((err as Error).message),
      },
    );
  };

  return (
    <Section
      label="Target directions"
      help="Primary direction picks the default master for every JD. Secondaries get masters too — used when the JD's lens routing prefers them."
    >
      {!editing ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap" data-testid="target-directions-display">
            <span className="text-xs text-muted-foreground">Primary:</span>
            {primary ? (
              <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                {LENS_LABELS_ZH[primary]}
              </span>
            ) : (
              <span className="text-xs italic text-muted-foreground">none</span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">Secondary:</span>
            {secondary.length === 0 ? (
              <span className="text-xs italic text-muted-foreground">none</span>
            ) : (
              secondary.map((l) => (
                <span
                  key={l}
                  className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-foreground/80"
                >
                  {LENS_LABELS_ZH[l]}
                </span>
              ))
            )}
          </div>
          <button
            onClick={startEdit}
            className="mt-2 inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
            data-testid="edit-directions"
          >
            <Plus className="h-3 w-3" />
            {primary ? "Change directions" : "Add direction"}
          </button>
        </div>
      ) : (
        <DirectionsEditor
          primary={editing.primary}
          secondary={editing.secondary}
          setPrimary={(p) => setEditing({ ...editing, primary: p })}
          setSecondary={(s) => setEditing({ ...editing, secondary: s })}
          onCancel={cancelEdit}
          onSave={saveEdit}
          saving={setLensTargetsMut.isPending}
        />
      )}
    </Section>
  );
}

function DirectionsEditor({
  primary,
  secondary,
  setPrimary,
  setSecondary,
  onCancel,
  onSave,
  saving,
}: {
  primary: Lens | null;
  secondary: Lens[];
  setPrimary: (l: Lens) => void;
  setSecondary: (next: Lens[]) => void;
  onCancel: () => void;
  onSave: () => void;
  saving: boolean;
}) {
  const addSecondary = () => {
    const available = LENSES.filter((l) => l !== primary && !secondary.includes(l));
    if (available.length > 0) setSecondary([...secondary, available[0]]);
  };

  const removeSecondary = (idx: number) => {
    setSecondary(secondary.filter((_, i) => i !== idx));
  };

  const updateSecondary = (idx: number, lens: Lens) => {
    const next = [...secondary];
    next[idx] = lens;
    setSecondary(next);
  };

  const availableForMore = LENSES.filter((l) => l !== primary && !secondary.includes(l));
  const canAddMore = secondary.length < 3 && availableForMore.length > 0;

  return (
    <div className="rounded-lg border border-border bg-card/50 px-3 py-3 space-y-3">
      {/* Primary */}
      <div>
        <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Primary direction
        </p>
        <Select value={primary ?? ""} onValueChange={(v) => setPrimary(v as Lens)}>
          <SelectTrigger className="h-9 text-sm">
            <SelectValue placeholder="Choose a primary direction…" />
          </SelectTrigger>
          <SelectContent>
            {LENSES.map((lens) => (
              <SelectItem key={lens} value={lens}>
                {LENS_LABELS_ZH[lens]}
              </SelectItem>
            ))}
            <div className="px-2 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground select-none">
              Coming soon
            </div>
            {LENS_PLACEHOLDERS.map((p) => (
              <SelectItem key={p.id} value={p.id} disabled>
                {p.label_en}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Secondary */}
      <div>
        <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Secondary directions (optional)
        </p>
        <div className="space-y-1.5">
          {secondary.map((lens, idx) => (
            <div key={idx} className="flex items-center gap-1.5">
              <div className="flex-1">
                <Select value={lens} onValueChange={(v) => updateSecondary(idx, v as Lens)}>
                  <SelectTrigger className="h-9 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LENSES.filter(
                      (l) => l !== primary && (!secondary.includes(l) || l === lens),
                    ).map((l) => (
                      <SelectItem key={l} value={l}>
                        {LENS_LABELS_ZH[l]}
                      </SelectItem>
                    ))}
                    <div className="px-2 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground select-none">
                      Coming soon
                    </div>
                    {LENS_PLACEHOLDERS.map((p) => (
                      <SelectItem key={p.id} value={p.id} disabled>
                        {p.label_en}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <button
                type="button"
                onClick={() => removeSecondary(idx)}
                aria-label="Remove this secondary direction"
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-card text-muted-foreground transition hover:border-foreground/20 hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
          {canAddMore ? (
            <button
              type="button"
              onClick={addSecondary}
              className="flex h-9 w-full items-center justify-center gap-1.5 rounded-md border border-dashed border-border text-xs text-muted-foreground transition hover:border-foreground/20 hover:text-foreground"
            >
              <Plus className="h-3.5 w-3.5" />
              Add secondary direction
            </button>
          ) : null}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onSave}
          disabled={saving || !primary}
          className="h-9 rounded-md bg-foreground px-3 text-xs font-medium text-background transition hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          onClick={onCancel}
          className="h-9 rounded-md border border-border bg-card px-3 text-xs font-medium transition hover:border-foreground/20"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/* ============= Per-Direction Masters ============= */

function PerDirectionMastersSection() {
  const { data: status } = useUserStatus();
  const profile = status?.profile;
  const primary = profile?.target_lens_default ?? null;
  const secondary = profile?.target_lens_secondary ?? [];

  const targetLenses = useMemo(() => {
    const all: Lens[] = [];
    if (primary) all.push(primary);
    for (const s of secondary) if (!all.includes(s)) all.push(s);
    return all;
  }, [primary, secondary]);

  const { data: masters } = useMasters(targetLenses.length > 0);
  const generate = useGenerateMaster();
  const del = useDeleteMaster();
  const [confirmDelete, setConfirmDelete] = useState<Lens | null>(null);

  if (targetLenses.length === 0) {
    return (
      <Section
        label="Per-direction masters"
        help="A tailored master.tex per direction. Each one is regenerable."
      >
        <p className="text-xs italic text-muted-foreground">
          Pick at least a primary direction first to manage masters.
        </p>
      </Section>
    );
  }

  return (
    <Section
      label="Per-direction masters"
      help="A tailored master.tex per direction. Each one is regenerable. Generation runs in the background; the pill updates as it progresses."
    >
      <ul className="space-y-2" data-testid="masters-table">
        {targetLenses.map((lens) => {
          const m = masters?.[lens];
          const status = m?.status ?? "absent";
          const isPrimary = lens === primary;
          const generatedAt = formatDate(m?.generated_at ?? null);
          const isGenerating = status === "generating";
          return (
            <li
              key={lens}
              className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2.5"
              data-testid={`master-row-${lens}`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-foreground">
                    {LENS_LABELS_ZH[lens]}
                  </span>
                  {isPrimary ? (
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      primary
                    </span>
                  ) : null}
                  <MasterStatusPill status={status} />
                </div>
                <p className="text-[11px] text-muted-foreground mt-0.5">
                  {status === "ready"
                    ? `generated ${generatedAt}${m?.method ? ` · ${m.method}` : ""}`
                    : status === "generating"
                      ? "running…"
                      : "no master yet — generate to create one"}
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                {status === "ready" ? (
                  <button
                    onClick={() =>
                      generate.mutate(lens, {
                        onSuccess: () => toast.success(`Regenerating ${LENS_LABELS_ZH[lens]}…`),
                        onError: (err) => toast.error((err as Error).message),
                      })
                    }
                    disabled={generate.isPending}
                    className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-card px-2.5 text-[11px] font-medium transition hover:border-foreground/20 disabled:opacity-50"
                    data-testid={`regenerate-${lens}`}
                  >
                    <RefreshCw className="h-3 w-3" />
                    Regenerate
                  </button>
                ) : status === "absent" ? (
                  <button
                    onClick={() =>
                      generate.mutate(lens, {
                        onSuccess: () => toast.success(`Generating ${LENS_LABELS_ZH[lens]}…`),
                        onError: (err) => toast.error((err as Error).message),
                      })
                    }
                    disabled={generate.isPending}
                    className="inline-flex h-8 items-center gap-1.5 rounded-md bg-primary px-2.5 text-[11px] font-medium text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
                    data-testid={`generate-${lens}`}
                  >
                    <Sparkles className="h-3 w-3" />
                    Generate
                  </button>
                ) : (
                  <span className="text-[11px] text-muted-foreground italic">—</span>
                )}
                {status === "ready" && !isGenerating ? (
                  <button
                    onClick={() => setConfirmDelete(lens)}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition hover:text-error"
                    aria-label={`Delete ${LENS_LABELS_ZH[lens]} master`}
                    data-testid={`delete-${lens}`}
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>

      <AlertDialog
        open={confirmDelete !== null}
        onOpenChange={(o) => !o && setConfirmDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete the {confirmDelete ? LENS_LABELS_ZH[confirmDelete] : ""} master?
            </AlertDialogTitle>
            <AlertDialogDescription>
              The next run for this direction will fall back to your single uploaded resume (or
              the project sample if none exists). You can regenerate at any time.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!confirmDelete) return;
                del.mutate(confirmDelete, {
                  onSuccess: () => {
                    toast.success(`Deleted ${LENS_LABELS_ZH[confirmDelete]} master`);
                    setConfirmDelete(null);
                  },
                  onError: (err) => toast.error((err as Error).message),
                });
              }}
              className="bg-error text-error-foreground hover:bg-error/90"
            >
              {del.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Section>
  );
}
