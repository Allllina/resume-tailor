import { useUserStatus } from "@/lib/queries";

interface Props {
  collapsed: boolean;
  overrideName?: string;
}

/**
 * Bottom-of-sidebar user identity. Shows candidate name + experience count
 * + has_resume status pip. Falls back to "Anonymous" when no profile exists
 * (fresh anonymous user before upload).
 */
export function UserCard({ collapsed, overrideName }: Props) {
  const { data, isLoading } = useUserStatus();

  if (isLoading && !data) {
    return collapsed ? <SkeletonAvatar /> : <SkeletonRow />;
  }

  const profile = data?.profile;
  const primaryName = overrideName ?? profile?.candidate_names?.[0] ?? "Anonymous";
  const initial = primaryName.charAt(0).toUpperCase();
  const expCount = data?.experience_count ?? 0;
  const expScored = data?.experiences_scored_count ?? 0;
  const hasResume = data?.has_resume ?? false;

  const subtitle = hasResume
    ? `${expCount} exp · ${expScored === expCount ? "✓ ready" : `${expScored}/${expCount} scored`}`
    : "no resume yet";

  if (collapsed) {
    return (
      <div className="flex h-9 items-center justify-center" title={`${primaryName} — ${subtitle}`}>
        <Avatar initial={initial} />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2.5 rounded-md px-1.5 py-1.5">
      <Avatar initial={initial} />
      <div className="min-w-0 flex-1">
        <p
          className="truncate text-xs font-medium text-foreground"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          {primaryName}
        </p>
        <p className="truncate text-[10px] leading-tight text-muted-foreground">{subtitle}</p>
      </div>
      <span
        className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ background: hasResume ? "var(--verified)" : "var(--attention)" }}
        aria-hidden
      />
    </div>
  );
}

function Avatar({ initial }: { initial: string }) {
  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[11px] font-medium text-primary">
      {initial || "?"}
    </span>
  );
}

function SkeletonAvatar() {
  return <div className="h-7 w-7 animate-pulse rounded-full bg-muted" />;
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-2.5 px-1.5 py-1.5">
      <div className="h-7 w-7 animate-pulse rounded-full bg-muted" />
      <div className="flex-1 space-y-1.5">
        <div className="h-2.5 w-20 animate-pulse rounded bg-muted" />
        <div className="h-2 w-16 animate-pulse rounded bg-muted" />
      </div>
    </div>
  );
}
