import {
  Outlet,
  Link,
  createRootRoute,
  HeadContent,
  Scripts,
  useLocation,
} from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import appCss from "../styles.css?url";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

/**
 * Routes that render full-screen WITHOUT the AppShell (sidebar + main).
 * The setup wizard is a single-purpose flow; it should not show the
 * sidebar (the sidebar would imply the user already has a workspace).
 */
function shouldUseAppShell(pathname: string): boolean {
  return pathname !== "/setup" && !pathname.startsWith("/setup/") && pathname !== "/demo";
}

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl text-foreground">404</h1>
        <p className="mt-4 text-sm text-muted-foreground">Nothing here. The AI hasn't seen this page.</p>
        <Link to="/" className="mt-6 inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          Back to Inbox
        </Link>
      </div>
    </div>
  );
}

function RootBody() {
  const location = useLocation();
  const useShell = shouldUseAppShell(location.pathname);

  return (
    <>
      {useShell ? (
        <AppShell>
          <Outlet />
        </AppShell>
      ) : (
        <Outlet />
      )}
      {/* top-right keeps toasts away from the floating composer (bottom-right) */}
      <Toaster richColors closeButton position="top-right" />
    </>
  );
}

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Inbox · AI is working" },
      { name: "description", content: "AI tailors your applications. You review and ship." },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Serif+SC:wght@500;700&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: () => (
    <QueryClientProvider client={queryClient}>
      <RootBody />
    </QueryClientProvider>
  ),
  notFoundComponent: NotFoundComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}
