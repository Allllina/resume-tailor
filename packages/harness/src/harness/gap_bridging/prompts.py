"""Prompt constants for harness.gap_bridging."""

_SYSTEM_PROMPT = (
    "You are the gap-bridging-planner sub-skill. Convert pre-rewrite "
    "fit-diagnosis gaps into a STRICT JSON planning object for Step 5a "
    "Reframe, Step 5b Add, and Step 5c skill-gap plus structural advice. "
    "Output ONLY the JSON object -- no prose, no Markdown fences. Every "
    "required key MUST be present. Do NOT rewrite resume bullets. Do NOT "
    "fabricate evidence or inflate skills; every reframe directive must cite "
    "source evidence."
)

_USER_PROMPT_TEMPLATE = """Produce a gap-bridging-planner JSON object for this run.

Target market: {target_market}
Application timeline: {application_timeline}

Fit diagnosis pre_rewrite payload:
{fit_diagnosis}

Competency profile:
{competency_profile}

Candidate assets:
{candidate_assets}

Emit JSON with EXACTLY these top-level keys:

- reframe_directives: array of objects:
  {{
    "matrix_row_id": str,
    "target_experience": str,
    "target_bullet_id": str,
    "keyword_to_inject": str,
    "framing_directive": str,
    "source_evidence": str
  }}

- add_suggestions: array of objects:
  {{
    "gap_label": str,
    "horizon": "short_term" | "mid_term" | "not_closeable",
    "action": "plan_now" | "defer" | "accept",
    "suggestion": str
  }}

- skill_bar_adjustments: object:
  {{
    "add_to_bar": [
      {{
        "skill": str,
        "tier": "A" | "B",
        "placement_row": "technical" | "ai" | "language" | "other",
        "rationale": str
      }}
    ],
    "remove_from_bar": [{{"skill": str, "reason": str}}],
    "do_not_add": [{{"skill": str, "reason": str}}]
  }}

- section_ordering: object:
  {{
    "experience_section_order": [str, ...],
    "experience_section_emphasis": [
      {{"exp_id": str, "bullet_count_recommendation": int, "rationale": str}}
    ],
    "missing_sections": [
      {{"section_name": str, "action": "add" | "acknowledge_absence", "rationale": str}}
    ]
  }}

- multi_jd_conflict: object:
  {{
    "conflicting_directives": [
      {{"jd_a": str, "jd_b": str, "conflict_summary": str}}
    ],
    "proposed_resolution": "master_with_jd_specific" | "branch_versions" | "accept_compromise",
    "rationale": str
  }}

Rules:
- Output STRICT JSON only, parsable by json.loads.
- Reframe directives require concrete source_evidence; no source means move it to add_suggestions.
- Derive add_suggestions.action from horizon and application_timeline.
- Tier C skills must appear only in do_not_add, never add_to_bar.
- Keep directives concise and grounded in the supplied inputs.
"""


def render_user_prompt(
    *,
    target_market: str,
    application_timeline: str,
    fit_diagnosis: str,
    competency_profile: str,
    candidate_assets: str,
) -> str:
    return _USER_PROMPT_TEMPLATE.format(
        target_market=target_market or "(unspecified)",
        application_timeline=application_timeline or "immediate",
        fit_diagnosis=fit_diagnosis,
        competency_profile=competency_profile,
        candidate_assets=candidate_assets,
    )


__all__ = ["_SYSTEM_PROMPT", "render_user_prompt"]
