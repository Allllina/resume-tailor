import { createFileRoute, Outlet } from "@tanstack/react-router";
import { LangProvider } from "@/lib/lang-context";

export const Route = createFileRoute("/preview")({
  component: PreviewLayout,
});

function PreviewLayout() {
  return (
    <LangProvider value="zh">
      <Outlet />
    </LangProvider>
  );
}
