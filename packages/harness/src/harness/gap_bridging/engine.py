"""Gap bridging planner engine."""
from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from harness.exceptions import SubSkillUnavailable
from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen

from ._normalize import normalize_gap_bridging_sections
from .prompts import _SYSTEM_PROMPT, render_user_prompt


_VALID_MARKETS = frozenset({"north-america", "mainland-china", "hong-kong"})
_VALID_TIMELINES = frozenset({"immediate", "near", "mid"})


def _strip_json_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _stable_hash(payload: Any) -> str:
    if payload is None:
        return "unknown"
    try:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        serialized = repr(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _json_block(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        return "(unserializable)"


def _is_multi_jd_scope(competency_profile: Any) -> bool:
    if not isinstance(competency_profile, dict):
        return False
    flat = competency_profile.get("flat")
    notes = ""
    if isinstance(flat, dict):
        notes = str(flat.get("scoring_notes") or "")
    return "multi-jd" in notes.lower() or "multi_jd" in notes.lower()


def _compute_confidence(*, method: str, sections: dict) -> str:
    if method == "fallback_no_llm":
        return "low"
    if method == "llm_partial":
        return "moderate"
    if (
        len(sections["reframe_directives"]) >= 3
        and sections["add_suggestions"]
        and sections["skill_bar_adjustments"]["add_to_bar"]
    ):
        return "high"
    return "moderate"


def _build_payload(
    *,
    sections: dict,
    target_market: str,
    application_timeline: str,
    fit_diagnosis_pre_rewrite: Any,
    competency_profile: Any,
    method: str,
) -> dict:
    confidence = _compute_confidence(method=method, sections=sections)
    conflict = sections["multi_jd_conflict"]
    conflict_flag = bool(conflict["conflicting_directives"]) or _is_multi_jd_scope(
        competency_profile
    )
    return {
        "sub_skill": "gap-bridging-planner",
        "target_market": target_market,
        "ppaf_stage": "planning",
        "invoked_at": datetime.now(timezone.utc).isoformat(),
        "inputs_signature": {
            "fit_diagnosis_id": _stable_hash(fit_diagnosis_pre_rewrite),
            "competency_profile_id": _stable_hash(competency_profile),
        },
        "application_timeline": application_timeline,
        "confidence": confidence,
        "multi_jd_conflict_flag": conflict_flag,
        "_method": method,
        "reframe_directives": sections["reframe_directives"],
        "add_suggestions": sections["add_suggestions"],
        "skill_bar_adjustments": sections["skill_bar_adjustments"],
        "section_ordering": sections["section_ordering"],
        "multi_jd_conflict": conflict,
    }


def fallback_gap_bridging_plan(
    *,
    target_market: str = "north-america",
    application_timeline: str = "immediate",
    fit_diagnosis_pre_rewrite: dict | None = None,
    competency_profile: dict | None = None,
) -> dict:
    if target_market not in _VALID_MARKETS:
        raise ValueError("target_market must be north-america, mainland-china, or hong-kong")
    if application_timeline not in _VALID_TIMELINES:
        application_timeline = "immediate"
    sections, _ = normalize_gap_bridging_sections(
        {}, application_timeline=application_timeline
    )
    return _build_payload(
        sections=sections,
        target_market=target_market,
        application_timeline=application_timeline,
        fit_diagnosis_pre_rewrite=fit_diagnosis_pre_rewrite,
        competency_profile=competency_profile,
        method="fallback_no_llm",
    )


async def build_gap_bridging_plan(
    *,
    fit_diagnosis_pre_rewrite: dict,
    competency_profile: dict,
    candidate_assets: dict,
    target_market: str,
    application_timeline: str = "immediate",
    llm: Any,
) -> dict:
    if target_market not in _VALID_MARKETS:
        raise ValueError("target_market must be north-america, mainland-china, or hong-kong")
    if application_timeline not in _VALID_TIMELINES:
        application_timeline = "immediate"

    if llm is None:
        raise SubSkillUnavailable(
            "gap_bridging_planner",
            "LLM provider not configured",
            llm_unreachable=True,
        )

    user_prompt = render_user_prompt(
        target_market=target_market,
        application_timeline=application_timeline,
        fit_diagnosis=_json_block(fit_diagnosis_pre_rewrite),
        competency_profile=_json_block(competency_profile),
        candidate_assets=_json_block(candidate_assets),
    )

    try:
        response = await llm.call(
            system=_SYSTEM_PROMPT,
            user=user_prompt,
            # 4096 (was 2048): the gap-bridging plan (reframe + add + section
            # ordering) can exceed 2048 tokens; truncation produced unterminated
            # JSON → SubSkillUnavailable → 503 (live smoke 2026-05-23).
            max_tokens=4096,
            temperature=0.2,
        )
    except (asyncio.TimeoutError, ConnectionError, CircuitOpen) as e:
        raise SubSkillUnavailable(
            "gap_bridging_planner", str(e), llm_unreachable=True
        ) from e
    except InjectionDetectedError as e:
        raise SubSkillUnavailable(
            "gap_bridging_planner",
            f"injection detected: {e}",
            llm_unreachable=False,
        ) from e

    if not isinstance(response, str) or not response.strip():
        raise SubSkillUnavailable(
            "gap_bridging_planner",
            "empty LLM response",
            llm_unreachable=False,
        )

    try:
        raw = json.loads(_strip_json_fences(response))
    except (json.JSONDecodeError, ValueError) as e:
        raise SubSkillUnavailable(
            "gap_bridging_planner",
            f"malformed JSON from LLM: {e}",
            llm_unreachable=False,
        ) from e

    sections, was_complete = normalize_gap_bridging_sections(
        raw, application_timeline=application_timeline
    )
    method = "llm" if was_complete else "llm_partial"
    return _build_payload(
        sections=sections,
        target_market=target_market,
        application_timeline=application_timeline,
        fit_diagnosis_pre_rewrite=fit_diagnosis_pre_rewrite,
        competency_profile=competency_profile,
        method=method,
    )


__all__ = ["build_gap_bridging_plan", "fallback_gap_bridging_plan"]
