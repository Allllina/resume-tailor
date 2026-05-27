"""Read stage — Token transformation pipeline (Wave 1 minimal).

Per HARNESS_DESIGN.md §3.1 (Read) and §9 (Token transformation pipeline).
Wave 1 implements stages 1 (gather) + 4 (budget) only; full 5-stage
pipeline (relevance ranking + compression + template assembly) lands
Wave 2 when first context-overflow case surfaces.

For Tier 1 Light Tailoring (Skills row reorder + label/summary rewrite),
the minimal context is sufficient — Tier 1 doesn't read raw experience
files, only their index.json metadata.
"""
from typing import Any


def _score_value(cell: Any) -> str | None:
    """Extract score from a recognition/fit cell which may be dict or string."""
    if cell is None:
        return None
    if isinstance(cell, dict):
        return cell.get("score")
    if isinstance(cell, str):
        return cell
    return None


def assemble_tier1_context(
    jd_text: str,
    master_tex: str,
    index_slice: dict,
    target_industry: str,
    target_lens: str,
    token_budget: int = 8_000,
) -> dict:
    """Assemble structured context for Tier 1 transforms.

    Returns dict with keys:
      jd_text, master_tex, relevant_experiences, target_industry,
      target_lens, token_budget.

    relevant_experiences: experiences with non-null recognition[target_industry]
    OR non-null vertical_fit[target_lens]. Each item is a small summary
    {id, company, recognition, fit} (no raw bullets).
    """
    relevant: list[dict] = []
    for exp in index_slice.get("experiences", []) or []:
        rec_cell = (exp.get("recognition_per_industry") or {}).get(target_industry)
        fit_cell = (exp.get("vertical_fit_per_lens") or {}).get(target_lens)

        rec_score = _score_value(rec_cell)
        fit_score = _score_value(fit_cell)

        if rec_score is None and fit_score is None:
            continue

        relevant.append({
            "id": exp.get("id", ""),
            "company": exp.get("company", ""),
            "recognition": rec_score,
            "fit": fit_score,
        })

    return {
        "jd_text": jd_text,
        "master_tex": master_tex,
        "relevant_experiences": relevant,
        "target_industry": target_industry,
        "target_lens": target_lens,
        "token_budget": token_budget,
    }
