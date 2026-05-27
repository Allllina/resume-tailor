"""Prompt constants for harness.fit_diagnosis (pre_rewrite mode).

Mirrors the prompt style of harness.forecast.prompts: STRICT JSON
output, no Markdown fences, every required key present even if brief.

Spec reference: `packages/strategy-modules/fit-diagnosis-engine/
output-schema.md` Section 4 (matching_matrix + integrated_assessment +
optimization_boundary + optional multi_jd_coverage).

F3 will add a parallel _POST_REWRITE_* pair for Section 8 (HM + HRBP +
radar + improvement_suggestions).
"""

_PRE_REWRITE_SYSTEM_PROMPT = (
    "You are the fit-diagnosis-engine sub-skill running in pre_rewrite mode. "
    "Read a JD plus its already-extracted competency model and the candidate's "
    "experience selection trace, then emit a STRICT JSON object describing "
    "Section 4 of the output schema: a per-JD-requirement matching matrix "
    "(with bridging-or-closure plan), a 3-5 sentence integrated assessment, "
    "and the optimization boundary (what rewriting can vs cannot solve, with "
    "an explicit closure path). Output ONLY the JSON object — no prose, no "
    "Markdown fences. Every required key MUST be present even if brief. "
    "Do NOT fabricate experiences or evidence; if no candidate evidence exists "
    "for a requirement, the verdict is 'missing', not 'transferable'."
)


_PRE_REWRITE_USER_PROMPT_TEMPLATE = """Produce a Section 4 (pre_rewrite) JSON object for this run.

Target market: {target_market}
Primary lens: {lens}
Multi-JD mode: {multi_jd}

JD:
\"\"\"
{jd_text}
\"\"\"

Competency model — Section B (core hiring logic, ordered priorities):
{section_b}

Competency model — Section C (qualification model, tiered):
{section_c}

Experience selection trace (per-experience pass A/B/C tier + final_category 1-4):
{experience_trace}

Emit JSON with EXACTLY these top-level keys:

- matching_matrix: array of 6-12 items, each describing one JD core
  requirement drawn from Section B priorities and Section C tier 1/2/3
  must_have / strongly_preferred / nice_to_have items. Dedup by text.
  Each item is an object with EXACTLY these keys:
    {{
      "text": str,                          // requirement paraphrased from JD, 1 line
      "evidence": str,                      // 1-2 sentence justification grounded in
                                            //   the experience selection trace
      "verdict": "strong_match" | "transferable" | "missing",
      "source": "section_b_priority" | "section_c_tier_1"
              | "section_c_tier_2" | "section_c_tier_3",
      "bridging_or_closure": str            // see semantics below
    }}
  Verdict semantics:
    - strong_match: candidate has direct relevant experience + data backing
    - transferable: relevant experience exists but needs angle adjustment
    - missing: no corresponding experience on file
  bridging_or_closure semantics — required by spec:
    - verdict == strong_match  → empty string ""
    - verdict == transferable  → "<tier>; <one-sentence bridge plan>"
        e.g. "preferred; 面试侧重 Columbia + GPA 3.9 抵消专业差异"
        e.g. "hard; cover letter 确认时间窗口"
    - verdict == missing       → "<tier>; <closure horizon label>"
        where closure horizon label is one of:
          short_term | long_term | not_closeable
        e.g. "preferred; long_term"
    - <tier> in every non-empty case is one of: hard | preferred
      (hard surfaces hard-requirement risk in red; preferred is informational)

- integrated_assessment: 3-5 sentence string. Must explicitly cover
  biggest strength, biggest gap, and estimated pool position. Honest
  tone — no marketing language. If the candidate is a stretch, say so.

- optimization_boundary: object with EXACTLY two keys:
    {{
      "rewriting_can_solve":   [str, ...],
      "rewriting_cannot_solve":[str, ...]
    }}
  Format constraints:
    - Each item starts with a short label (≤ 8 chars), then ': ', then a
      one-line description.
    - Each cannot_solve item additionally ends with '; <closure path>'
      where closure path is one of: supplement | accept.
  Examples:
    can_solve:    "关键词显化: 行业研究 / 市场参与者等 4 个核心 keyword 注入 bullet 标题"
    cannot_solve: "无大厂战略 returner: 用 AI Agent 项目对冲差异化; accept"

{multi_jd_section}

Rules:
- Output STRICT JSON only, parsable by json.loads.
- All required top-level keys must exist.
- Keep total output under ~2000 tokens; prefer concise content over filler.
- DO NOT fabricate. Every matrix verdict must trace to evidence in the
  experience selection trace or competency model. No evidence → missing.
"""


_MULTI_JD_SECTION = """- multi_jd_coverage: array of one entry per JD in the multi-JD set.
  Each entry EXACTLY:
    {{
      "jd_id":        str,
      "jd_title":     str,
      "coverage_pct": int (0-100),
      "note":         str  // ≤ 50 chars; empty string when coverage is in expected range
    }}
"""


def render_pre_rewrite_user_prompt(
    *,
    target_market: str,
    lens: str,
    multi_jd: bool,
    jd_text: str,
    section_b: str,
    section_c: str,
    experience_trace: str,
) -> str:
    """Format the pre_rewrite user prompt.

    Hides the multi_jd_section conditional from the engine layer so
    `engine.build_diagnosis` doesn't need to know the prompt internals.
    """
    multi_jd_section = _MULTI_JD_SECTION if multi_jd else ""
    return _PRE_REWRITE_USER_PROMPT_TEMPLATE.format(
        target_market=target_market or "(unspecified)",
        lens=lens or "(unspecified)",
        multi_jd="true" if multi_jd else "false",
        jd_text=jd_text or "",
        section_b=section_b,
        section_c=section_c,
        experience_trace=experience_trace,
        multi_jd_section=multi_jd_section,
    )


# ----------------------------- post_rewrite (Wave 5 F3) -----------------------------

_POST_REWRITE_SYSTEM_PROMPT = (
    "You are the fit-diagnosis-engine sub-skill running in post_rewrite mode. "
    "Read a JD plus its already-extracted competency model, the candidate's "
    "experience selection trace, an optional D06 / pre_rewrite match-matrix "
    "summary, AND the candidate's CURRENT REWRITTEN resume body, then emit a "
    "STRICT JSON object describing Section 8 of the output schema: a Hiring "
    "Manager simulation (highlights / concerns / comparison risk), an HRBP "
    "simulation (keyword hit rate / hard filter match dict / advance decision "
    "/ rationale), an overall 5-level competitiveness rating, a 6-axis radar "
    "comparing resume vs JD with citations, and up to 5 prioritized improvement "
    "suggestions tagged by effort. Output ONLY the JSON object — no prose, no "
    "Markdown fences. Every required key MUST be present even if brief. "
    "Ground every assertion in the rewritten resume body provided; do NOT "
    "fabricate experiences or evidence."
)


_POST_REWRITE_USER_PROMPT_TEMPLATE = """Produce a Section 8 (post_rewrite) JSON object for this run.

Target market: {target_market}
Primary lens: {lens}

JD:
\"\"\"
{jd_text}
\"\"\"

Competency model — Section B (core hiring logic, ordered priorities):
{section_b}

Competency model — Section C (qualification model, tiered):
{section_c}

Experience selection trace (per-experience pass A/B/C tier + final_category 1-4):
{experience_trace}

Pre-rewrite match-matrix summary (Section 4 verdicts already computed —
use these to ground the HM/HRBP perspectives if available):
{match_matrix_summary}

CURRENT REWRITTEN RESUME (load-bearing — every HM/HRBP/radar assertion
MUST cite a section or bullet from this body):
\"\"\"
{current_resume}
\"\"\"

Emit JSON with EXACTLY these top-level keys:

- competitiveness_rating: one of "high" | "above_mid" | "mid"
  | "below_mid" | "low" — overall 5-level verdict.

- hm: Hiring Manager simulation. EXACTLY these keys:
    {{
      "highlights":      [str, ...],   // 1-3 short items — what would make
                                       //   them want to interview; each item
                                       //   should reference a specific resume
                                       //   bullet or section by short citation
                                       //   (e.g., "Acme 2.1" or "summary")
      "concerns":        [str, ...],   // 1-3 short items — capabilities not
                                       //   visible on resume; need probing
      "comparison_risk": str           // 1-2 sentences — if pool has someone
                                       //   with direct experience, where
                                       //   does this candidate lose
    }}

- hrbp: HRBP / recruiter screen simulation. EXACTLY these keys:
    {{
      "keyword_hit_rate":   float,     // 0.0-1.0; fraction of JD core
                                       //   keywords appearing in resume
      "hard_filter_match":  object,    // each value one of "match" |
                                       //   "mismatch" | "uncertain". Common
                                       //   keys: "degree", "language",
                                       //   "location", "timing"
      "advance_decision":   "push_direct" | "push_with_note" | "screen_out",
      "decision_rationale": str        // 1-2 sentences — why this decision
    }}

- radar: 6-axis dimension comparison. EXACTLY:
    {{
      "dimensions": [
        {{
          "name":          str,        // axis label (1-6 chars Chinese ideal)
          "resume_score":  int,        // 0-100, how strong the resume is
          "jd_required":   int,        // 0-100, how much the JD demands
          "citation":      str         // one-line evidence justifying
                                       //   resume_score (resume bullet or
                                       //   section ref); empty string only
                                       //   when no evidence available
        }},
        ...   // EXACTLY 6 items
      ]
    }}
  Typical axis set (adjust the 6th to a JD-specific axis when warranted):
    行业经验 / 核心技能 / 数据能力 / 沟通协作 / 文化匹配 / <JD-specific>

- improvement_suggestions: array of 0-5 items, ordered most actionable first.
  Each item EXACTLY:
    {{
      "text":   str,
      "effort": "wording" | "supplement_project" | "long_term"
    }}
  Effort semantics:
    - wording: rewording / structure / terminology — fixable in this run
    - supplement_project: needs adding / surfacing an existing project
    - long_term: skill or experience the candidate doesn't have yet

Rules:
- Output STRICT JSON only, parsable by json.loads.
- All five top-level keys must exist.
- radar.dimensions MUST contain exactly 6 entries; each entry includes
  a non-empty `citation` whenever evidence exists in the resume body.
- keyword_hit_rate MUST be a number in [0.0, 1.0].
- Each radar score MUST be an integer in [0, 100].
- Keep total output under ~2000 tokens; prefer concise content over filler.
- DO NOT fabricate. Every assertion must trace to the rewritten resume
  body or the experience selection trace.
"""


def render_post_rewrite_user_prompt(
    *,
    target_market: str,
    lens: str,
    jd_text: str,
    section_b: str,
    section_c: str,
    experience_trace: str,
    current_resume: str,
    match_matrix_summary: str,
) -> str:
    """Format the post_rewrite user prompt.

    Mirror of `render_pre_rewrite_user_prompt` style — hides template
    formatting from the engine layer. `match_matrix_summary` may be the
    string "(unavailable)" when no upstream Section 4 result is
    available; the LLM is expected to operate primarily off the resume
    body in that case.
    """
    return _POST_REWRITE_USER_PROMPT_TEMPLATE.format(
        target_market=target_market or "(unspecified)",
        lens=lens or "(unspecified)",
        jd_text=jd_text or "",
        section_b=section_b,
        section_c=section_c,
        experience_trace=experience_trace,
        current_resume=current_resume or "",
        match_matrix_summary=match_matrix_summary,
    )


__all__ = [
    "_PRE_REWRITE_SYSTEM_PROMPT",
    "_PRE_REWRITE_USER_PROMPT_TEMPLATE",
    "render_pre_rewrite_user_prompt",
    "_POST_REWRITE_SYSTEM_PROMPT",
    "_POST_REWRITE_USER_PROMPT_TEMPLATE",
    "render_post_rewrite_user_prompt",
]
