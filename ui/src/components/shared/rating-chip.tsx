// Shared RatingChip — surfaces the 5-tier `competitiveness_rating` enum
// that both fit_diagnosis_pre_rewrite (F1) and fit_diagnosis_post_rewrite
// (F3) emit. Single source of truth for the RATING_LABEL / RATING_EN /
// RATING_TONE vocabulary that previously lived inline in MatchMatrixPanel
// (now FitDiagnosisPreRewritePanel); both top-level trust panels render
// the same chip side-by-side.
//
// Sentiment-graded: emerald (high) → red (low). Mirrors the verdict-pill
// color convention so the page reads consistently top-to-bottom.
import type { FitDiagnosisPreRewrite } from "@/types/generated";
import { useLang } from "@/lib/lang-context";

type Rating = FitDiagnosisPreRewrite["competitiveness_rating"];

const RATING_LABEL_EN: Record<Rating, string> = {
  high: "High",
  above_mid: "Above mid",
  mid: "Mid",
  below_mid: "Below mid",
  low: "Low",
};

const RATING_LABEL_ZH: Record<Rating, string> = {
  high: "高",
  above_mid: "中偏高",
  mid: "中",
  below_mid: "中偏低",
  low: "低",
};

const RATING_EN: Record<Rating, string> = {
  high: "high",
  above_mid: "above mid",
  mid: "mid",
  below_mid: "below mid",
  low: "low",
};

const RATING_TONE: Record<Rating, string> = {
  high: "border-emerald-500/40 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  above_mid:
    "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  mid: "border-amber-500/30 bg-amber-500/15 text-amber-700 dark:text-amber-300",
  below_mid:
    "border-orange-500/30 bg-orange-500/15 text-orange-700 dark:text-orange-300",
  low: "border-red-500/40 bg-red-500/15 text-red-700 dark:text-red-300",
};

interface RatingChipProps {
  rating: Rating;
}

export function RatingChip({ rating }: RatingChipProps) {
  const lang = useLang();
  const label = lang === "zh" ? RATING_LABEL_ZH[rating] : RATING_LABEL_EN[rating];
  const chipLabel = lang === "zh" ? "竞争力" : "Fit";
  return (
    <span
      className={`ml-auto inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-[11px] ${RATING_TONE[rating]}`}
      aria-label={lang === "zh" ? `整体竞争力 ${label}` : `Competitiveness: ${label}`}
    >
      <span className="text-[10px] uppercase tracking-wider opacity-80">{chipLabel}</span>
      <span className="font-medium">{label}</span>
    </span>
  );
}
