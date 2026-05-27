"""Role competency extractor — Wave 4 Step B.

LLM-driven port of `packages/strategy-modules/role-competency-extractor`.

Goal: read JD text + primary lens, ask the LLM for a JSON object containing
the 9 sections specified in
`packages/strategy-modules/role-competency-extractor/output-schema.md`,
validate the shape, and return it. On any failure (LLM raise, malformed
JSON, missing sections) return a minimal "fallback_no_llm" model so the
PLANNING stage can keep moving.

Contract (returned dict):
    {
      "section_a_role_definition": str,
      "section_b_core_hiring_logic": list[dict | str],
      "section_c_qualification_model": {
          "tier_1_must_have": list[...],
          "tier_2_strongly_preferred": list[...],
          "tier_3_nice_to_have": list[...]
      },
      "section_d_keyword_architecture": {
          "tier_1_core_role": list[str],
          "tier_2_capability": list[str],
          "tier_3_tools_methods": list[str],
          "tier_4_action_verbs": list[str],
          "tier_5_semantic_equivalents": list[str]
      },
      "section_e_shared_patterns": str | dict,
      "section_f_hidden_screening": list[dict | str],
      "section_g_market_interpretation": str | dict,
      "section_h_strategy_implications": {
          "emphasize_most": str,
          "de_emphasize": str,
          "top_half_content": str,
          "natural_keyword_placement": str,
          "common_mistakes": list[str] | str
      },
      "section_i_limitations_confidence": {
          "summary": str,
          "confidence": "high" | "moderate" | "low"
      },
      "flat_summary": {
          "primary_lens": str,
          "confidence": "high" | "moderate" | "low",
          ...
      },
      "_method": "llm" | "llm_partial" | "fallback_no_llm"
    }

`_method` values:
    - "llm": full LLM-driven extraction with all required sections present.
    - "llm_partial": LLM ran but JSON was missing required sections; gaps
      filled with fallback values + degradation event emitted.
    - "fallback_no_llm": LLM unavailable / raised / returned malformed JSON;
      whole model is the placeholder fallback.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from harness.exceptions import SubSkillUnavailable
from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen


SECTION_KEYS: tuple[str, ...] = (
    "section_a_role_definition",
    "section_b_core_hiring_logic",
    "section_c_qualification_model",
    "section_d_keyword_architecture",
    "section_e_shared_patterns",
    "section_f_hidden_screening",
    "section_g_market_interpretation",
    "section_h_strategy_implications",
    "section_i_limitations_confidence",
)


_SYSTEM_PROMPT = (
    "You are a role-competency analyst. Read a JD and produce a 9-section "
    "structured competency model as STRICT JSON. Output ONLY the JSON object, "
    "no prose, no Markdown fences. Every section A-I must be present even if "
    "brief. Section I always includes a confidence rating in {high, moderate, low}."
)


_USER_PROMPT_TEMPLATE = """Analyze the following JD against the assigned primary lens and emit
a JSON object with the 9 sections below plus a flat_summary block.

Primary lens: {lens}
JD:
\"\"\"
{jd_text}
\"\"\"

Emit JSON with EXACTLY these top-level keys:

- section_a_role_definition: 3-5 sentence role briefing (string).
- section_b_core_hiring_logic: array of 4-6 items, ordered highest to lowest
  screening priority. Each item: {{
    "priority_name": str, "what_it_means": str, "why_it_matters": str,
    "credible_proof_signals": str
  }}.
- section_c_qualification_model: object with three arrays:
  tier_1_must_have, tier_2_strongly_preferred, tier_3_nice_to_have. Each
  array element: {{ "name": str, "practical_meaning": str, "credible_proof_signals": str }}.
- section_d_keyword_architecture: object with five string arrays
  (3-5 highest-value terms each, JD source language):
    tier_1_core_role, tier_2_capability, tier_3_tools_methods,
    tier_4_action_verbs, tier_5_semantic_equivalents.
- section_e_shared_patterns: object {{ "cross_company_consensus": str,
  "company_specific_variations": str }}. For single-JD analysis use
  "single-JD; cross-company patterns not derivable" in cross_company_consensus
  and leave company_specific_variations empty.
- section_f_hidden_screening: array of 3-5 items. Each: {{
    "criterion": str, "signal_in_jd": str, "implication": str
  }}.
- section_g_market_interpretation: object {{ "priorities": str,
  "experience_framing": str, "proof_signals": str, "resume_style": str,
  "cultural_conventions": str }}.
- section_h_strategy_implications: object {{ "emphasize_most": str,
  "de_emphasize": str, "top_half_content": str,
  "natural_keyword_placement": str, "common_mistakes": [str, ...] }}.
- section_i_limitations_confidence: object {{ "summary": str,
  "confidence": "high" | "moderate" | "low" }}.
- flat_summary: object {{ "primary_lens": str, "role_family": str,
  "target_market": str, "confidence": "high" | "moderate" | "low",
  "competency_tags": [str, ...], "evidence_requirements": [str, ...],
  "scoring_notes": str }}.

Rules:
- Output STRICT JSON only, parsable by json.loads.
- All 9 section keys must exist.
- Keep total output under ~3500 tokens; prefer concise content over filler.
"""


def _placeholder_value(key: str) -> Any:
    """Minimal valid content for a fallback section.

    Strings are intentionally neutral — `_method` is the source of truth
    for WHY the section is unavailable (the fallback model is also returned
    when llm is None or returned non-dict JSON, where "extraction failed"
    is misleading).
    """
    if key == "section_a_role_definition":
        return "Role definition unavailable."
    if key == "section_b_core_hiring_logic":
        return [
            {
                "priority_name": "Unknown",
                "what_it_means": "(unavailable)",
                "why_it_matters": "(unavailable)",
                "credible_proof_signals": "(unavailable)",
            }
        ]
    if key == "section_c_qualification_model":
        return {
            "tier_1_must_have": [],
            "tier_2_strongly_preferred": [],
            "tier_3_nice_to_have": [],
        }
    if key == "section_d_keyword_architecture":
        return {
            "tier_1_core_role": [],
            "tier_2_capability": [],
            "tier_3_tools_methods": [],
            "tier_4_action_verbs": [],
            "tier_5_semantic_equivalents": [],
        }
    if key == "section_e_shared_patterns":
        return {
            "cross_company_consensus": "single-JD; cross-company patterns not derivable",
            "company_specific_variations": "",
        }
    if key == "section_f_hidden_screening":
        return []
    if key == "section_g_market_interpretation":
        return {
            "priorities": "",
            "experience_framing": "",
            "proof_signals": "",
            "resume_style": "",
            "cultural_conventions": "",
        }
    if key == "section_h_strategy_implications":
        return {
            "emphasize_most": "",
            "de_emphasize": "",
            "top_half_content": "",
            "natural_keyword_placement": "",
            "common_mistakes": [],
        }
    if key == "section_i_limitations_confidence":
        return {
            "summary": "Competency model unavailable.",
            "confidence": "low",
        }
    return None


def _placeholder_flat_summary(lens: str) -> dict:
    return {
        "primary_lens": lens or "",
        "role_family": "",
        "target_market": "",
        "confidence": "low",
        "competency_tags": [],
        "evidence_requirements": [],
        "scoring_notes": "fallback model: competency extraction unavailable",
    }


def fallback_model(lens: str) -> dict:
    """Return the minimal valid 9-section model marked as fallback.

    Used when the LLM raises, returns malformed JSON, or returns content
    that is missing critical structure. The PLANNING stage should record
    a degradation_event when this is returned so callers can see why.
    """
    out: dict = {key: _placeholder_value(key) for key in SECTION_KEYS}
    out["flat_summary"] = _placeholder_flat_summary(lens)
    out["_method"] = "fallback_no_llm"
    return out


def _normalize_model(raw: dict, lens: str) -> tuple[dict, bool]:
    """Ensure every required section is present.

    Returns (model, was_complete). When `was_complete` is False, at least
    one required section was missing and was filled with a placeholder —
    callers should record a degradation event.
    """
    if not isinstance(raw, dict):
        return fallback_model(lens), False

    out: dict = {}
    was_complete = True
    for key in SECTION_KEYS:
        if key in raw and raw[key] not in (None, ""):
            out[key] = raw[key]
        else:
            out[key] = _placeholder_value(key)
            was_complete = False

    flat = raw.get("flat_summary")
    if isinstance(flat, dict) and flat:
        # WHY: confidence and primary_lens are both required semantic fields;
        # missing either flips was_complete so callers emit a degradation event.
        if "confidence" not in flat:
            flat["confidence"] = "low"
            was_complete = False
        if not flat.get("primary_lens"):
            flat["primary_lens"] = lens or ""
            was_complete = False
        out["flat_summary"] = flat
    else:
        out["flat_summary"] = _placeholder_flat_summary(lens)
        was_complete = False

    return out, was_complete


def _strip_json_fences(text: str) -> str:
    """Best-effort: pull a JSON object out of ```json ...``` fences if present."""
    s = text.strip()
    if s.startswith("```"):
        # remove leading fence line
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        # remove trailing fence
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


async def extract_competencies(jd_text: str, lens: str, llm: Any) -> dict:
    """Extract a 9-section competency model for the given JD + primary lens.

    Returns a dict containing all 9 section keys + `flat_summary` + a
    `_method` marker:
      - `"llm"` on full success;
      - `"llm_partial"` when the LLM ran but JSON was missing required
        sections; gaps filled with fallback values + degradation event
        emitted by the caller;
      - `"fallback_no_llm"` when any failure short-circuits to the
        placeholder model (LLM unavailable / raised / returned malformed
        JSON).

    `llm` follows the `harness.llm.protocol.LLMProvider` interface
    (single async `.call(system, user, max_tokens, temperature)`). If
    `llm` is None the fallback model is returned with `_method ==
    "fallback_no_llm"`.
    """
    if llm is None:
        raise SubSkillUnavailable(
            "competency_extractor", "LLM provider not configured", llm_unreachable=True
        )

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        lens=lens or "(unspecified)",
        jd_text=jd_text or "",
    )

    try:
        response = await llm.call(
            system=_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=4096,
            temperature=0.2,
        )
    except (asyncio.TimeoutError, ConnectionError, CircuitOpen) as e:
        raise SubSkillUnavailable("competency_extractor", str(e), llm_unreachable=True) from e
    except InjectionDetectedError as e:
        raise SubSkillUnavailable(
            "competency_extractor", f"injection detected: {e}", llm_unreachable=False
        ) from e

    if not isinstance(response, str) or not response.strip():
        raise SubSkillUnavailable(
            "competency_extractor", "empty LLM response", llm_unreachable=False
        )

    try:
        raw = json.loads(_strip_json_fences(response))
    except (json.JSONDecodeError, ValueError) as e:
        raise SubSkillUnavailable(
            "competency_extractor", f"malformed JSON from LLM: {e}", llm_unreachable=False
        ) from e

    model, was_complete = _normalize_model(raw, lens)
    model["_method"] = "llm" if was_complete else "llm_partial"
    return model


# ----------------------------- helpers for callers -----------------------------


def section_d_keywords(model: dict | None) -> list[str]:
    """Flatten Section D tiers 1/2/3/5 into a deduped keyword list.

    Tier 4 is action verbs (Skills rows are nouns) — skip per Step B.3 spec.
    Returns [] if `model` is None / missing Section D.
    """
    if not model:
        return []
    section_d = model.get("section_d_keyword_architecture")
    if not isinstance(section_d, dict):
        return []

    keys = (
        "tier_1_core_role",
        "tier_2_capability",
        "tier_3_tools_methods",
        "tier_5_semantic_equivalents",
    )
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        items = section_d.get(key) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized:
                continue
            low = normalized.lower()
            if low in seen:
                continue
            seen.add(low)
            out.append(normalized)
    return out


def section_h_strategy_hints(model: dict | None, max_chars: int = 280) -> dict | None:
    """Extract Section H content as a compact dict for SummaryWriter prompts.

    Returns None if `model` is None / Section H missing / empty.
    """
    if not model:
        return None
    section_h = model.get("section_h_strategy_implications")
    if not isinstance(section_h, dict):
        return None

    emphasize = (section_h.get("emphasize_most") or "").strip()
    top_half = (section_h.get("top_half_content") or "").strip()
    if not emphasize and not top_half:
        return None

    def _trim(s: str, cap: int) -> str:
        return s if len(s) <= cap else s[: cap - 1].rstrip() + "…"

    return {
        "emphasize_most": _trim(emphasize, max_chars),
        "top_half_content": _trim(top_half, max_chars),
    }
