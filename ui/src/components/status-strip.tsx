interface Props {
  sources: number;
  drafts: number;
  lastScan?: string;
}

export function StatusStrip({ sources, drafts, lastScan }: Props) {
  const empty = drafts === 0;

  return (
    <div className="sticky top-0 z-20 border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto max-w-2xl h-8 px-6 flex items-center gap-3">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-verified opacity-60" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-verified" />
        </span>
        {empty ? (
          <p className="text-[11px] text-muted-foreground tracking-wide">
            <span className="text-foreground">I'm ready</span>
            <span className="mx-2 text-border">·</span>
            No JDs in queue yet
            <span className="mx-2 text-border">·</span>
            Drop one to start
          </p>
        ) : (
          <p className="text-[11px] text-muted-foreground tracking-wide">
            Watching <span className="text-foreground">{sources} sources</span>
            <span className="mx-2 text-border">·</span>
            <span className="text-foreground">{drafts} drafts</span> ready
            {lastScan ? (
              <>
                <span className="mx-2 text-border">·</span>
                Last scan <span className="text-foreground">{lastScan}</span> ago
              </>
            ) : null}
          </p>
        )}
      </div>
    </div>
  );
}
