"""Fit diagnosis engine — Wave 5 F1 entry point.

Two-mode entry point per the canonical spec at
`packages/strategy-modules/fit-diagnosis-engine/`:
  - mode == "pre_rewrite"  → Section 4 payload (this phase, F1).
  - mode == "post_rewrite" → Section 8 payload (F3, NotImplementedError).

`build_diagnosis` returns a dict matching the common header + Section 4
shape described in `output-schema.md`. On any documented LLM failure
(timeout / connection / circuit / injection) it returns a shape-valid
fallback marked `_method == "fallback_no_llm"`. Programmer-bug
exceptions (RuntimeError / KeyError / TypeError) propagate so the bug
gets surfaced — see `docs/SUBAGENT_DISPATCH_TEMPLATE.md` Rule 1.1.

Caller-side wiring (PLANNING stage invocation, late_feedback ABCD
ordering, REPL state attach) lands in F2 — see plan
`docs/plans/2026-05-09-fit-diagnosis-engine-refactor.md`.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, Literal

from harness.exceptions import SubSkillUnavailable
from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen

from ._normalize import _normalize_post_rewrite, _normalize_pre_rewrite
from ._shared import build_common_header, compute_confidence
from .prompts import (
    _POST_REWRITE_SYSTEM_PROMPT,
    _PRE_REWRITE_SYSTEM_PROMPT,
    render_post_rewrite_user_prompt,
    render_pre_rewrite_user_prompt,
)


_VALID_MODES: frozenset[str] = frozenset({"pre_rewrite", "post_rewrite"})

Mode = Literal["pre_rewrite", "post_rewrite"]


def _strip_json_fences(text: str) -> str:
    """Best-effort: pull a JSON object out of ```json ...``` fences if present.

    Copied from `harness/forecast/matrix.py` to keep fit_diagnosis a
    self-contained sub-skill (no cross-module imports between the old
    Step-4-only forecast/ module and the consolidated fit_diagnosis/).
    """
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _format_section_b(competency_profile: dict | None) -> str:
    if not isinstance(competency_profile, dict):
        return "(unavailable)"
    section_b = competency_profile.get("section_b_core_hiring_logic")
    if not section_b:
        return "(unavailable)"
    try:
        return json.dumps(section_b, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return "(unserializable)"


def _format_section_c(competency_profile: dict | None) -> str:
    if not isinstance(competency_profile, dict):
        return "(unavailable)"
    section_c = competency_profile.get("section_c_qualification_model")
    if not section_c:
        return "(unavailable)"
    try:
        return json.dumps(section_c, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return "(unserializable)"


def _format_experience_trace(trace: list[dict] | None) -> str:
    if not trace:
        return "(no experience selection trace available)"
    try:
        return json.dumps(trace, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return "(unserializable)"


def _competency_complete(competency_profile: dict | None) -> bool:
    """Approximation: 9-section model is complete iff all 9 section_x_* keys
    plus a flat-field summary are present."""
    if not isinstance(competency_profile, dict):
        return False
    section_keys = [k for k in competency_profile if k.startswith("section_")]
    return len(section_keys) >= 9


def _market_loaded(target_market: str | None) -> bool:
    """target_market is loaded when the caller passed an explicit value
    rather than relying on default fallback."""
    return target_market in {"north-america", "mainland-china", "hong-kong"}


def _build_pre_rewrite_payload(
    *,
    section_4: dict,
    target_market: str,
    jd_analysis: Any,
    competency_profile: Any,
    multi_jd: bool,
    method: str,
    competency_complete: bool,
    market_loaded: bool,
    jd_count: int,
) -> dict:
    """Stitch common header + Section 4 body into the public output dict."""
    confidence = compute_confidence(
        jd_count=jd_count,
        competency_complete=competency_complete,
        market_loaded=market_loaded,
        method=method,
    )
    competitiveness_rating = "mid"  # spec-compliant placeholder until
    # post-LLM rating extraction lands; F1 contract only needs the field
    # to exist — F3 may add an LLM-driven rating.
    header = build_common_header(
        mode="pre_rewrite",
        target_market=target_market,
        jd_analysis=jd_analysis,
        competency_profile=competency_profile,
        current_resume_hash=None,
        multi_jd=multi_jd,
        method=method,
        competitiveness_rating=competitiveness_rating,
        confidence=confidence,
    )
    payload = dict(header)
    payload["matching_matrix"] = section_4["matching_matrix"]
    payload["integrated_assessment"] = section_4["integrated_assessment"]
    payload["optimization_boundary"] = section_4["optimization_boundary"]
    if multi_jd:
        payload["multi_jd_coverage"] = section_4["multi_jd_coverage"]
        payload["spread_flag"] = section_4["spread_flag"]
    else:
        payload["multi_jd_coverage"] = None
        payload["spread_flag"] = None
    return payload


def _empty_section_4(*, integrated_assessment: str, multi_jd: bool) -> dict:
    """Shape-valid empty Section 4 body — used by every fallback branch."""
    return {
        "matching_matrix": [],
        "integrated_assessment": integrated_assessment,
        "optimization_boundary": {
            "rewriting_can_solve": [],
            "rewriting_cannot_solve": [],
        },
        "multi_jd_coverage": [] if multi_jd else None,
        "spread_flag": False if multi_jd else None,
    }


def _build_post_rewrite_payload(
    *,
    section_8: dict,
    target_market: str,
    jd_analysis: Any,
    competency_profile: Any,
    current_resume_hash: str | None,
    multi_jd: bool,
    method: str,
    competency_complete: bool,
    market_loaded: bool,
    jd_count: int,
) -> dict:
    """Stitch common header + Section 8 body into the public output dict.

    Mirrors `_build_pre_rewrite_payload`. The Section 8 dict carries
    `competitiveness_rating` (LLM-emitted, unlike the placeholder used
    in pre_rewrite), so we lift it into the header rather than hard-coding.
    """
    confidence = compute_confidence(
        jd_count=jd_count,
        competency_complete=competency_complete,
        market_loaded=market_loaded,
        method=method,
    )
    competitiveness_rating = section_8.get("competitiveness_rating", "mid")
    header = build_common_header(
        mode="post_rewrite",
        target_market=target_market,
        jd_analysis=jd_analysis,
        competency_profile=competency_profile,
        current_resume_hash=current_resume_hash,
        multi_jd=multi_jd,
        method=method,
        competitiveness_rating=competitiveness_rating,
        confidence=confidence,
    )
    payload = dict(header)
    payload["hm"] = section_8["hm"]
    payload["hrbp"] = section_8["hrbp"]
    payload["radar"] = section_8["radar"]
    payload["improvement_suggestions"] = section_8["improvement_suggestions"]
    return payload


def _empty_section_8() -> dict:
    """Shape-valid empty Section 8 body — used by every post_rewrite fallback."""
    from ._normalize import _DEFAULT_AXES  # local import to avoid circular

    return {
        "competitiveness_rating": "mid",
        "hm": {
            "highlights": [],
            "concerns": [],
            "comparison_risk": (
                "Fit diagnosis unavailable; LLM did not return a usable structure."
            ),
        },
        "hrbp": {
            "keyword_hit_rate": 0.0,
            "hard_filter_match": {},
            "advance_decision": "screen_out",
            "decision_rationale": (
                "Fit diagnosis unavailable; defaulting to conservative screen."
            ),
        },
        "improvement_suggestions": [],
        "radar": {
            "dimensions": [
                {
                    "name": axis,
                    "resume_score": 0,
                    "jd_required": 0,
                    "citation": "",
                }
                for axis in _DEFAULT_AXES
            ]
        },
    }


def _hash_current_resume(current_resume: str | None) -> str | None:
    """Compute the sha256 hex digest of the rewritten resume body.

    Returns None when current_resume is None (pre_rewrite mode signature).
    Per spec: full 64-char hex digest, NOT truncated; the test contract
    accepts 16-64 hex chars but we always emit 64 for forensic parity
    with `git rev-parse`-style hashes.
    """
    if current_resume is None:
        return None
    return hashlib.sha256(current_resume.encode("utf-8")).hexdigest()


def fallback_diagnosis(
    *,
    mode: str = "pre_rewrite",
    target_market: str = "north-america",
    multi_jd: bool = False,
    current_resume_hash: str | None = None,
) -> dict:
    """Return a minimal valid diagnosis marked as fallback.

    Used when the LLM raises, returns malformed JSON, or returns content
    that is missing critical structure. The FEEDBACK stage should record
    a degradation event when this is returned so callers can see why.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            "mode must be 'pre_rewrite' or 'post_rewrite'"
        )

    if mode == "post_rewrite":
        return _build_post_rewrite_payload(
            section_8=_empty_section_8(),
            target_market=target_market,
            jd_analysis=None,
            competency_profile=None,
            current_resume_hash=current_resume_hash,
            multi_jd=multi_jd,
            method="fallback_no_llm",
            competency_complete=False,
            market_loaded=_market_loaded(target_market),
            jd_count=0,
        )

    section_4 = _empty_section_4(
        integrated_assessment=(
            "Fit diagnosis unavailable; LLM did not return a usable structure."
        ),
        multi_jd=multi_jd,
    )
    return _build_pre_rewrite_payload(
        section_4=section_4,
        target_market=target_market,
        jd_analysis=None,
        competency_profile=None,
        multi_jd=multi_jd,
        method="fallback_no_llm",
        competency_complete=False,
        market_loaded=_market_loaded(target_market),
        jd_count=0,
    )


async def build_diagnosis(
    *,
    mode: str,
    target_market: str,
    jd_text: str,
    competency_profile: dict | None,
    experience_selection_trace: list[dict] | None,
    lens: str,
    multi_jd: bool = False,
    current_resume: str | None = None,
    llm: Any,
) -> dict:
    """Produce the fit-diagnosis payload for the given run.

    F1 contract:
      - mode must be one of {"pre_rewrite", "post_rewrite"}.
      - mode == "pre_rewrite" → returns Section 4 payload.
      - mode == "post_rewrite" → raises NotImplementedError (F3 fills in).

    `_method` semantics mirror harness/forecast/matrix.py:
      - "llm": full LLM-driven extraction with all required keys present.
      - "llm_partial": LLM ran but JSON was missing required keys / had
        invalid enum values; gaps filled with fallback values.
      - "fallback_no_llm": LLM unavailable / raised / returned malformed
        JSON; whole structure is the placeholder fallback.

    `llm` follows the `harness.llm.protocol.LLMProvider` interface
    (single async `.call(system, user, max_tokens, temperature)`). If
    `llm` is None the fallback diagnosis is returned with `_method ==
    "fallback_no_llm"`.

    Per Rule 1.1 (SUBAGENT_DISPATCH_TEMPLATE.md), only the documented
    LLM failure modes are caught; programmer-bug exceptions
    (RuntimeError / KeyError / TypeError) propagate.
    """
    if mode not in _VALID_MODES:
        raise ValueError(
            "mode must be 'pre_rewrite' or 'post_rewrite'"
        )

    market_loaded = _market_loaded(target_market)
    competency_complete = _competency_complete(competency_profile)
    # F1/F3 callers always pass a single JD (multi_jd flag enables Section
    # 4-D, but the JD count itself is 1 unless future callers pass an
    # explicit count — for now we approximate as 4 when multi_jd=True
    # so confidence can climb; F2/F4 may pipe an explicit jd_count param).
    jd_count = 4 if multi_jd else 1

    if mode == "post_rewrite":
        # Per spec: post_rewrite mode requires the rewritten resume body
        # because every HM/HRBP/radar assertion is grounded in it.
        if current_resume is None:
            raise ValueError(
                "post_rewrite requires current_resume; pass the rewritten resume body"
            )

        current_resume_hash = _hash_current_resume(current_resume)

        if llm is None:
            raise SubSkillUnavailable(
                "fit_diagnosis_post_rewrite",
                "LLM unavailable at call time",
                llm_unreachable=True,
            )

        post_user_prompt = render_post_rewrite_user_prompt(
            target_market=target_market,
            lens=lens,
            jd_text=jd_text,
            section_b=_format_section_b(competency_profile),
            section_c=_format_section_c(competency_profile),
            experience_trace=_format_experience_trace(experience_selection_trace),
            current_resume=current_resume,
            # F3 ships without an explicit upstream pre_rewrite/match-matrix
            # input wired through this signature; F3.5 may add an explicit
            # `fit_diagnosis_pre_rewrite` parameter so HRBP can cross-reference
            # the Section 4 verdicts. For now the LLM operates off the
            # rewritten resume body + JD only.
            match_matrix_summary="(unavailable)",
        )

        try:
            response = await llm.call(
                system=_POST_REWRITE_SYSTEM_PROMPT,
                user=post_user_prompt,
                max_tokens=2048,
                temperature=0.2,
            )
        except (asyncio.TimeoutError, ConnectionError, CircuitOpen) as e:
            raise SubSkillUnavailable(
                "fit_diagnosis_post_rewrite", str(e), llm_unreachable=True
            ) from e
        except InjectionDetectedError as e:
            raise SubSkillUnavailable(
                "fit_diagnosis_post_rewrite",
                f"injection detected: {e}",
                llm_unreachable=False,
            ) from e

        if not isinstance(response, str) or not response.strip():
            raise SubSkillUnavailable(
                "fit_diagnosis_post_rewrite",
                "LLM returned empty response",
                llm_unreachable=False,
            )

        try:
            raw = json.loads(_strip_json_fences(response))
        except (json.JSONDecodeError, ValueError) as e:
            raise SubSkillUnavailable(
                "fit_diagnosis_post_rewrite",
                f"malformed JSON from LLM: {e}",
                llm_unreachable=False,
            ) from e

        section_8, was_complete = _normalize_post_rewrite(raw)
        method = "llm" if was_complete else "llm_partial"

        return _build_post_rewrite_payload(
            section_8=section_8,
            target_market=target_market,
            jd_analysis=jd_text,
            competency_profile=competency_profile,
            current_resume_hash=current_resume_hash,
            multi_jd=multi_jd,
            method=method,
            competency_complete=competency_complete,
            market_loaded=market_loaded,
            jd_count=jd_count,
        )

    # ----- mode == "pre_rewrite" -----
    # current_resume is allowed but ignored in pre_rewrite; the spec
    # forbids it being non-null but the F1 caller-side hasn't been
    # tightened yet, so we tolerate (signature still null in header).
    _ = current_resume

    if llm is None:
        raise SubSkillUnavailable(
            "fit_diagnosis_pre_rewrite",
            "LLM unavailable at call time",
            llm_unreachable=True,
        )

    user_prompt = render_pre_rewrite_user_prompt(
        target_market=target_market,
        lens=lens,
        multi_jd=multi_jd,
        jd_text=jd_text,
        section_b=_format_section_b(competency_profile),
        section_c=_format_section_c(competency_profile),
        experience_trace=_format_experience_trace(experience_selection_trace),
    )

    try:
        response = await llm.call(
            system=_PRE_REWRITE_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=2048,
            temperature=0.2,
        )
    except (asyncio.TimeoutError, ConnectionError, CircuitOpen) as e:
        raise SubSkillUnavailable(
            "fit_diagnosis_pre_rewrite", str(e), llm_unreachable=True
        ) from e
    except InjectionDetectedError as e:
        raise SubSkillUnavailable(
            "fit_diagnosis_pre_rewrite",
            f"injection detected: {e}",
            llm_unreachable=False,
        ) from e

    if not isinstance(response, str) or not response.strip():
        raise SubSkillUnavailable(
            "fit_diagnosis_pre_rewrite",
            "LLM returned empty response",
            llm_unreachable=False,
        )

    try:
        raw = json.loads(_strip_json_fences(response))
    except (json.JSONDecodeError, ValueError) as e:
        raise SubSkillUnavailable(
            "fit_diagnosis_pre_rewrite",
            f"malformed JSON from LLM: {e}",
            llm_unreachable=False,
        ) from e

    section_4, was_complete = _normalize_pre_rewrite(raw, multi_jd=multi_jd)
    method = "llm" if was_complete else "llm_partial"

    return _build_pre_rewrite_payload(
        section_4=section_4,
        target_market=target_market,
        jd_analysis=jd_text,
        competency_profile=competency_profile,
        multi_jd=multi_jd,
        method=method,
        competency_complete=competency_complete,
        market_loaded=market_loaded,
        jd_count=jd_count,
    )


__all__ = ["build_diagnosis", "fallback_diagnosis"]
