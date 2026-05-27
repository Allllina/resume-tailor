import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";

const COLLAPSED_KEY = "rt:sidebar-collapsed";

interface Props {
  children: React.ReactNode;
}

/**
 * Top-level workspace layout. Left: foldable sidebar (240px / 60px). Right:
 * main content (flex-1). Sidebar collapse state persists in localStorage so
 * power users keep the icon-only mode across sessions.
 *
 * Routes that need full-screen real estate (e.g. /setup wizard) should NOT
 * wrap in AppShell — see __root.tsx for the conditional rendering.
 */
export function AppShell({ children }: Props) {
  const [collapsed, setCollapsed] = useState(false);

  // Hydrate persisted state on mount (client-only; SSR initial render uses
  // the `false` default to keep server + client markup consistent).
  useEffect(() => {
    if (typeof localStorage === "undefined") return;
    const persisted = localStorage.getItem(COLLAPSED_KEY);
    if (persisted === "1") setCollapsed(true);
  }, []);

  const toggle = () => {
    setCollapsed((prev) => {
      const next = !prev;
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(COLLAPSED_KEY, next ? "1" : "0");
      }
      return next;
    });
  };

  return (
    <div className="flex min-h-screen bg-background bg-grain">
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <main className="relative flex-1 min-w-0">{children}</main>
    </div>
  );
}
