"""Per-section normalizers for fit_diagnosis pre_rewrite mode.

Mirrors the pattern in `harness/forecast/matrix.py:_normalize_*` —
each normalizer returns `(value, was_complete)`. `was_complete=False`
means the LLM-emitted shape was repaired (missing key, invalid enum,
missing bridging_or_closure); the engine layer maps that to
`_method = "llm_partial"`.

Section 4 contract per `packages/strategy-modules/fit-diagnosis-engine/
output-schema.md` Section 4 (matching_matrix + integrated_assessment +
optimization_boundary + optional multi_jd_coverage / spread_flag).

Note: bridging_or_closure semantic constraints (per spec):
  - verdict == "strong_match"  → bridging_or_closure: ""
  - verdict == "transferable"  → "<tier>; <one-sentence bridge plan>"
  - verdict == "missing"       → "<tier>; <closure horizon label>"
where <tier> in {"hard", "preferred"} and closure horizon label in
{"short_term", "long_term", "not_closeable"}. The Python normalizer
enforces the prefix + non-empty body; the JSON Schema layer keeps the
field as plain `{"type": "string"}` to keep the contract human-readable.
"""
from __future__ import annotations

from typing import Any


_VALID_VERDICTS: frozenset[str] = frozenset(
    {"strong_match", "transferable", "missing"}
)
_VALID_SOURCES: frozenset[str] = frozenset(
    {
        "section_b_priority",
        "section_c_tier_1",
        "section_c_tier_2",
        "section_c_tier_3",
    }
)
_VALID_TIERS: frozenset[str] = frozenset({"hard", "preferred"})
_VALID_CLOSURE_HORIZONS: frozenset[str] = frozenset(
    {"short_term", "long_term", "not_closeable"}
)
_VALID_BOUNDARY_PATHS: frozenset[str] = frozenset({"supplement", "accept"})

_REQUIRED_TOP_KEYS: tuple[str, ...] = (
    "matching_matrix",
    "integrated_assessment",
    "optimization_boundary",
)

_MAX_MATRIX_ITEMS: int = 12

_PLACEHOLDER_TRANSFERABLE_BRIDGE: str = "preferred; bridge plan unavailable"
_PLACEHOLDER_MISSING_CLOSURE: str = "preferred; long_term"


# ----------------------------- post_rewrite (Wave 5 F3) -----------------------------
#
# Section 8 normalizers — port of legacy harness/review/dual_perspective.py
# adapted to the fit_diagnosis_engine spec (citation field is a spec
# extension over the legacy harness/review/ contract; default empty
# string but flag partial when the LLM omitted it).

_VALID_RATINGS: frozenset[str] = frozenset(
    {"high", "above_mid", "mid", "below_mid", "low"}
)
_VALID_DECISIONS: frozenset[str] = frozenset(
    {"push_direct", "push_with_note", "screen_out"}
)
_VALID_EFFORTS: frozenset[str] = frozenset(
    {"wording", "supplement_project", "long_term"}
)
_VALID_FILTER_VALUES: frozenset[str] = frozenset(
    {"match", "mismatch", "uncertain"}
)

_REQUIRED_POST_REWRITE_KEYS: tuple[str, ...] = (
    "competitiveness_rating",
    "hm",
    "hrbp",
    "improvement_suggestions",
    "radar",
)

_RADAR_DIM_COUNT: int = 6
_MAX_SUGGESTIONS: int = 5
_DEFAULT_AXES: tuple[str, ...] = (
    "行业经验",
    "核心技能",
    "数据能力",
    "沟通协作",
    "文化匹配",
    "JD匹配",
)


def _clamp_int(value: Any, lo: int, hi: int) -> tuple[int, bool]:
    """Coerce to int, clamp to [lo, hi]. Returns (clamped, was_inrange)."""
    if isinstance(value, bool):  # bool is subclass of int — exclude
        return lo, False
    try:
        n = int(value)
    except (TypeError, ValueError):
        return lo, False
    if n < lo:
        return lo, False
    if n > hi:
        return hi, False
    return n, True


def _clamp_float(value: Any, lo: float, hi: float) -> tuple[float, bool]:
    """Coerce to float, clamp to [lo, hi]. Returns (clamped, was_inrange)."""
    if isinstance(value, bool):
        return lo, False
    try:
        f = float(value)
    except (TypeError, ValueError):
        return lo, False
    if f < lo:
        return lo, False
    if f > hi:
        return hi, False
    return f, True


def _normalize_string_list(raw: Any) -> tuple[list[str], bool]:
    """Filter a raw value to a list of non-empty strings.

    Returns (cleaned, was_complete). was_complete is False when the raw
    value was not a list at all, or when any element was dropped.
    """
    if not isinstance(raw, list):
        return [], False
    cleaned = [s.strip() for s in raw if isinstance(s, str) and s.strip()]
    was_complete = len(cleaned) == len(raw)
    return cleaned, was_complete


def _normalize_hm(raw: Any) -> tuple[dict, bool]:
    """Coerce hm into the contract shape. Returns (hm, was_complete)."""
    if not isinstance(raw, dict):
        return (
            {"highlights": [], "concerns": [], "comparison_risk": ""},
            False,
        )

    was_complete = True

    highlights, hl_complete = _normalize_string_list(raw.get("highlights"))
    if not hl_complete:
        was_complete = False

    concerns, co_complete = _normalize_string_list(raw.get("concerns"))
    if not co_complete:
        was_complete = False

    risk = raw.get("comparison_risk")
    if not isinstance(risk, str):
        risk = ""
        was_complete = False
    else:
        risk = risk.strip()

    return (
        {
            "highlights": highlights,
            "concerns": concerns,
            "comparison_risk": risk,
        },
        was_complete,
    )


def _normalize_hard_filter_match(raw: Any) -> tuple[dict, bool]:
    """Drop entries whose value is not in the allowed enum set.

    Returns (cleaned_dict, was_complete).
    """
    if not isinstance(raw, dict):
        return {}, False
    cleaned: dict = {}
    was_complete = True
    for key, value in raw.items():
        if not isinstance(key, str):
            was_complete = False
            continue
        if value in _VALID_FILTER_VALUES:
            cleaned[key] = value
        else:
            was_complete = False
    return cleaned, was_complete


def _normalize_hrbp(raw: Any) -> tuple[dict, bool]:
    """Coerce hrbp into the contract shape. Returns (hrbp, was_complete)."""
    if not isinstance(raw, dict):
        return (
            {
                "keyword_hit_rate": 0.0,
                "hard_filter_match": {},
                "advance_decision": "screen_out",
                "decision_rationale": "",
            },
            False,
        )

    was_complete = True

    hit_rate, hit_complete = _clamp_float(raw.get("keyword_hit_rate"), 0.0, 1.0)
    if not hit_complete:
        was_complete = False

    filters, filter_complete = _normalize_hard_filter_match(
        raw.get("hard_filter_match")
    )
    if not filter_complete:
        was_complete = False

    decision = raw.get("advance_decision")
    if decision not in _VALID_DECISIONS:
        decision = "screen_out"
        was_complete = False

    rationale = raw.get("decision_rationale")
    if not isinstance(rationale, str):
        rationale = ""
        was_complete = False
    else:
        rationale = rationale.strip()

    return (
        {
            "keyword_hit_rate": hit_rate,
            "hard_filter_match": filters,
            "advance_decision": decision,
            "decision_rationale": rationale,
        },
        was_complete,
    )


def _normalize_suggestion(item: Any) -> tuple[dict | None, bool]:
    """Coerce one improvement suggestion into the contract shape.

    Returns (item, was_complete). `item` is None when the input is so
    malformed it cannot be repaired (not a dict / no usable text).
    """
    if not isinstance(item, dict):
        return None, False

    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        return None, False

    was_complete = True

    effort = item.get("effort")
    if effort not in _VALID_EFFORTS:
        effort = "wording"
        was_complete = False

    return (
        {"text": text.strip(), "effort": effort},
        was_complete,
    )


def _normalize_improvement_suggestions(raw: Any) -> tuple[list[dict], bool]:
    """Cap the suggestions list at `_MAX_SUGGESTIONS`.

    Returns (cleaned_list, was_complete).
    """
    if not isinstance(raw, list):
        return [], False

    out: list[dict] = []
    was_complete = True

    for item in raw:
        normalized, item_complete = _normalize_suggestion(item)
        if normalized is None:
            was_complete = False
            continue
        if not item_complete:
            was_complete = False
        out.append(normalized)

    if len(out) > _MAX_SUGGESTIONS:
        out = out[:_MAX_SUGGESTIONS]

    return out, was_complete


def _normalize_radar_dimension(item: Any, default_name: str) -> tuple[dict, bool]:
    """Coerce one radar dimension into the contract shape (with citation).

    Returns (dim, was_complete). Always returns a dict; on bad input the
    dict has the default_name, zero scores, empty citation, and
    was_complete is False.

    `citation` is a spec extension over harness/review/ legacy — required
    by the F3 schema but allowed to default to empty string when the LLM
    omits it (flagged partial).
    """
    if not isinstance(item, dict):
        return (
            {
                "name": default_name,
                "resume_score": 0,
                "jd_required": 0,
                "citation": "",
            },
            False,
        )

    was_complete = True

    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        name = default_name
        was_complete = False
    else:
        name = name.strip()

    resume_score, resume_in_range = _clamp_int(item.get("resume_score"), 0, 100)
    if not resume_in_range:
        was_complete = False

    jd_required, jd_in_range = _clamp_int(item.get("jd_required"), 0, 100)
    if not jd_in_range:
        was_complete = False

    if "citation" not in item:
        citation = ""
        was_complete = False
    else:
        raw_citation = item.get("citation")
        if not isinstance(raw_citation, str):
            citation = ""
            was_complete = False
        else:
            citation = raw_citation.strip()

    return (
        {
            "name": name,
            "resume_score": resume_score,
            "jd_required": jd_required,
            "citation": citation,
        },
        was_complete,
    )


def _normalize_radar(raw: Any) -> tuple[dict, bool]:
    """Coerce radar into the contract shape.

    Pads to exactly `_RADAR_DIM_COUNT` items (with zero-score placeholders
    drawn from `_DEFAULT_AXES`) or truncates from the end if too many.
    Returns (radar, was_complete).
    """
    if not isinstance(raw, dict):
        raw = {}

    dims_raw = raw.get("dimensions")
    if not isinstance(dims_raw, list):
        dims_raw = []

    was_complete = True
    if len(dims_raw) != _RADAR_DIM_COUNT:
        was_complete = False

    if len(dims_raw) > _RADAR_DIM_COUNT:
        dims_raw = dims_raw[:_RADAR_DIM_COUNT]

    dims_out: list[dict] = []
    for idx in range(_RADAR_DIM_COUNT):
        if idx < len(dims_raw):
            normalized, dim_complete = _normalize_radar_dimension(
                dims_raw[idx], _DEFAULT_AXES[idx]
            )
            if not dim_complete:
                was_complete = False
        else:
            normalized = {
                "name": _DEFAULT_AXES[idx],
                "resume_score": 0,
                "jd_required": 0,
                "citation": "",
            }
        dims_out.append(normalized)

    return {"dimensions": dims_out}, was_complete


def _normalize_post_rewrite(raw: Any) -> tuple[dict, bool]:
    """Top-level normalizer for the post_rewrite Section 8 payload.

    Returns (section_8_dict, was_complete). The returned dict carries
    competitiveness_rating + hm + hrbp + radar + improvement_suggestions.

    Common-header fields (sub_skill / mode / target_market / etc.) are
    attached by the engine layer, not here.
    """
    if not isinstance(raw, dict):
        return (
            {
                "competitiveness_rating": "mid",
                "hm": {"highlights": [], "concerns": [], "comparison_risk": ""},
                "hrbp": {
                    "keyword_hit_rate": 0.0,
                    "hard_filter_match": {},
                    "advance_decision": "screen_out",
                    "decision_rationale": "",
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
            },
            False,
        )

    was_complete = all(key in raw for key in _REQUIRED_POST_REWRITE_KEYS)

    rating = raw.get("competitiveness_rating")
    if rating not in _VALID_RATINGS:
        rating = "mid"
        was_complete = False

    hm, hm_complete = _normalize_hm(raw.get("hm"))
    if not hm_complete:
        was_complete = False

    hrbp, hrbp_complete = _normalize_hrbp(raw.get("hrbp"))
    if not hrbp_complete:
        was_complete = False

    suggestions, suggestions_complete = _normalize_improvement_suggestions(
        raw.get("improvement_suggestions")
    )
    if not suggestions_complete:
        was_complete = False

    radar, radar_complete = _normalize_radar(raw.get("radar"))
    if not radar_complete:
        was_complete = False

    return (
        {
            "competitiveness_rating": rating,
            "hm": hm,
            "hrbp": hrbp,
            "improvement_suggestions": suggestions,
            "radar": radar,
        },
        was_complete,
    )


def _normalize_bridging_or_closure(
    raw: Any, verdict: str
) -> tuple[str, bool]:
    """Validate / repair the bridging_or_closure field per verdict.

    Returns (cleaned, was_complete). Repair rules:
      - strong_match: any non-empty body becomes ""; flag partial.
      - transferable: must start with "hard;" or "preferred;" and have
        a non-empty body after the prefix.
      - missing: must start with "hard;" or "preferred;" and a closure
        horizon label after the prefix.
    """
    if verdict == "strong_match":
        if isinstance(raw, str) and raw.strip():
            return "", False
        if raw is None or raw == "":
            return "", True
        return "", False

    if not isinstance(raw, str) or not raw.strip():
        if verdict == "transferable":
            return _PLACEHOLDER_TRANSFERABLE_BRIDGE, False
        return _PLACEHOLDER_MISSING_CLOSURE, False

    body_text = raw.strip()
    if ";" not in body_text:
        if verdict == "transferable":
            return _PLACEHOLDER_TRANSFERABLE_BRIDGE, False
        return _PLACEHOLDER_MISSING_CLOSURE, False

    tier_part, _, body_part = body_text.partition(";")
    tier = tier_part.strip().lower()
    body = body_part.strip()

    if tier not in _VALID_TIERS or not body:
        if verdict == "transferable":
            return _PLACEHOLDER_TRANSFERABLE_BRIDGE, False
        return _PLACEHOLDER_MISSING_CLOSURE, False

    if verdict == "missing" and body not in _VALID_CLOSURE_HORIZONS:
        return f"{tier}; long_term", False

    return f"{tier}; {body}", True


def _normalize_matrix_row(item: Any) -> tuple[dict | None, bool]:
    """Coerce one matching_matrix row into the contract shape.

    Returns (row, was_complete). `row` is None when the input is so
    malformed it cannot be repaired (not a dict / no usable text).
    """
    if not isinstance(item, dict):
        return None, False

    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        return None, False

    was_complete = True

    verdict = item.get("verdict")
    if verdict not in _VALID_VERDICTS:
        verdict = "transferable"
        was_complete = False

    evidence = item.get("evidence")
    if not isinstance(evidence, str):
        evidence = ""
        was_complete = False

    source = item.get("source")
    if source not in _VALID_SOURCES:
        source = "section_b_priority"
        was_complete = False

    bridging, bridging_complete = _normalize_bridging_or_closure(
        item.get("bridging_or_closure"), verdict
    )
    if not bridging_complete:
        was_complete = False

    return (
        {
            "text": text.strip(),
            "evidence": evidence,
            "verdict": verdict,
            "source": source,
            "bridging_or_closure": bridging,
        },
        was_complete,
    )


def _normalize_matching_matrix(raw: Any) -> tuple[list[dict], bool]:
    """Dedup, validate, and cap the raw matching_matrix array.

    Dedup is case-insensitive on text. Cap is `_MAX_MATRIX_ITEMS`
    (12 items per spec).
    """
    if not isinstance(raw, list):
        return [], False

    out: list[dict] = []
    seen_keys: set[str] = set()
    was_complete = True

    for item in raw:
        normalized, item_complete = _normalize_matrix_row(item)
        if normalized is None:
            was_complete = False
            continue
        key = normalized["text"].lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if not item_complete:
            was_complete = False
        out.append(normalized)

    if len(out) > _MAX_MATRIX_ITEMS:
        out = out[:_MAX_MATRIX_ITEMS]

    return out, was_complete


def _normalize_boundary_can_solve(items: Any) -> tuple[list[str], bool]:
    if not isinstance(items, list):
        return [], False
    cleaned: list[str] = []
    was_complete = True
    for item in items:
        if not isinstance(item, str) or not item.strip():
            was_complete = False
            continue
        cleaned.append(item.strip())
    return cleaned, was_complete


def _normalize_boundary_cannot_solve(items: Any) -> tuple[list[str], bool]:
    """Each cannot_solve item must end with `; supplement` or `; accept`.

    When the closure path is missing or invalid, default to "accept"
    (the most conservative choice — does not promise supplemental work).
    """
    if not isinstance(items, list):
        return [], False
    cleaned: list[str] = []
    was_complete = True
    for item in items:
        if not isinstance(item, str) or not item.strip():
            was_complete = False
            continue
        body = item.strip()
        # Find last ';' — closure path is the trailing token.
        if ";" in body:
            head, _, tail = body.rpartition(";")
            tail = tail.strip()
            if tail in _VALID_BOUNDARY_PATHS:
                cleaned.append(f"{head.strip()}; {tail}")
                continue
        # Missing or invalid closure path → append default "accept".
        cleaned.append(f"{body}; accept")
        was_complete = False
    return cleaned, was_complete


def _normalize_optimization_boundary(raw: Any) -> tuple[dict, bool]:
    """Coerce optimization_boundary into the Section 4-C contract shape."""
    if not isinstance(raw, dict):
        return {"rewriting_can_solve": [], "rewriting_cannot_solve": []}, False

    was_complete = True

    can_raw = raw.get("rewriting_can_solve")
    can_solve, can_complete = _normalize_boundary_can_solve(can_raw)
    if not can_complete:
        was_complete = False

    cannot_raw = raw.get("rewriting_cannot_solve")
    cannot_solve, cannot_complete = _normalize_boundary_cannot_solve(cannot_raw)
    if not cannot_complete:
        was_complete = False

    return (
        {
            "rewriting_can_solve": can_solve,
            "rewriting_cannot_solve": cannot_solve,
        },
        was_complete,
    )


def _normalize_multi_jd_coverage_row(item: Any) -> tuple[dict | None, bool]:
    if not isinstance(item, dict):
        return None, False
    jd_id = item.get("jd_id")
    jd_title = item.get("jd_title")
    coverage_pct = item.get("coverage_pct")
    note = item.get("note")

    was_complete = True

    if not isinstance(jd_id, (str, int)) or (isinstance(jd_id, str) and not jd_id.strip()):
        return None, False
    jd_id_str = str(jd_id).strip()

    if not isinstance(jd_title, str) or not jd_title.strip():
        jd_title = "(untitled)"
        was_complete = False

    if isinstance(coverage_pct, bool) or not isinstance(coverage_pct, (int, float)):
        coverage_pct = 0
        was_complete = False
    else:
        coverage_pct = max(0, min(100, int(coverage_pct)))

    if not isinstance(note, str):
        note = ""
        was_complete = False
    else:
        note = note.strip()
        if len(note) > 50:
            note = note[:50]
            was_complete = False

    return (
        {
            "jd_id": jd_id_str,
            "jd_title": jd_title.strip(),
            "coverage_pct": coverage_pct,
            "note": note,
        },
        was_complete,
    )


def _normalize_multi_jd_coverage(
    raw: Any, *, multi_jd: bool
) -> tuple[list[dict] | None, bool, bool | None]:
    """Section 4-D: multi-JD coverage matrix.

    Returns (rows, was_complete, spread_flag).
      - When multi_jd is False → returns (None, True, None) regardless
        of input; the field is omitted from output.
      - When multi_jd is True → coerces rows; spread_flag is True iff
        (max - min) coverage_pct > 30.

    Empty list when multi_jd=True is allowed shape-wise but flagged
    as suspicious (was_complete=False).
    """
    if not multi_jd:
        return None, True, None

    if not isinstance(raw, list):
        return [], False, False

    out: list[dict] = []
    was_complete = True
    for item in raw:
        normalized, item_complete = _normalize_multi_jd_coverage_row(item)
        if normalized is None:
            was_complete = False
            continue
        if not item_complete:
            was_complete = False
        out.append(normalized)

    if not out:
        # multi_jd=True but no usable rows — allowed shape, flag partial.
        return [], False, False

    coverages = [row["coverage_pct"] for row in out]
    spread_flag = (max(coverages) - min(coverages)) > 30
    return out, was_complete, spread_flag


def _normalize_pre_rewrite(raw: Any, *, multi_jd: bool) -> tuple[dict, bool]:
    """Top-level normalizer for the pre_rewrite Section 4 payload.

    Returns (section_4_dict, was_complete). The returned dict carries
    matching_matrix + integrated_assessment + optimization_boundary +
    optional multi_jd_coverage + optional spread_flag.

    Common-header fields (sub_skill / mode / target_market / etc.) are
    attached by the engine layer, not here.
    """
    if not isinstance(raw, dict):
        return (
            {
                "matching_matrix": [],
                "integrated_assessment": "Diagnosis unavailable.",
                "optimization_boundary": {
                    "rewriting_can_solve": [],
                    "rewriting_cannot_solve": [],
                },
                "multi_jd_coverage": None,
                "spread_flag": None,
            },
            False,
        )

    was_complete = True
    for key in _REQUIRED_TOP_KEYS:
        if key not in raw:
            was_complete = False
            break

    matrix, matrix_complete = _normalize_matching_matrix(raw.get("matching_matrix"))
    if not matrix_complete:
        was_complete = False

    integrated = raw.get("integrated_assessment")
    if not isinstance(integrated, str) or not integrated.strip():
        integrated = "Integrated assessment unavailable."
        was_complete = False
    else:
        integrated = integrated.strip()

    boundary, boundary_complete = _normalize_optimization_boundary(
        raw.get("optimization_boundary")
    )
    if not boundary_complete:
        was_complete = False

    # multi_jd_coverage handling: when multi_jd=True we normalize; when
    # multi_jd=False we drop any LLM-emitted coverage to None and flag
    # partial (LLM disregarded the input flag).
    raw_coverage = raw.get("multi_jd_coverage")
    coverage, coverage_complete, spread_flag = _normalize_multi_jd_coverage(
        raw_coverage, multi_jd=multi_jd
    )
    if not coverage_complete:
        was_complete = False
    if not multi_jd and raw_coverage is not None:
        # LLM emitted coverage despite multi_jd=False → repair to None.
        was_complete = False

    return (
        {
            "matching_matrix": matrix,
            "integrated_assessment": integrated,
            "optimization_boundary": boundary,
            "multi_jd_coverage": coverage,
            "spread_flag": spread_flag,
        },
        was_complete,
    )


__all__ = [
    "_normalize_pre_rewrite",
    "_normalize_matching_matrix",
    "_normalize_optimization_boundary",
    "_normalize_multi_jd_coverage",
    "_normalize_bridging_or_closure",
    "_normalize_post_rewrite",
    "_normalize_hm",
    "_normalize_hrbp",
    "_normalize_radar",
    "_normalize_improvement_suggestions",
]
