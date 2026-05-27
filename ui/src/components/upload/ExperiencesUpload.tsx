import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useUploadExperiences } from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { FileDropZone } from "./FileDropZone";

interface Props {
  /** Called after a successful upload. The mutation already invalidates
   * userStatus so the page list will refresh. */
  onUploaded?: (count: number) => void;
  compact?: boolean;
}

const EXP_MAX_BYTES = 2 * 1024 * 1024; // 2MB — matches backend cap

/**
 * Multi-file experiences drop zone. Auto-scoring runs in the background
 * on the server; the page that hosts this component is responsible for
 * polling via useUserStatus's dynamic refetchInterval.
 */
export function ExperiencesUpload({ onUploaded, compact }: Props) {
  const upload = useUploadExperiences();

  const handle = (files: File[]) => {
    if (files.length === 0) return;
    const oversized = files.filter((f) => f.size > EXP_MAX_BYTES);
    if (oversized.length > 0) {
      toast.error(`Skipped ${oversized.length} file(s) over 2MB`);
    }
    const valid = files.filter((f) => f.size <= EXP_MAX_BYTES);
    if (valid.length === 0) return;

    upload.mutate(valid, {
      onSuccess: (resp) => {
        toast.success(`Uploaded ${resp.experiences.length} experience(s) — scoring in background`);
        onUploaded?.(resp.experiences.length);
      },
      onError: (err) => {
        const msg = err instanceof ApiError ? (err.detail ?? err.message) : (err as Error).message;
        toast.error(msg);
      },
    });
  };

  return (
    <FileDropZone
      multiple
      compact={compact}
      disabled={upload.isPending}
      maxBytes={EXP_MAX_BYTES}
      onFiles={handle}
      hint={
        upload.isPending ? (
          <span className="inline-flex items-center gap-1.5">
            <Loader2 className="h-3 w-3 animate-spin" />
            Uploading & queuing for scoring…
          </span>
        ) : (
          <>
            .md · .tex · .docx · .pdf — 2MB each, up to 30 at once
          </>
        )
      }
    />
  );
}
