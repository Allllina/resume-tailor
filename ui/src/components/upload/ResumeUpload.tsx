import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useUploadResume } from "@/lib/queries";
import { ApiError } from "@/lib/api";
import { FileDropZone } from "./FileDropZone";

interface Props {
  onSuccess?: (info: { format: string; confidence: number }) => void;
  /** Called once the user has completed (or attempted) an upload — used by
   * the wizard to advance regardless of confidence (with confirmation dialog
   * when confidence is low). */
  onComplete?: () => void;
  compact?: boolean;
}

const RESUME_MAX_BYTES = 5 * 1024 * 1024; // 5MB — matches backend cap

/**
 * Single-file resume drop zone wired to useUploadResume(). Shows confidence
 * + warnings inline on success; toast on error. Caller handles routing.
 */
export function ResumeUpload({ onSuccess, onComplete, compact }: Props) {
  const upload = useUploadResume();
  const [warnings, setWarnings] = useState<string[]>([]);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [format, setFormat] = useState<string | null>(null);

  const handle = (files: File[]) => {
    const file = files[0];
    if (!file) return;
    if (file.size > RESUME_MAX_BYTES) {
      toast.error(`File too large (${(file.size / 1024 / 1024).toFixed(1)}MB > 5MB cap)`);
      return;
    }
    upload.mutate(file, {
      onSuccess: (resp) => {
        setConfidence(resp.confidence);
        setWarnings(resp.warnings ?? []);
        setFormat(resp.format);
        toast.success(`Resume uploaded (${resp.format} · confidence ${(resp.confidence * 100).toFixed(0)}%)`);
        onSuccess?.({ format: resp.format, confidence: resp.confidence });
        onComplete?.();
      },
      onError: (err) => {
        const msg = err instanceof ApiError ? (err.detail ?? err.message) : (err as Error).message;
        toast.error(msg);
      },
    });
  };

  return (
    <div className="space-y-3">
      <FileDropZone
        multiple={false}
        compact={compact}
        disabled={upload.isPending}
        maxBytes={RESUME_MAX_BYTES}
        onFiles={handle}
        hint={
          upload.isPending ? (
            <span className="inline-flex items-center gap-1.5">
              <Loader2 className="h-3 w-3 animate-spin" />
              Parsing & saving…
            </span>
          ) : (
            <>
              .md · .tex · .docx · .pdf — 5MB max
            </>
          )
        }
      />

      {confidence !== null && format ? (
        <div className="rounded-lg border border-border bg-card px-3 py-2.5 text-xs">
          <div className="flex items-center justify-between">
            <p className="text-foreground">
              <span className="font-mono">{format}</span> · parsed
            </p>
            <ConfidenceBar value={confidence} />
          </div>
          {confidence < 0.7 ? (
            <p className="mt-2 text-attention-foreground/80">
              {format === "pdf"
                ? "PDF extraction is approximate — please review the parsed content. You can replace the file later from /resume."
                : "Parser confidence is low — review before relying on this master."}
            </p>
          ) : null}
          {warnings.length > 0 ? (
            <ul className="mt-2 space-y-0.5 text-muted-foreground">
              {warnings.map((w, i) => (
                <li key={i}>• {w}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value));
  const color =
    pct >= 0.85 ? "var(--verified)" : pct >= 0.7 ? "var(--primary)" : "var(--attention)";
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="inline-block h-1.5 w-16 overflow-hidden rounded-full bg-muted"
        aria-label={`Confidence ${(pct * 100).toFixed(0)}%`}
      >
        <span
          className="block h-full rounded-full"
          style={{ width: `${pct * 100}%`, background: color }}
        />
      </span>
      <span className="font-mono text-[10px] text-muted-foreground">{(pct * 100).toFixed(0)}%</span>
    </span>
  );
}
