"""Quality-pass-runner entry points for Pass 1.5 and Pass 2."""
from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen

from ._normalize import (
    build_pass_1_stub,
    build_pass_3_stub,
    normalize_ai_tone,
    normalize_chinese_readability,
)
from .prompts import (
    _PASS_1_5_SYSTEM_PROMPT,
    _PASS_2_SYSTEM_PROMPT,
    render_pass_1_5_user_prompt,
    render_pass_2_user_prompt,
)


_VALID_MARKETS = frozenset({"north-america", "mainland-china", "hong-kong"})


async def _probe_llm(
    *,
    llm: Any,
    system: str,
    user: str,
) -> str:
    response = await llm.call(
        system=system,
        user=user,
        max_tokens=512,
        temperature=0.0,
    )
    if not isinstance(response, str) or not response.strip():
        return "fallback_no_llm"
    return "llm"


async def run_pass_1_5(
    resume_text: str,
    *,
    target_market: str,
    llm: Any = None,
) -> dict[str, Any]:
    method = "fallback_no_llm"
    if llm is not None:
        try:
            method = await _probe_llm(
                llm=llm,
                system=_PASS_1_5_SYSTEM_PROMPT,
                user=render_pass_1_5_user_prompt(
                    target_market=target_market,
                    resume_text=resume_text or "",
                ),
            )
        except (asyncio.TimeoutError, ConnectionError, CircuitOpen, InjectionDetectedError):
            method = "fallback_no_llm"

    result = normalize_chinese_readability(
        resume_text or "",
        target_market=target_market,
    )
    result["_method"] = method
    return result


async def run_pass_2(
    resume_text: str,
    *,
    jd_text: str,
    target_market: str,
    llm: Any = None,
) -> dict[str, Any]:
    method = "fallback_no_llm"
    if llm is not None:
        try:
            method = await _probe_llm(
                llm=llm,
                system=_PASS_2_SYSTEM_PROMPT,
                user=render_pass_2_user_prompt(
                    target_market=target_market,
                    resume_text=resume_text or "",
                    jd_text=jd_text or "",
                ),
            )
        except (asyncio.TimeoutError, ConnectionError, CircuitOpen, InjectionDetectedError):
            method = "fallback_no_llm"

    result = normalize_ai_tone(resume_text or "", jd_text=jd_text or "")
    result["_method"] = method
    return result


async def build_quality_pass_report(
    *,
    rewritten_resume: str,
    target_market: str,
    jd_text: str,
    competency_profile: dict | None,
    experience_bank: dict | None,
    llm: Any = None,
    invoked_at: datetime | None = None,
) -> dict[str, Any]:
    if target_market not in _VALID_MARKETS:
        raise ValueError(
            f"target_market must be one of {sorted(_VALID_MARKETS)}, got {target_market!r}"
        )

    if invoked_at is None:
        invoked_at = datetime.now(timezone.utc)

    resume = rewritten_resume or ""
    pass_1 = build_pass_1_stub()

    pass_1_5 = await run_pass_1_5(
        resume,
        target_market=target_market,
        llm=llm,
    )
    after_1_5 = pass_1_5["text"]

    pass_2 = await run_pass_2(
        after_1_5,
        jd_text=jd_text or "",
        target_market=target_market,
        llm=llm,
    )
    final_text = pass_2["text"]

    pass_3 = build_pass_3_stub()
    aggregate = _aggregate_verdict(pass_1, pass_1_5, pass_2, pass_3)
    confidence = _compute_confidence(
        resume=resume,
        competency_profile=competency_profile,
        experience_bank=experience_bank,
        methods=[pass_1_5.get("_method"), pass_2.get("_method")],
    )
    pending = aggregate in {"partial_pending_user", "fail"} or confidence == "low"

    return {
        "schema_version": "1.0.0",
        "sub_skill": "quality-pass-runner",
        "target_market": target_market,
        "ppaf_stage": "late_feedback",
        "invoked_at": invoked_at.isoformat(),
        "inputs_signature": {
            "rewritten_resume_hash": hashlib.sha256(resume.encode("utf-8")).hexdigest(),
            "competency_profile_id": _stable_hash(competency_profile),
            "experience_bank_version": _stable_hash(experience_bank),
        },
        "final_resume_text": final_text,
        "aggregate_verdict": aggregate,
        "pending_user_review_flag": pending,
        "confidence": confidence,
        "_method": _combined_method(pass_1_5.get("_method"), pass_2.get("_method")),
        "pass_1_keyword_injection": pass_1,
        "pass_1_5_chinese_readability": _without_text(pass_1_5),
        "pass_2_ai_taste_removal": _without_text(pass_2),
        "pass_3_truthfulness": pass_3,
    }


def _stable_hash(payload: Any) -> str:
    if payload is None:
        return "unknown"
    try:
        data = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        data = repr(payload)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def _without_text(result: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in result.items() if k != "text"}


def _aggregate_verdict(pass_1: dict, pass_1_5: dict, pass_2: dict, pass_3: dict) -> str:
    verdicts = [
        pass_1.get("verdict"),
        pass_1_5.get("verdict"),
        pass_2.get("verdict"),
        pass_3.get("verdict"),
    ]
    if "fail" in verdicts:
        return "fail"
    if "partial_pending_user" in verdicts or "partial" in verdicts:
        return "partial_pending_user"
    return "pass"


def _compute_confidence(
    *,
    resume: str,
    competency_profile: dict | None,
    experience_bank: dict | None,
    methods: list[str | None],
) -> str:
    if not resume.strip():
        return "low"
    if any(method == "fallback_no_llm" for method in methods):
        if competency_profile and experience_bank:
            return "moderate"
        return "low"
    if competency_profile and experience_bank:
        return "high"
    return "moderate"


def _combined_method(*methods: str | None) -> str:
    if any(method == "llm_partial" for method in methods):
        return "llm_partial"
    if all(method == "llm" for method in methods):
        return "llm"
    return "fallback_no_llm"


__all__ = [
    "build_quality_pass_report",
    "run_pass_1_5",
    "run_pass_2",
]
