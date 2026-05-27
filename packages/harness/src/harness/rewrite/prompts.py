"""LLM prompt templates for the rewrite engine (Wave 4 D.2a).

One prompt per Cat 1 / Cat 2 experience. The orchestrator (`engine.py`)
calls the LLM once per experience and merges the per-experience JSON into
the 10-section RewriteOutput.

Hard rules (paraphrased from `packages/strategy-modules/resume-rewrite-engine/SKILL.md`):
    R-1: Truthfulness — every claim must be locatable in the raw markdown.
         No fabricated stats / titles / scopes.
    R-2: Single resume version per JD.
    R-3: Risk flags (Section J) are mandatory.
    R-4: Lens / scenario / market contexts are read-only.
    R-5: LaTeX rendering is downstream — output is plain text, no LaTeX
         commands.
    R-6: HC lens hard-sell positioning (not exercised in single-experience
         prompts here).
    R-7: Brand-recognition disambiguator — applied via the
         `disambiguator_parenthetical` field for Cat 1/2 only when
         pass_b_lift ∈ {mis_classification, pure_recognition}. NOT
         applied to Cat 3 backup lines (see selection_trace input).
    R-8: Disambiguator-aware selection — already enforced upstream by
         `harness.selection.three_pass`. The prompt just consumes the
         resulting trace.

Style rules:
    - No AI 标点 (— / → / ◇ etc). Use plain ASCII punctuation.
    - Bullet text follows the 6-element structure: Action / Context /
      Method / Contribution / Outcome / Scale (Cat 1: ≥4 elements;
      Cat 2: ≥3 elements).
    - Numbers, percentages, scope language must match the raw markdown.
"""
from __future__ import annotations


REWRITE_SYSTEM_PROMPT = (
    "You are a senior resume writer working under strict truthfulness rules. "
    "Every claim you write must be directly supported by the candidate's raw "
    "experience markdown. NEVER fabricate stats, titles, scope, dates, or "
    "outcomes. Output ONLY a JSON object — no Markdown fences, no prose. "
    "Avoid AI-style punctuation (em dashes, arrows, bullets); use plain "
    "ASCII (commas, periods, semicolons) only."
)


# Prompt sections kept compact to stay under ~5000 chars total.
_HARD_RULES_PARAPHRASE = (
    "Hard rules:\n"
    "1. Truthfulness: every fact in `claimed_facts` MUST appear (substring) in "
    "the raw markdown. Write each `claimed_facts` entry in the SAME language as "
    "the raw markdown (if the raw is Chinese, the claim must be Chinese), "
    "quoting the source phrasing so it is substring-traceable. Fabrication = "
    "automatic reject.\n"
    "2. Bullet structure: 4-6 elements (Action, Context, Method, Contribution, "
    "Outcome, Scale) for Cat 1; 3-4 elements for Cat 2.\n"
    "3. Length: 1.5-2.5 lines per Cat 1 bullet; 1-2 lines per Cat 2 bullet.\n"
    "4. No AI punctuation: no em dash (—), no en dash (–), no arrows (→), "
    "no decorative bullets. Use plain ASCII.\n"
    "5. Disambiguator parenthetical: include the exact `disambiguator_text` "
    "ONLY when `apply_disambiguator` is true. Set the field to null otherwise.\n"
    "6. Keywords: weave JD-aligned keywords naturally; do not stuff.\n"
    "7. No 'Responsible for' / 'Duties included'. Lead with action verbs.\n"
    "8. Quantification: only use numbers / percentages that are present in "
    "the raw markdown."
)


_OUTPUT_CONTRACT = (
    "Output a JSON object with EXACTLY these keys:\n"
    "  experience_id: string (echo the input id)\n"
    "  final_category: integer (echo final_category from input)\n"
    "  bullets: array of objects, each with:\n"
    "    id: string (e.g. \"<experience_id>-bullet-1\")\n"
    "    text: string (the rewritten bullet, plain text, no LaTeX)\n"
    "    claimed_facts: array of short factual claims that the bullet "
    "asserts. Each must be a string traceable to the raw markdown.\n"
    "  disambiguator_parenthetical: string OR null (set per rule 5 above)\n"
    "  decision_rationale: 1-sentence string explaining why this bullet "
    "set fits the role.\n"
    "Bullet count: Cat 1 → 2-4 bullets; Cat 2 → 1-2 bullets."
)


def build_user_prompt(
    experience_id: str,
    final_category: int,
    raw_markdown: str,
    jd_excerpt: str,
    primary_lens: str,
    pass_b_lift: str,
    disambiguator_text: str | None,
    competency_section_b: object,
    competency_section_h: object,
) -> str:
    """Build the per-experience LLM user prompt.

    `disambiguator_text` is the exact parenthetical to insert (e.g.
    "(头部汽车电子上市公司)") — provided by the caller after reading
    `experience.disambiguator_per_industry[target_industry].text`.
    `apply_disambiguator` is True ONLY when caller already determined
    the experience is Cat 1/2 with pass_b_lift in (mis_classification,
    pure_recognition). The prompt itself does not re-derive eligibility.
    """
    apply_disambiguator = bool(
        disambiguator_text
        and final_category in (1, 2)
        and pass_b_lift in ("mis_classification", "pure_recognition")
    )

    bullet_target = "2-4 bullets" if final_category == 1 else "1-2 bullets"

    # Truncate inputs aggressively to stay within ~5000 chars total.
    jd_block = (jd_excerpt or "")[:800]
    raw_block = (raw_markdown or "")[:3500]

    section_b_repr = _stringify_section(competency_section_b, max_chars=500)
    section_h_repr = _stringify_section(competency_section_h, max_chars=400)

    parts = [
        f"Experience id: {experience_id}",
        f"Final category: {final_category} (Cat 1 = lead+expand, Cat 2 = compress)",
        f"Bullet target: {bullet_target}",
        f"Primary lens: {primary_lens or '(unspecified)'}",
        "",
        "Disambiguator decision (applied at the merge step, not in bullet "
        "text — record only in `disambiguator_parenthetical`):",
        f"  apply_disambiguator: {str(apply_disambiguator).lower()}",
        f"  disambiguator_text: {disambiguator_text or 'null'}",
        f"  pass_b_lift: {pass_b_lift}",
        "",
        "Competency Section B (core hiring logic):",
        section_b_repr,
        "",
        "Competency Section H (resume strategy):",
        section_h_repr,
        "",
        "JD excerpt (truncated):",
        '"""',
        jd_block,
        '"""',
        "",
        "Candidate raw markdown for this experience (truncated):",
        '"""',
        raw_block,
        '"""',
        "",
        _HARD_RULES_PARAPHRASE,
        "",
        _OUTPUT_CONTRACT,
    ]
    return "\n".join(parts)


def _stringify_section(section: object, max_chars: int) -> str:
    """Best-effort dump of a competency section to a compact string.

    The caller may pass a list, dict, or string. We accept any of these
    shapes, render a short representation (JSON-ish), and truncate.
    """
    if section is None:
        return "(unavailable)"
    if isinstance(section, str):
        return section[:max_chars]
    try:
        import json as _json

        rendered = _json.dumps(section, ensure_ascii=False)
    except (TypeError, ValueError):
        rendered = str(section)
    if len(rendered) > max_chars:
        rendered = rendered[: max_chars - 1].rstrip() + "…"
    return rendered
