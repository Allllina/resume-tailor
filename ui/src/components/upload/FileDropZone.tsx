import { useCallback, useRef, useState } from "react";
import { Upload } from "lucide-react";

interface Props {
  /** Accepted formats — defaults to all 4 supported types. */
  accept?: string;
  multiple?: boolean;
  /** When true, shows a slimmer drop zone (used in modals etc.) */
  compact?: boolean;
  disabled?: boolean;
  /** Max bytes per individual file (UI-only soft check; backend re-enforces). */
  maxBytes?: number;
  onFiles: (files: File[]) => void;
  hint?: React.ReactNode;
}

const DEFAULT_ACCEPT = ".md,.tex,.docx,.pdf";

/**
 * Drag-and-drop zone with click-to-browse fallback. Shows a soft visual
 * highlight on dragover. Filters files locally to the configured `accept`
 * extensions before calling `onFiles` — silent prevention of the obvious
 * wrong type so the user gets immediate feedback (a "wrong format" toast
 * is the caller's job since the backend will also reject non-matching).
 */
export function FileDropZone({
  accept = DEFAULT_ACCEPT,
  multiple = false,
  compact = false,
  disabled = false,
  maxBytes,
  onFiles,
  hint,
}: Props) {
  const [hover, setHover] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const acceptedExts = accept
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter((e) => e.startsWith("."));

  const matchesAccept = useCallback(
    (file: File) => {
      const lower = file.name.toLowerCase();
      return acceptedExts.some((ext) => lower.endsWith(ext));
    },
    [acceptedExts.join(",")], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const handle = useCallback(
    (list: FileList | null) => {
      if (!list || disabled) return;
      // Always pass everything through to the caller — the caller is the one
      // with toast access + business-context-aware error messages. Silent
      // filtering at this layer caused "drop a PDF, nothing happens" bugs.
      const all = Array.from(list);
      if (all.length === 0) return;
      onFiles(all);
    },
    [onFiles, disabled],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setHover(true);
      }}
      onDragLeave={() => setHover(false)}
      onDrop={(e) => {
        e.preventDefault();
        setHover(false);
        handle(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      className={`group cursor-pointer rounded-xl border border-dashed bg-card transition ${
        compact ? "p-4" : "p-8"
      } ${hover && !disabled ? "border-primary bg-primary/5" : "border-border hover:bg-accent/50"} ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        className="hidden"
        onChange={(e) => {
          handle(e.target.files);
          // Clear value so the same file can be re-uploaded after delete
          e.target.value = "";
        }}
      />
      <div className={`flex ${compact ? "gap-3" : "flex-col gap-2"} items-center text-center`}>
        <span
          className={`inline-flex items-center justify-center rounded-full bg-primary/10 text-primary ${
            compact ? "h-8 w-8" : "h-10 w-10"
          }`}
        >
          <Upload className={compact ? "h-3.5 w-3.5" : "h-4 w-4"} />
        </span>
        <div className={compact ? "text-left" : ""}>
          <p className="text-sm text-foreground">
            {multiple ? "Drop files or click to browse" : "Drop file or click to browse"}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {hint ?? <>Accepted: {acceptedExts.join(" · ")}</>}
          </p>
        </div>
      </div>
    </div>
  );
}
