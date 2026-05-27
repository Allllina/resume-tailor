"""Normalizers for gap-bridging-planner output."""
from __future__ import annotations

from typing import Any


_VALID_HORIZONS = frozenset({"short_term", "mid_term", "not_closeable"})
_VALID_ACTIONS = frozenset({"plan_now", "defer", "accept"})
_VALID_TIMELINES = frozenset({"immediate", "near", "mid"})
_VALID_TIERS = frozenset({"A", "B"})
_VALID_PLACEMENTS = frozenset({"technical", "ai", "language", "other"})
_VALID_MISSING_ACTIONS = frozenset({"add", "acknowledge_absence"})
_VALID_RESOLUTIONS = frozenset(
    {"master_with_jd_specific", "branch_versions", "accept_compromise"}
)


def _clean_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _derive_action(horizon: str, timeline: str) -> str:
    if horizon == "short_term":
        return "plan_now"
    if horizon == "mid_term":
        return "defer" if timeline == "immediate" else "plan_now"
    return "accept"


def _normalize_reframe_directives(raw: Any) -> tuple[list[dict], bool]:
    if not isinstance(raw, list):
        return [], False
    out: list[dict] = []
    complete = True
    for item in raw:
        if not isinstance(item, dict):
            complete = False
            continue
        normalized = {
            "matrix_row_id": _clean_str(item.get("matrix_row_id")),
            "target_experience": _clean_str(item.get("target_experience")),
            "target_bullet_id": _clean_str(item.get("target_bullet_id")),
            "keyword_to_inject": _clean_str(item.get("keyword_to_inject")),
            "framing_directive": _clean_str(item.get("framing_directive")),
            "source_evidence": _clean_str(item.get("source_evidence")),
        }
        if not all(normalized.values()):
            complete = False
            continue
        out.append(normalized)
    return out, complete


def _normalize_add_suggestions(raw: Any, timeline: str) -> tuple[list[dict], bool]:
    if not isinstance(raw, list):
        return [], False
    out: list[dict] = []
    complete = True
    for item in raw:
        if not isinstance(item, dict):
            complete = False
            continue
        gap_label = _clean_str(item.get("gap_label"))
        suggestion = _clean_str(item.get("suggestion"))
        if not gap_label or not suggestion:
            complete = False
            continue
        horizon = item.get("horizon")
        if horizon not in _VALID_HORIZONS:
            horizon = "not_closeable"
            complete = False
        action = item.get("action")
        derived = _derive_action(horizon, timeline)
        if action not in _VALID_ACTIONS or action != derived:
            action = derived
            complete = False
        out.append(
            {
                "gap_label": gap_label,
                "horizon": horizon,
                "action": action,
                "suggestion": suggestion,
            }
        )
    return out, complete


def _normalize_skill_bar(raw: Any) -> tuple[dict, bool]:
    if not isinstance(raw, dict):
        return {"add_to_bar": [], "remove_from_bar": [], "do_not_add": []}, False
    complete = True
    add_to_bar: list[dict] = []
    for item in raw.get("add_to_bar", []):
        if not isinstance(item, dict):
            complete = False
            continue
        skill = _clean_str(item.get("skill"))
        rationale = _clean_str(item.get("rationale"))
        tier = item.get("tier")
        placement = item.get("placement_row")
        if (
            not skill
            or not rationale
            or tier not in _VALID_TIERS
            or placement not in _VALID_PLACEMENTS
        ):
            complete = False
            continue
        add_to_bar.append(
            {
                "skill": skill,
                "tier": tier,
                "placement_row": placement,
                "rationale": rationale,
            }
        )
    remove_from_bar, remove_complete = _normalize_skill_reason_list(
        raw.get("remove_from_bar")
    )
    do_not_add, dna_complete = _normalize_skill_reason_list(raw.get("do_not_add"))
    return (
        {
            "add_to_bar": add_to_bar,
            "remove_from_bar": remove_from_bar,
            "do_not_add": do_not_add,
        },
        complete and remove_complete and dna_complete,
    )


def _normalize_skill_reason_list(raw: Any) -> tuple[list[dict], bool]:
    if not isinstance(raw, list):
        return [], False
    out: list[dict] = []
    complete = True
    for item in raw:
        if not isinstance(item, dict):
            complete = False
            continue
        skill = _clean_str(item.get("skill"))
        reason = _clean_str(item.get("reason"))
        if not skill or not reason:
            complete = False
            continue
        out.append({"skill": skill, "reason": reason})
    return out, complete


def _normalize_section_ordering(raw: Any) -> tuple[dict, bool]:
    if not isinstance(raw, dict):
        return _empty_section_ordering(), False
    complete = True
    order_raw = raw.get("experience_section_order")
    if isinstance(order_raw, list):
        order = [_clean_str(x) for x in order_raw if _clean_str(x)]
        if len(order) != len(order_raw):
            complete = False
    else:
        order = []
        complete = False
    emphasis: list[dict] = []
    for item in raw.get("experience_section_emphasis", []):
        if not isinstance(item, dict):
            complete = False
            continue
        exp_id = _clean_str(item.get("exp_id"))
        rationale = _clean_str(item.get("rationale"))
        try:
            count = int(item.get("bullet_count_recommendation"))
        except (TypeError, ValueError):
            count = 1
            complete = False
        if count < 1:
            count = 1
            complete = False
        if not exp_id or not rationale:
            complete = False
            continue
        emphasis.append(
            {
                "exp_id": exp_id,
                "bullet_count_recommendation": count,
                "rationale": rationale,
            }
        )
    missing: list[dict] = []
    for item in raw.get("missing_sections", []):
        if not isinstance(item, dict):
            complete = False
            continue
        section_name = _clean_str(item.get("section_name"))
        rationale = _clean_str(item.get("rationale"))
        action = item.get("action")
        if action not in _VALID_MISSING_ACTIONS:
            action = "acknowledge_absence"
            complete = False
        if not section_name or not rationale:
            complete = False
            continue
        missing.append(
            {"section_name": section_name, "action": action, "rationale": rationale}
        )
    return (
        {
            "experience_section_order": order,
            "experience_section_emphasis": emphasis,
            "missing_sections": missing,
        },
        complete,
    )


def _normalize_multi_jd_conflict(raw: Any) -> tuple[dict, bool]:
    if not isinstance(raw, dict):
        return _empty_multi_jd_conflict(), False
    complete = True
    conflicts: list[dict] = []
    conflicts_raw = raw.get("conflicting_directives")
    if not isinstance(conflicts_raw, list):
        conflicts_raw = []
        complete = False
    for item in conflicts_raw:
        if not isinstance(item, dict):
            complete = False
            continue
        jd_a = _clean_str(item.get("jd_a"))
        jd_b = _clean_str(item.get("jd_b"))
        summary = _clean_str(item.get("conflict_summary"))
        if not jd_a or not jd_b or not summary:
            complete = False
            continue
        conflicts.append(
            {"jd_a": jd_a, "jd_b": jd_b, "conflict_summary": summary}
        )
    resolution = raw.get("proposed_resolution")
    if resolution not in _VALID_RESOLUTIONS:
        resolution = "accept_compromise"
        complete = False
    rationale = _clean_str(raw.get("rationale"))
    return (
        {
            "conflicting_directives": conflicts,
            "proposed_resolution": resolution,
            "rationale": rationale,
        },
        complete,
    )


def _empty_section_ordering() -> dict:
    return {
        "experience_section_order": [],
        "experience_section_emphasis": [],
        "missing_sections": [],
    }


def _empty_multi_jd_conflict() -> dict:
    return {
        "conflicting_directives": [],
        "proposed_resolution": "accept_compromise",
        "rationale": "",
    }


def normalize_gap_bridging_sections(
    raw: Any, *, application_timeline: str
) -> tuple[dict, bool]:
    if not isinstance(raw, dict):
        return _empty_sections(), False
    timeline = (
        application_timeline
        if application_timeline in _VALID_TIMELINES
        else "immediate"
    )
    reframe, reframe_complete = _normalize_reframe_directives(
        raw.get("reframe_directives")
    )
    add, add_complete = _normalize_add_suggestions(
        raw.get("add_suggestions"), timeline
    )
    skills, skills_complete = _normalize_skill_bar(raw.get("skill_bar_adjustments"))
    ordering, ordering_complete = _normalize_section_ordering(
        raw.get("section_ordering")
    )
    conflict, conflict_complete = _normalize_multi_jd_conflict(
        raw.get("multi_jd_conflict")
    )
    return (
        {
            "reframe_directives": reframe,
            "add_suggestions": add,
            "skill_bar_adjustments": skills,
            "section_ordering": ordering,
            "multi_jd_conflict": conflict,
        },
        all(
            [
                reframe_complete,
                add_complete,
                skills_complete,
                ordering_complete,
                conflict_complete,
            ]
        ),
    )


def _empty_sections() -> dict:
    return {
        "reframe_directives": [],
        "add_suggestions": [],
        "skill_bar_adjustments": {
            "add_to_bar": [],
            "remove_from_bar": [],
            "do_not_add": [],
        },
        "section_ordering": _empty_section_ordering(),
        "multi_jd_conflict": _empty_multi_jd_conflict(),
    }


__all__ = ["normalize_gap_bridging_sections"]
