/**
 * DemoCardLoop
 * 10s loop showing the tailoring flow on /setup, in three beats:
 *   1.  JD text streams in (left)
 *   2.  DraftCard appears (right) with a typed first-person narration
 *   3.  Status pill cycles ◷ verify → ▸ ready → ✓ submitted
 */

const LOOP_MS = 10000;

export function DemoCardLoop() {
  return (
    <div
      className="relative mt-6 mb-10 overflow-hidden rounded-2xl border border-border bg-card"
      aria-hidden="true"
      style={
        {
          "--loop": `${LOOP_MS}ms`,
        } as React.CSSProperties
      }
    >
      <style>{LOOP_CSS}</style>

      <div className="grid grid-cols-[1fr_1.1fr] gap-0 min-h-[200px]">
        {/* Left — JD streaming in */}
        <div className="relative border-r border-border p-5">
          <p className="text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
            Job description
          </p>
          <p className="mt-2 text-[11px] font-mono text-muted-foreground">anker-aigc-content.txt</p>

          <p className="dcl-jd mt-4 text-xs leading-relaxed text-foreground/85">
            Anker AIGC 内容实习生 — 负责短视频脚本与图文内容的 AI 辅助生产，参与 prompt
            工程、模型评测与素材库建设…
          </p>
        </div>

        {/* Right — DraftCard appearing */}
        <div className="relative p-5">
          <div className="dcl-card rounded-xl border border-border bg-background p-4 pl-5 relative">
            <span
              className="dcl-rail absolute left-0 top-3 bottom-3 w-[3px] rounded-full"
              aria-hidden
            />

            <header className="flex items-baseline gap-2">
              <span className="dcl-icon text-sm leading-none" />
              <h3 className="text-[13px] font-medium text-foreground">Anker AIGC 内容实习生</h3>
              <span className="text-[10px] text-muted-foreground">· 深圳</span>
            </header>

            <p className="dcl-narration mt-2 text-[11px] leading-relaxed text-foreground/85" />
          </div>

          <p className="dcl-status mt-3 text-[10px] font-mono text-muted-foreground" />
        </div>
      </div>

      {/* Quiet caption (constant) */}
      <p className="border-t border-border bg-muted/40 px-5 py-2 text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
        Demo · loops every 10s
      </p>
    </div>
  );
}

const NARRATION = "I tailored this 2 min ago. C 产品运营 lens, 3 项目命中 AIGC. No issues found.";

const LOOP_CSS = `
@keyframes dcl-jd-stream {
  0%, 4%   { clip-path: inset(0 100% 0 0); }
  28%      { clip-path: inset(0 0 0 0); }
  92%      { clip-path: inset(0 0 0 0); }
  100%     { clip-path: inset(0 0 0 0); }
}
@keyframes dcl-card-rise {
  0%, 30%  { opacity: 0; transform: translateY(12px); }
  42%      { opacity: 1; transform: translateY(0); }
  100%     { opacity: 1; transform: translateY(0); }
}
@keyframes dcl-narration-type {
  0%, 42%  { width: 0; }
  72%      { width: 100%; }
  100%     { width: 100%; }
}
@keyframes dcl-rail-color {
  0%, 50%  { background: var(--attention); }   /* verify */
  60%, 78% { background: var(--verified); }    /* ready */
  86%, 100%{ background: var(--muted-foreground); } /* submitted */
}
@keyframes dcl-icon-content {
  0%, 50%  { content: "◷"; color: var(--attention); }
  60%, 78% { content: "▸"; color: var(--verified); }
  86%, 100%{ content: "✓"; color: var(--muted-foreground); }
}
@keyframes dcl-status-text {
  0%, 50%   { content: "◷ verify · checking 1 claim"; }
  60%, 78%  { content: "▸ ready · 3 changes proposed"; }
  86%, 100% { content: "✓ submitted · via 安克招聘 portal"; }
}

.dcl-jd {
  animation: dcl-jd-stream var(--loop) ease-out infinite;
}
.dcl-card {
  animation: dcl-card-rise var(--loop) ease-out infinite;
  box-shadow: 0 1px 0 rgba(0,0,0,0.02);
}
.dcl-narration::before {
  content: "${NARRATION}";
  display: inline-block;
  white-space: nowrap;
  overflow: hidden;
  width: 0;
  vertical-align: bottom;
  animation: dcl-narration-type var(--loop) steps(60, end) infinite;
}
.dcl-rail {
  animation: dcl-rail-color var(--loop) steps(1, end) infinite;
  background: var(--attention);
}
.dcl-icon::before {
  animation: dcl-icon-content var(--loop) steps(1, end) infinite;
  content: "◷";
  color: var(--attention);
}
.dcl-status::before {
  animation: dcl-status-text var(--loop) steps(1, end) infinite;
  content: "◷ verify · checking 1 claim";
}

@media (prefers-reduced-motion: reduce) {
  .dcl-jd, .dcl-card, .dcl-narration::before,
  .dcl-rail, .dcl-icon::before, .dcl-status::before {
    animation: none;
  }
  .dcl-narration::before { width: 100%; }
  .dcl-card { opacity: 1; transform: none; }
}
`;
