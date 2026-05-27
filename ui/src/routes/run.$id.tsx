import { createFileRoute } from "@tanstack/react-router";
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
      {/* Back-to-Inbox lives in the DraftReview toolbar header — no separate
          header here (avoids a duplicate Inbox link). */}
      <DraftReview draftId={id} />

      <FloatingComposer />
    </>
  );
}
