import { Link, useLocation } from "@tanstack/react-router";
import {
  ChevronsLeft,
  Eye,
  FileText,
  Inbox,
  Library,
  PencilLine,
  Search,
  Settings as SettingsIcon,
  Wand2,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useRuns, useUserStatus } from "@/lib/queries";
import { PRODUCT_STATUS_META, productStatusForRun } from "@/components/inbox/status-meta";
import type { RunSummary } from "@/lib/api";
import { LlmHealthPill } from "@/components/LlmHealthPill";
import { UserCard } from "./UserCard";

interface NavItemSpec {
  to: "/" | "/resume" | "/experiences" | "/settings" | "/setup";
  label: string;
  Icon: typeof Inbox;
  // Right-side count / status pill — supplied at render time per item
  badge?: ReactNode;
}

interface Props {
  collapsed: boolean;
  onToggle: () => void;
  /** Optional drafts count from /api runs query — kept opt-in so the sidebar
   * can render even before the runs query has resolved. */
  draftsCount?: number;
  /** Override the user name shown in UserCard (used by /demo for persona). */
  overrideName?: string;
}

/**
 * Notion-style left sidebar. 240px expanded, 60px collapsed; sidebar state is
 * persisted by the AppShell (parent owns the `collapsed` flag).
 */
export function Sidebar({ collapsed, onToggle, draftsCount, overrideName }: Props) {
  const { data: status } = useUserStatus();
  const { data: runsData } = useRuns();
  const location = useLocation();

  const expCount = status?.experience_count ?? 0;
  const expScored = status?.experiences_scored_count ?? 0;
  const hasResume = status?.has_resume ?? false;
  const activeRuns = (runsData?.runs ?? []).filter((run) => {
    const state = run.lifecycle_state ?? "tailored";
    return state !== "archived" && state !== "dismissed";
  });
  const sidebarDraftsCount = draftsCount ?? activeRuns.length;
  const recentRuns = [...activeRuns]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, 3);
  const reviewCount = activeRuns.filter((run) => productStatusForRun(run) === "review_recommended").length;
  const rewriteCount = activeRuns.filter((run) => productStatusForRun(run) === "needs_deep_rewrite").length;
  const pendingCount = reviewCount + rewriteCount;

  const items: NavItemSpec[] = [
    {
      to: "/",
      label: "Inbox",
      Icon: Inbox,
      badge:
        sidebarDraftsCount > 0 ? (
          <CountPill count={sidebarDraftsCount} />
        ) : null,
    },
    {
      to: "/resume",
      label: "Master resume",
      Icon: FileText,
      badge: hasResume ? <StatusDot color="var(--verified)" title="Master uploaded" /> : <StatusDot color="var(--attention)" title="No resume yet" />,
    },
    {
      to: "/experiences",
      label: "Experiences",
      Icon: Library,
      badge: expCount > 0 ? (
        <ProgressPill scored={expScored} total={expCount} />
      ) : null,
    },
    { to: "/settings", label: "Settings", Icon: SettingsIcon },
  ];

  return (
    <aside
      className="flex h-screen flex-col border-r border-border bg-accent/40 transition-[width] duration-200"
      style={{ width: collapsed ? 60 : 260 }}
    >
      {/* Brand block */}
      <div className="flex items-center justify-between gap-2 px-3 pt-4 pb-2">
        {!collapsed ? (
          <Link
            to="/"
            className="text-sm font-medium tracking-tight text-foreground hover:text-foreground/80"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            Resume Tailor
          </Link>
        ) : (
          <div className="h-5 w-5 rounded bg-primary/15" aria-hidden />
        )}
        <button
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition hover:bg-accent hover:text-foreground"
        >
          <ChevronsLeft
            className={`h-4 w-4 transition-transform ${collapsed ? "rotate-180" : ""}`}
          />
        </button>
      </div>

      {!collapsed ? (
        <div className="px-3 pb-3">
          <button className="flex h-8 w-full items-center gap-2 rounded-md border border-border bg-card px-2.5 text-xs text-muted-foreground transition hover:border-foreground/15 hover:text-foreground">
            <Search className="h-3.5 w-3.5" />
            <span className="flex-1 text-left">Search runs, JDs…</span>
            <span className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">⌘K</span>
          </button>
        </div>
      ) : null}

      {/* Primary nav */}
      <nav className="px-2 py-1">
        <TooltipProvider delayDuration={200}>
          <ul className="space-y-0.5">
            {items.map((item) => (
              <li key={item.to}>
                <NavItem
                  to={item.to}
                  label={item.label}
                  Icon={item.Icon}
                  badge={item.badge}
                  collapsed={collapsed}
                  active={isActive(location.pathname, item.to)}
                />
              </li>
            ))}
          </ul>
        </TooltipProvider>
      </nav>

      {!collapsed ? (
        <div className="min-h-0 flex-1 px-3 pt-3">
          <div className="mb-2 flex items-center gap-2 text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <span>In flight</span>
            <span className="h-px flex-1 bg-border" />
            <span className="font-mono tracking-normal">{activeRuns.length}</span>
          </div>
          {recentRuns.length > 0 ? (
            <div className="space-y-1">
              {recentRuns.map((run) => (
                <MiniRun
                  key={run.run_id}
                  run={run}
                  color={PRODUCT_STATUS_META[productStatusForRun(run)].color}
                />
              ))}
            </div>
          ) : (
            <p className="px-2 text-xs text-muted-foreground">No active drafts</p>
          )}
        </div>
      ) : (
        <div className="flex-1" />
      )}

      {!collapsed ? (
        <div className="mx-2 mb-2 rounded-lg border border-border bg-card p-2.5">
          <div className="mb-1.5 flex items-baseline justify-between">
            <span className="text-[11px] font-medium text-foreground">Today's queue</span>
            <span className="text-[10px] text-muted-foreground">{pendingCount} pending</span>
          </div>
          <div className="space-y-1 text-[11px]">
            <QueueLine Icon={Eye} color="var(--attention)" label="Review recommended" count={reviewCount} />
            <QueueLine Icon={PencilLine} color="var(--error)" label="Needs deep rewrite" count={rewriteCount} />
          </div>
        </div>
      ) : null}

      {/* LLM health pill (hidden when healthy) */}
      <TooltipProvider delayDuration={200}>
        <LlmHealthPill collapsed={collapsed} />
      </TooltipProvider>

      {/* User card */}
      <div className="border-t border-border px-2 py-3">
        <TooltipProvider delayDuration={200}>
          <div className="mb-2">
            <NavItem
              to="/setup"
              label="Setup"
              Icon={Wand2}
              collapsed={collapsed}
              active={isActive(location.pathname, "/setup")}
            />
          </div>
        </TooltipProvider>
        <UserCard collapsed={collapsed} overrideName={overrideName} />
      </div>
    </aside>
  );
}

function isActive(pathname: string, to: NavItemSpec["to"]): boolean {
  if (to === "/") return pathname === "/";
  return pathname === to || pathname.startsWith(`${to}/`);
}

function NavItem({
  to,
  label,
  Icon,
  badge,
  collapsed,
  active,
}: {
  to: NavItemSpec["to"];
  label: string;
  Icon: typeof Inbox;
  badge?: ReactNode;
  collapsed: boolean;
  active: boolean;
}) {
  const link = (
    <Link
      to={to}
      className={`group relative flex h-9 items-center gap-2.5 rounded-md px-2 text-sm transition ${
        active
          ? "bg-card text-foreground shadow-[0_1px_0_rgba(0,0,0,0.02)]"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      }`}
    >
      {/* Active edge stripe */}
      {active ? (
        <span
          className="absolute -left-2 top-1.5 bottom-1.5 w-[3px] rounded-full bg-primary"
          aria-hidden
        />
      ) : null}
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed ? (
        <>
          <span className="flex-1 truncate">{label}</span>
          {badge ? <span className="shrink-0">{badge}</span> : null}
        </>
      ) : null}
    </Link>
  );

  if (!collapsed) return link;
  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right" className="text-xs">
        {label}
      </TooltipContent>
    </Tooltip>
  );
}

function MiniRun({ run, color }: { run: RunSummary; color: string }) {
  const title = [run.company_hint, run.role_title_hint].filter(Boolean).join(" · ") || "Untitled draft";

  return (
    <div className="flex h-7 items-center gap-2 rounded-md px-2 text-xs text-foreground transition hover:bg-accent">
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      <span className="truncate">{title}</span>
    </div>
  );
}

function QueueLine({
  Icon,
  color,
  label,
  count,
}: {
  Icon: LucideIcon;
  color: string;
  label: string;
  count: number;
}) {
  return (
    <div className="flex items-center gap-1.5 text-foreground">
      <Icon className="h-3 w-3" style={{ color }} />
      <span className="flex-1 truncate">{label}</span>
      <span className="font-mono text-[10px] text-muted-foreground">{count}</span>
    </div>
  );
}

function CountPill({ count }: { count: number }) {
  return (
    <span className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-muted px-1.5 text-[10px] font-medium text-muted-foreground">
      {count}
    </span>
  );
}

function ProgressPill({ scored, total }: { scored: number; total: number }) {
  const all = scored === total;
  return (
    <span
      className={`inline-flex h-5 items-center rounded-full px-1.5 text-[10px] font-medium ${
        all ? "bg-verified/10 text-verified" : "bg-attention/10 text-attention-foreground"
      }`}
      title={all ? "All scored" : `${scored}/${total} scored`}
    >
      {scored}/{total}
    </span>
  );
}

function StatusDot({ color, title }: { color: string; title: string }) {
  return (
    <span
      className="inline-block h-2 w-2 rounded-full"
      style={{ background: color }}
      title={title}
      aria-label={title}
    />
  );
}
