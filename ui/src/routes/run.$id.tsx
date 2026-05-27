import { createFileRoute, Link } from "@tanstack/react-router";
import { DraftReview } from "@/components/draft-review";
import { FloatingComposer } from "@/components/floating-composer";

export const Route = createFileRoute("/run/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `Review draft · ${params.id} — Resume Tailor` },
      { name: "description", content: "Review AI changes before submit." },
    ],
  }),
  component: RunPage,
});

function RunPage() {
  const { id } = Route.useParams();

  return (
    <>
      <header className="mx-auto max-w-2xl px-6 pt-8 pb-4">
        <Link to="/" className="text-sm text-muted-foreground hover:text-foreground transition">
          ← Inbox
        </Link>
      </header>

      <DraftReview draftId={id} />

      <FloatingComposer />
    </>
  );
}
