// F4 — Hand-rolled SVG radar chart for the fit_diagnosis_post_rewrite
// panel. Moved from `ui/src/components/dual-review/RadarChart.tsx`
// (which is being deleted) so it lives next to the panel that owns it.
//
// Renders two filled polygons (resume_score on top, jd_required
// underneath) over a 6-axis polar grid with concentric reference rings
// at 25/50/75/100. The new schema adds a per-dimension `citation`
// caption — the chart itself does NOT render the citation visually
// (that's the FitDiagnosisPostRewritePanel's job, see RadarSection).
// The shape is accepted defensively so the chart compiles + renders
// regardless of where citations end up surfacing.
//
// Constraints (preserved from D07.2 dispatch):
//   - No third-party chart lib (no recharts / visx / d3-*); package.json
//     intentionally not touched. Hand-rolled SVG only.
//   - Static — v1 has no interactivity, no tooltips. Visual scan only.
//   - Generated FitDiagnosisPostRewrite type only; no local redefinition.
//   - Accessible: role="img" + aria-label + <title>/<desc> + textual
//     fallback list inside <desc> for screen readers.
//
// Math: center (140, 140), inner radius 100, axis i angle starting at
// top and rotating clockwise -> -π/2 + i * (2π / total). Polygon vertex
// for score s: (cx + r * cos(angle) * s/100, cy + r * sin(angle) * s/100).
// Labels live at r * 1.15 so they sit just outside the outermost ring.
import type { FitDiagnosisPostRewrite } from "@/types/generated";

type Dimension = FitDiagnosisPostRewrite["radar"]["dimensions"][number];

interface RadarChartProps {
  dimensions: Dimension[];
}

// SVG geometry — chosen to fit a 280×280 viewport with comfortable
// padding for axis labels. Container scales via preserveAspectRatio.
const VIEW = 280;
const CX = 140;
const CY = 140;
const R = 100;
const RING_STEPS = [0.25, 0.5, 0.75, 1.0];

// Convert (axisIndex, score 0-100) → (x, y) in SVG space.
function pointFor(i: number, total: number, score: number): { x: number; y: number } {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / total;
  const clamped = Math.max(0, Math.min(100, score));
  return {
    x: CX + R * Math.cos(angle) * (clamped / 100),
    y: CY + R * Math.sin(angle) * (clamped / 100),
  };
}

// Axis tip (at score = 100) — used for the radial spokes and as anchor
// for the label placement (which sits at 1.15 × R, slightly outside).
function axisTip(i: number, total: number, factor = 1): { x: number; y: number } {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / total;
  return {
    x: CX + R * factor * Math.cos(angle),
    y: CY + R * factor * Math.sin(angle),
  };
}

function polygonPoints(dims: Dimension[], pick: (d: Dimension) => number): string {
  return dims
    .map((d, i) => {
      const p = pointFor(i, dims.length, pick(d));
      return `${p.x.toFixed(2)},${p.y.toFixed(2)}`;
    })
    .join(" ");
}

export function RadarChart({ dimensions }: RadarChartProps) {
  // Defensive: schema enforces exactly 6, but render gracefully if
  // backend ships fewer / more (e.g. a partial fallback row). Empty list
  // shows a stub so the page doesn't show a blank box.
  if (!dimensions || dimensions.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 bg-muted/20 px-4 py-6 text-center text-xs text-muted-foreground">
        暂无雷达数据
      </div>
    );
  }

  const resumePoints = polygonPoints(dimensions, (d) => d.resume_score);
  const jdPoints = polygonPoints(dimensions, (d) => d.jd_required);

  // Textual fallback for screen readers — one bullet per dimension.
  const ariaDesc = dimensions
    .map(
      (d) =>
        `${d.name}: 简历 ${Math.round(d.resume_score)} / 岗位 ${Math.round(d.jd_required)}`,
    )
    .join("; ");

  return (
    <div className="flex flex-col items-center gap-3">
      <svg
        viewBox={`0 0 ${VIEW} ${VIEW}`}
        className="w-full max-w-[320px] h-auto"
        role="img"
        aria-label="6-axis radar — resume vs JD required"
      >
        <title>6 维能力雷达 · Resume vs JD required</title>
        <desc>{ariaDesc}</desc>

        {/* Reference rings — concentric polygons at 25/50/75/100. Drawn as
            polygons (not circles) so they share the polygon's vertex count
            and the chart reads as a true polar grid rather than a target. */}
        {RING_STEPS.map((step) => {
          const pts = dimensions
            .map((_, i) => {
              const p = axisTip(i, dimensions.length, step);
              return `${p.x.toFixed(2)},${p.y.toFixed(2)}`;
            })
            .join(" ");
          return (
            <polygon
              key={step}
              points={pts}
              fill="none"
              stroke="currentColor"
              strokeWidth={0.6}
              className="text-muted-foreground/30"
            />
          );
        })}

        {/* Radial axis spokes — one per dimension, full radius. */}
        {dimensions.map((_, i) => {
          const tip = axisTip(i, dimensions.length, 1);
          return (
            <line
              key={`spoke-${i}`}
              x1={CX}
              y1={CY}
              x2={tip.x}
              y2={tip.y}
              stroke="currentColor"
              strokeWidth={0.6}
              className="text-muted-foreground/30"
            />
          );
        })}

        {/* JD required polygon — drawn first so it sits underneath the
            resume layer. Muted neutral fill so it reads as "the bar". */}
        <polygon
          points={jdPoints}
          fill="rgb(148 163 184 / 0.25)"
          stroke="rgb(100 116 139 / 0.7)"
          strokeWidth={1.2}
          strokeLinejoin="round"
        />

        {/* Resume score polygon — emerald, sits on top of the JD layer.
            Uses raw rgb() with alpha because Tailwind utility classes
            don't reliably apply to SVG fill primitives across themes. */}
        <polygon
          points={resumePoints}
          fill="rgb(16 185 129 / 0.35)"
          stroke="rgb(16 185 129 / 0.95)"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />

        {/* Axis labels — placed at 1.15 × R, anchored by quadrant so
            text doesn't collide with the polygon edge. */}
        {dimensions.map((d, i) => {
          const labelPos = axisTip(i, dimensions.length, 1.15);
          // Anchor by horizontal position relative to center.
          const dx = labelPos.x - CX;
          const anchor = Math.abs(dx) < 1 ? "middle" : dx > 0 ? "start" : "end";
          // Slight vertical nudge so labels don't sit exactly on the spoke tip.
          const dy = labelPos.y < CY ? -2 : labelPos.y > CY ? 10 : 4;
          return (
            <text
              key={`label-${i}`}
              x={labelPos.x}
              y={labelPos.y + dy}
              textAnchor={anchor}
              className="fill-foreground/80"
              style={{ fontSize: "10px", fontFamily: "var(--font-mono, monospace)" }}
            >
              {d.name}
            </text>
          );
        })}
      </svg>

      {/* Inline legend — small key for the two polygons. */}
      <div className="flex items-center gap-4 font-mono text-[10px] text-muted-foreground">
        <span className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-2 w-2 rounded-sm"
            style={{ background: "rgb(16 185 129 / 0.85)" }}
          />
          简历得分 · resume score
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block h-2 w-2 rounded-sm"
            style={{ background: "rgb(100 116 139 / 0.7)" }}
          />
          岗位要求 · JD required
        </span>
      </div>
    </div>
  );
}
