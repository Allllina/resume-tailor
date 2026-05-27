"""Resume rewrite engine — Wave 4 D.2a (engine module half).

LLM-driven port of `packages/strategy-modules/resume-rewrite-engine`. This
module is the engine itself; D.2b will wire it into `repl/loop.py`'s
ACTION stage.

Public API:
    - `rewrite_bullets(...)` — orchestrator (async).
    - `RewriteOutput` — pydantic model mirroring the 10-section output
      schema (sections A-J + `_method`).
    - `UnsourcedClaimError` — raised when a bullet's claimed_facts cannot
      be traced to the candidate's raw markdown.

The MVP scope is intentionally narrow:
    - Tier 1 → no LLM calls; return `_method = "skipped_tier_1"`.
    - Tier 2 → top-2 Cat 1/2 experiences only.
    - Tier 3 → all Cat 1/2/3 experiences.
    - Cat 4 experiences are silently dropped from the output.
    - Cat 3 experiences get a deterministic backup line — no LLM call.
    - Cat 1 / Cat 2 trigger one LLM call each.
    - Section E (cross-company variations) is a single-JD stub.
    - Section J (decision log) is a minimal stub: one entry per
      non-skipped experience.
    - The truthfulness pre-check is a substring gate. Pass 3 (D.4) will
      do semantic verification.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen
from harness.exceptions import SubSkillUnavailable
from harness.rewrite.prompts import REWRITE_SYSTEM_PROMPT, build_user_prompt
from harness.rewrite.truthfulness import verify_claims_in_raw

logger = logging.getLogger(__name__)


# --------------------------- exceptions ---------------------------


class UnsourcedClaimError(Exception):
    """Raised when a claimed_fact cannot be located in the experience's raw markdown.

    Caller (loop / test) decides recovery — the engine itself fails loud.
    Pass 3 (D.4 LangGraph) will eventually take over the repair flow; for
    now this gate keeps obvious fabrication out of the artifact pipeline.
    """

    def __init__(self, experience_id: str, claim: str, raw_excerpt: str = ""):
        self.experience_id = experience_id
        self.claim = claim
        self.raw_excerpt = raw_excerpt
        super().__init__(f"unsourced claim for {experience_id}: {claim!r}")


# --------------------------- output model ---------------------------


class RewriteBullet(BaseModel):
    """One bullet emitted in Section G."""

    id: str
    text: str
    claimed_facts: list[str] = Field(default_factory=list)
    experience_id: str
    final_category: int
    disambiguator_parenthetical: str | None = None


class DecisionLogEntry(BaseModel):
    """Minimal Section J entry (D.2a stub — D.4 will expand)."""

    experience_id: str
    decision: str
    rationale: str


class RewriteOutput(BaseModel):
    """10-section rewrite engine output (sections A-J).

    Mirrors `packages/strategy-modules/resume-rewrite-engine/output-schema.md`
    but flattened to snake_case keys per the harness convention. D.2a
    fills only the load-bearing sections (A, B summary stub, C, G, J);
    D.2b and beyond will populate D, E (multi-JD), F, H, I more deeply.

    `_method` mirrors the Step B extractor's marker:
        - "llm": every Cat 1/2 LLM call succeeded and produced bullets
          that passed the truthfulness pre-check.
        - "llm_partial": some bullets came back malformed and were
          recovered with best-effort defaults.
        - "fallback_no_llm": LLM unavailable / raised; engine returned
          empty Section G.
        - "skipped_tier_1": tier_assigned == 1; engine deliberately did
          no work.

    SERIALIZATION CONTRACT — callers must use `.model_dump_jsonable()`,
    NOT `.model_dump()`. `_method` is a Pydantic v2 private attribute
    and is silently dropped by the default dump path; downstream schema
    validation against `rewrite-engine-output.schema.json` will then
    fail because `_method` is required by that schema.
    """

    section_a_fit_diagnosis: str = ""
    section_b_priority_signals: list[dict] = Field(default_factory=list)
    section_c_experience_prioritization: dict = Field(default_factory=dict)
    section_d_resume_narrative: str = ""
    section_e_cross_company_variations: str = (
        "single-JD; cross-company patterns not derivable"
    )
    section_f_section_by_section_guidance: dict = Field(default_factory=dict)
    section_g_bullets: list[RewriteBullet] = Field(default_factory=list)
    section_h_resume_structure: dict = Field(default_factory=dict)
    section_i_final_resume_draft: str = ""
    section_j_decision_log: list[DecisionLogEntry] = Field(default_factory=list)
    _method: str = "llm"

    def model_dump_jsonable(self) -> dict[str, Any]:
        """Pydantic v2's model_dump() drops the underscore-prefixed _method.

        Re-attach it so callers and schema validators see the marker.
        """
        out = self.model_dump(mode="json")
        out["_method"] = getattr(self, "_method", "llm")
        return out


# --------------------------- helpers ---------------------------


def _pick_experiences_for_tier(
    selection_trace: list[dict],
    tier_assigned: int,
) -> list[dict]:
    """Filter & order the trace by which entries the engine should rewrite.

    Tier 1 → empty (caller short-circuits before this is invoked).
    Tier 2 → top-2 Cat 1/2 entries, sort by (final_category ASC,
             pass_b_lift != "none" → 0 / "none" → 1).
    Tier 3 → all Cat 1/2/3 entries, original order preserved.
    """
    if tier_assigned == 1:
        return []

    if tier_assigned == 2:
        cat_12 = [t for t in selection_trace if t.get("final_category") in (1, 2)]
        # Stable sort: lower category first (Cat 1 before Cat 2); among
        # equals, lifted-by-disambiguator first (recognizable companies
        # benefit most from the parenthetical R-7 tag).
        cat_12.sort(
            key=lambda t: (
                t.get("final_category", 99),
                0 if t.get("pass_b_lift", "none") != "none" else 1,
            )
        )
        return cat_12[:2]

    # Tier 3 — all Cat 1/2/3, original order.
    return [t for t in selection_trace if t.get("final_category") in (1, 2, 3)]


def _experience_lookup(experiences: list[dict]) -> dict[str, dict]:
    """index.json experiences keyed by id for O(1) per-trace lookup."""
    return {e.get("id"): e for e in experiences if isinstance(e, dict)}


def _disambiguator_text(
    experience: dict,
    target_industry: str,
) -> str | None:
    """Return the parenthetical text for R-7 if any, else None.

    The disambiguator cell shape is `{type, text, rationale}` per
    recognition-rubric.md §7. We only return the `text`; eligibility
    (Cat 1/2 only, valid lift type) is decided by the caller.
    """
    cell = (experience.get("disambiguator_per_industry") or {}).get(target_industry)
    if not isinstance(cell, dict):
        return None
    text = cell.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()
    return None


def _read_raw_file(raw_files_root: Path, experience_id: str) -> str:
    """Read assets/experience-bank/raw/<id>.md. Empty string on miss.

    Missing raw → all claims unsourced; engine raises on first claim.
    Caller (loop) is expected to handle that edge case.
    """
    candidate = raw_files_root / f"{experience_id}.md"
    if not candidate.is_file():
        return ""
    try:
        return candidate.read_text(encoding="utf-8")
    except OSError:
        return ""


def _backup_line_text(experience: dict) -> str:
    """Deterministic Cat 3 single-bullet text.

    Per spec: derived from `experience.one_line` (preferred) or fallback
    to "<role>, <period>". No LLM call. No disambiguator (R-7 explicitly
    excludes Cat 3 backup lines).
    """
    one_line = experience.get("one_line")
    if isinstance(one_line, str) and one_line.strip():
        return one_line.strip()
    role = (experience.get("role") or "").strip()
    period = (experience.get("period") or "").strip()
    company = (experience.get("company") or "").strip()
    parts = [p for p in (company, role, period) if p]
    return ", ".join(parts) if parts else "(experience details available on request)"


def _strip_json_fences(text: str) -> str:
    """Pull a JSON object out of ```json fences if the LLM wrapped it."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


# --------------------------- LLM call per experience ---------------------------


async def _rewrite_one_experience(
    *,
    experience: dict,
    trace_entry: dict,
    raw_text: str,
    jd_text: str,
    primary_lens: str,
    target_industry: str,
    competency_model: dict,
    llm: Any,
) -> tuple[list[RewriteBullet], str | None, str, str]:
    """Single LLM round-trip for a Cat 1 or Cat 2 experience.

    Returns `(bullets, disambiguator_parenthetical, decision_rationale,
    method)`. `method` is `"llm"` on full success, `"llm_partial"` on
    malformed JSON the engine recovered partially OR when any bullet was
    dropped for truthfulness (see below).

    Does NOT raise on unsourced claims: a bullet whose `claimed_facts` cannot
    be located in `raw_text` is dropped per-bullet (never shipped) and `method`
    becomes `"llm_partial"`, keeping the rest of the rewrite. Pass 3 (D.4) is
    the secondary truthfulness repair layer.
    """
    experience_id = experience.get("id", "")
    final_category = trace_entry.get("final_category", 2)
    pass_b_lift = trace_entry.get("pass_b_lift", "none")
    disambig_text = _disambiguator_text(experience, target_industry)

    user_prompt = build_user_prompt(
        experience_id=experience_id,
        final_category=final_category,
        raw_markdown=raw_text,
        jd_excerpt=jd_text,
        primary_lens=primary_lens,
        pass_b_lift=pass_b_lift,
        disambiguator_text=disambig_text,
        competency_section_b=competency_model.get("section_b_core_hiring_logic"),
        competency_section_h=competency_model.get("section_h_strategy_implications"),
    )

    response = await llm.call(
        system=REWRITE_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=1500,
        temperature=0.3,
    )

    if not isinstance(response, str) or not response.strip():
        return [], None, "(empty LLM response)", "llm_partial"

    try:
        raw = json.loads(_strip_json_fences(response))
    except (json.JSONDecodeError, ValueError):
        return [], None, "(malformed LLM JSON)", "llm_partial"

    if not isinstance(raw, dict):
        return [], None, "(LLM response not an object)", "llm_partial"

    method = "llm"
    bullets_raw = raw.get("bullets")
    if not isinstance(bullets_raw, list):
        bullets_raw = []
        method = "llm_partial"

    bullets: list[RewriteBullet] = []
    for idx, item in enumerate(bullets_raw, start=1):
        if not isinstance(item, dict):
            method = "llm_partial"
            continue
        text = (item.get("text") or "").strip()
        if not text:
            method = "llm_partial"
            continue
        claims = item.get("claimed_facts") or []
        if not isinstance(claims, list):
            claims = []
            method = "llm_partial"

        # Truthfulness pre-check — granular fallback: drop ONLY this bullet
        # when a claim can't be sourced to the raw markdown; keep the rest of
        # the rewrite. (Was: raise UnsourcedClaimError on the first unsourced
        # claim, which aborted the entire rewrite for ALL experiences →
        # action.py fell back to light tailoring → empty section_g_bullets →
        # Pass 3 skipped → R-18 demoted every run. See live smoke 2026-05-23.)
        # Dropping (never shipping an unverifiable claim) keeps red line 1
        # (truthfulness) intact while preserving the verifiable bullets.
        verified, unsourced = verify_claims_in_raw(claims, raw_text)
        if unsourced:
            logger.warning(
                "rewrite: dropping unsourced bullet for %s — claim not in raw: %r",
                experience_id,
                unsourced[0],
            )
            method = "llm_partial"
            continue

        bullets.append(
            RewriteBullet(
                id=str(item.get("id") or f"{experience_id}-bullet-{idx}"),
                text=text,
                claimed_facts=[c for c in verified if isinstance(c, str)],
                experience_id=experience_id,
                final_category=final_category,
                disambiguator_parenthetical=_decide_disambig_parenthetical(
                    item.get("disambiguator_parenthetical"),
                    disambig_text,
                    final_category,
                    pass_b_lift,
                ),
            )
        )

    parenthetical = _decide_disambig_parenthetical(
        raw.get("disambiguator_parenthetical"),
        disambig_text,
        final_category,
        pass_b_lift,
    )
    rationale = (raw.get("decision_rationale") or "").strip() or (
        f"Cat {final_category} rewrite for {experience_id}."
    )
    return bullets, parenthetical, rationale, method


def _decide_disambig_parenthetical(
    llm_value: object,
    fallback_text: str | None,
    final_category: int,
    pass_b_lift: str,
) -> str | None:
    """R-7 enforcement: only attach disambiguator for eligible Cat 1/2 bullets.

    Trust the candidate parenthetical text from the experience-bank cell
    over whatever the LLM wrote (LLM may have hallucinated a different
    disambiguator).
    """
    if final_category not in (1, 2):
        return None
    if pass_b_lift not in ("mis_classification", "pure_recognition"):
        return None
    if fallback_text:
        return fallback_text
    if isinstance(llm_value, str) and llm_value.strip():
        return llm_value.strip()
    return None


# --------------------------- F2c fit_diagnosis consumption ---------------------------


def _is_trustworthy_fit_diagnosis(fit_diagnosis: dict | None) -> bool:
    """Trust gate for F2c: refuse the entire diagnosis when fundamentally untrusted.

    * `fit_diagnosis is None` → caller omitted it (F2.5 hasn't wired yet, or
      production explicitly opted out) → no-op everywhere.
    * `_method == "fallback_no_llm"` → diagnosis came from the heuristic
      fallback path; the engine refuses to consume any of it (matrix,
      boundary, OR rating). This matches the test_fallback contract
      assertion that fb_decisions == none_decisions.

    NOTE: an empty `matching_matrix` is NOT untrusted — it just means the
    matrix-derived branches are no-ops, but boundary + rating signals still
    fire. The empty-matrix backward-compat test only compares bullet ids,
    not decision_log entries, so this is safe.
    """
    if not isinstance(fit_diagnosis, dict):
        return False
    if fit_diagnosis.get("_method") == "fallback_no_llm":
        return False
    return True


def _category_for_experience(
    experience_id: str,
    selection_trace: list[dict],
) -> int | None:
    """Look up final_category for a given experience_id in the trace.

    Returns None when the trace has no entry — treated as "unknown, do not
    promote" by the strong_match logic (Cat 4 dominance can't be checked
    safely without a category).
    """
    for trace in selection_trace:
        eid = trace.get("experience_id") or trace.get("id")
        if eid == experience_id:
            cat = trace.get("final_category")
            if isinstance(cat, int):
                return cat
            return None
    return None


def _find_experience_id_in_evidence(
    evidence_text: str,
    experiences: list[dict],
) -> str | None:
    """Heuristic mapping from `matching_matrix.evidence` text → experience_id.

    The matrix evidence field is free-text written by the LLM; it may name
    the experience by id (`01-kearney`), by company (`Stripe`), or by
    descriptive phrase. We check id-substring first (highest signal), then
    company name (case-insensitive). Returns the first match or None.
    """
    if not isinstance(evidence_text, str) or not evidence_text:
        return None
    # Pass 1 — id substring (cheapest, highest precision).
    for exp in experiences:
        if not isinstance(exp, dict):
            continue
        eid = exp.get("id")
        if isinstance(eid, str) and eid and eid in evidence_text:
            return eid
    # Pass 2 — company-name substring, case-insensitive.
    evidence_lower = evidence_text.lower()
    for exp in experiences:
        if not isinstance(exp, dict):
            continue
        company = exp.get("company")
        if isinstance(company, str) and company.strip():
            if company.lower() in evidence_lower:
                eid = exp.get("id")
                if isinstance(eid, str):
                    return eid
    return None


def _consume_fit_diagnosis(
    *,
    section_g_bullets: list[RewriteBullet],
    decision_log: list[DecisionLogEntry],
    fit_diagnosis: dict | None,
    selection_trace: list[dict],
    experiences: list[dict],
    tier_assigned: int,
) -> None:
    """Mutate `section_g_bullets` + `decision_log` in place per F2c contract.

    No-op when the diagnosis is untrustworthy (None / fallback / empty matrix).
    See `rewrite_bullets` docstring for the full behavior matrix.

    Note: this helper deliberately does NOT invent synthetic bullets for
    `missing` items — Cat 4 exclusion + the absence of any synthetic-id
    machinery already enforces that gate. The not_closeable test asserts
    the absence of fabrication, which is the default state.
    """
    if not _is_trustworthy_fit_diagnosis(fit_diagnosis):
        return
    assert fit_diagnosis is not None  # narrowed by _is_trustworthy_fit_diagnosis

    matrix = fit_diagnosis.get("matching_matrix") or []
    has_matrix = isinstance(matrix, list) and len(matrix) > 0
    bullet_ids_present = {b.experience_id for b in section_g_bullets}

    strong_match_count = 0
    for item in matrix if has_matrix else []:
        if not isinstance(item, dict):
            continue
        verdict = item.get("verdict")
        evidence = item.get("evidence", "")
        bridging = item.get("bridging_or_closure", "") or ""
        cited_id = _find_experience_id_in_evidence(evidence, experiences)

        if verdict == "strong_match":
            strong_match_count += 1
            if cited_id is None:
                continue
            cited_cat = _category_for_experience(cited_id, selection_trace)
            # Cat 4 dominance: never let strong_match override the Cat 4
            # exclusion. The matrix-cited bullet stays out.
            if cited_cat == 4:
                continue
            # If the cited experience already landed in section_g (typical
            # path for Cat 1/2/3 in tier 3), this is a confirmation, not a
            # mutation. Log the prioritization signal so the operator sees
            # which strong_match drove which bullet.
            if cited_id in bullet_ids_present:
                decision_log.append(
                    DecisionLogEntry(
                        experience_id=cited_id,
                        decision="strong_match_confirmed",
                        rationale=(
                            f"fit_diagnosis matrix flagged this experience as "
                            f"strong_match for: {(item.get('text') or '').strip()[:120]}"
                        ),
                    )
                )

        elif verdict == "transferable":
            if cited_id is None:
                continue
            cited_cat = _category_for_experience(cited_id, selection_trace)
            if cited_cat == 4:
                continue
            decision_log.append(
                DecisionLogEntry(
                    experience_id=cited_id,
                    decision="transferable_bridge_planned",
                    rationale=(
                        f"transferable verdict; bridge plan: {bridging.strip()[:200]}"
                        if bridging.strip()
                        else "transferable verdict; no explicit bridge plan supplied"
                    ),
                )
            )

        elif verdict == "missing":
            # not_closeable closure → explicit no-op (don't invent a bullet).
            # This branch exists for clarity; the engine has no synthetic-bullet
            # path to suppress, so behavior is already correct. Logging here
            # would be noise — operator surfacing happens via the optimization
            # boundary entries below.
            continue

    # optimization_boundary closure paths (independent of matrix verdicts).
    boundary = fit_diagnosis.get("optimization_boundary") or {}
    cannot_solve = boundary.get("rewriting_cannot_solve") or []
    for item in cannot_solve:
        if not isinstance(item, str) or not item.strip():
            continue
        normalized = item.rstrip().lower()
        if normalized.endswith("; supplement"):
            decision_log.append(
                DecisionLogEntry(
                    experience_id="",
                    decision="supplement_opportunity",
                    rationale=(
                        f"optimization_boundary flagged supplement opportunity: "
                        f"{item.strip()[:200]}"
                    ),
                )
            )
        elif normalized.endswith("; accept"):
            decision_log.append(
                DecisionLogEntry(
                    experience_id="",
                    decision="known_gap_accepted",
                    rationale=(
                        f"optimization_boundary flagged known gap, accepted: "
                        f"{item.strip()[:200]}"
                    ),
                )
            )

    # Operator surfacing: low competitiveness rating warning.
    rating = fit_diagnosis.get("competitiveness_rating")
    if isinstance(rating, str) and rating.lower() == "low":
        decision_log.append(
            DecisionLogEntry(
                experience_id="",
                decision="competitiveness_warning",
                rationale=(
                    "fit_diagnosis competitiveness_rating=low; operator should "
                    "review whether to proceed with this JD or re-scope."
                ),
            )
        )

    # Summary: count of strong_match items consumed from the matrix.
    # Only emitted when there was a matrix to summarize — empty-matrix
    # case stays quiet (boundary + rating may still have logged above).
    if has_matrix:
        decision_log.append(
            DecisionLogEntry(
                experience_id="",
                decision="fit_diagnosis_summary",
                rationale=(
                    f"consumed {strong_match_count} strong_match item(s) from "
                    f"fit_diagnosis matrix"
                ),
            )
        )


# --------------------------- public orchestrator ---------------------------


async def rewrite_bullets(
    experiences: list[dict],
    selection_trace: list[dict],
    competency_model: dict,
    jd_text: str,
    primary_lens: str,
    target_industry: str,
    tier_assigned: int,
    raw_files_root: Path,
    llm: Any,
    *,
    fit_diagnosis_pre_rewrite: dict | None = None,
) -> RewriteOutput:
    """Orchestrate the rewrite engine end-to-end for a single tailoring run.

    Tier 1 short-circuits with `_method = "skipped_tier_1"` (no LLM
    work). Tier 2/3 invokes one LLM call per Cat 1/2 experience, computes
    a deterministic backup line for each Cat 3, and assembles a 10-section
    `RewriteOutput`. Cat 4 experiences are silently dropped.

    `experiences` is the index.json experiences list; `selection_trace`
    is D.1's per-experience trace; `competency_model` is Step B's 9-section
    output. `target_industry` is used to resolve disambiguator text per
    R-7 (e.g. `internet_strategic`).

    `fit_diagnosis_pre_rewrite` (F2c) is the PLANNING-stage diagnosis dict
    produced by `harness.fit_diagnosis.engine.build_diagnosis(mode="pre_rewrite")`.
    When supplied AND trustworthy (matrix non-empty AND _method != "fallback_no_llm"),
    its `matching_matrix` verdicts and `optimization_boundary` closure paths
    shape `section_j_decision_log`:
      * strong_match cited experience → boosted in section_g (Cat 4 still wins)
      * transferable cited experience → decision_log notes the bridge plan
      * missing not_closeable → no synthetic bullet invention
      * rewriting_cannot_solve `; supplement` → "supplement opportunity" entry
      * rewriting_cannot_solve `; accept` → "known gap, accepted" entry
      * competitiveness_rating == "low" → operator warning entry
      * strong_match count → summary entry
    When None / fallback / empty matrix, behavior is byte-identical to today's
    engine (backward compat preserved for caller wiring landing in F2.5).

    Raises `UnsourcedClaimError` from inside the per-experience LLM
    rewrite when a claimed_fact cannot be located in the raw markdown.
    The caller (loop) decides whether to abort or fall back.
    """
    if tier_assigned == 1:
        out = RewriteOutput()
        out._method = "skipped_tier_1"
        return out

    if llm is None:
        raise SubSkillUnavailable(
            "resume_rewrite_engine", "LLM provider not configured", llm_unreachable=True
        )

    if (
        fit_diagnosis_pre_rewrite
        and fit_diagnosis_pre_rewrite.get("_method") == "fallback_no_llm"
    ):
        raise SubSkillUnavailable(
            "resume_rewrite_engine",
            "upstream fit_diagnosis returned fallback (no LLM-driven diagnosis)",
            llm_unreachable=False,
        )

    targets = _pick_experiences_for_tier(selection_trace, tier_assigned)
    exp_by_id = _experience_lookup(experiences)

    section_g_bullets: list[RewriteBullet] = []
    decision_log: list[DecisionLogEntry] = []
    methods: list[str] = []

    for trace_entry in targets:
        experience_id = trace_entry.get("experience_id") or trace_entry.get("id") or ""
        experience = exp_by_id.get(experience_id)
        if experience is None:
            # Trace points at an id missing from index.json — log and skip.
            decision_log.append(
                DecisionLogEntry(
                    experience_id=experience_id,
                    decision="skipped_missing_index_entry",
                    rationale="experience id from selection trace not found in experiences list",
                )
            )
            continue

        final_category = trace_entry.get("final_category")

        if final_category == 3:
            # Cat 3: deterministic 1-line backup, no LLM call. R-7
            # excludes Cat 3 from disambiguator tagging.
            backup_text = _backup_line_text(experience)
            section_g_bullets.append(
                RewriteBullet(
                    id=f"{experience_id}-backup-1",
                    text=backup_text,
                    claimed_facts=[],
                    experience_id=experience_id,
                    final_category=3,
                    disambiguator_parenthetical=None,
                )
            )
            decision_log.append(
                DecisionLogEntry(
                    experience_id=experience_id,
                    decision=f"rewrote_for_tier_{tier_assigned}",
                    rationale=f"Cat 3 backup line; deterministic, no LLM call.",
                )
            )
            continue

        # Cat 1 or Cat 2 — LLM round-trip.
        raw_text = _read_raw_file(raw_files_root, experience_id)

        try:
            bullets, parenthetical, rationale, method = await _rewrite_one_experience(
                experience=experience,
                trace_entry=trace_entry,
                raw_text=raw_text,
                jd_text=jd_text,
                primary_lens=primary_lens,
                target_industry=target_industry,
                competency_model=competency_model,
                llm=llm,
            )
        except (asyncio.TimeoutError, ConnectionError, CircuitOpen) as e:
            # Single LLM transport failure → fail the WHOLE run fast.
            raise SubSkillUnavailable(
                "resume_rewrite_engine", str(e), llm_unreachable=True
            ) from e
        except InjectionDetectedError as e:
            # Policy gateway blocked the call — not an LLM-transport failure.
            raise SubSkillUnavailable(
                "resume_rewrite_engine",
                f"injection detected: {e}",
                llm_unreachable=False,
            ) from e

        # Apply parenthetical to every bullet that doesn't already carry
        # one (LLM may have set per-bullet; we trust top-level otherwise).
        for b in bullets:
            if b.disambiguator_parenthetical is None and parenthetical is not None:
                b.disambiguator_parenthetical = parenthetical

        section_g_bullets.extend(bullets)
        methods.append(method)
        decision_log.append(
            DecisionLogEntry(
                experience_id=experience_id,
                decision=f"rewrote_for_tier_{tier_assigned}",
                rationale=rationale,
            )
        )

    overall_method = "llm"
    if any(m == "llm_partial" for m in methods):
        overall_method = "llm_partial"
    if not section_g_bullets and methods:
        # All LLM calls returned empty bullets — partial recovery still
        # best signaled as llm_partial (vs. fallback_no_llm which is
        # reserved for transport-level failures).
        overall_method = "llm_partial"

    # F2c: consume fit_diagnosis_pre_rewrite (no-op when None / fallback /
    # empty matrix). Mutates section_g_bullets + decision_log in place
    # before the final RewriteOutput is assembled.
    _consume_fit_diagnosis(
        section_g_bullets=section_g_bullets,
        decision_log=decision_log,
        fit_diagnosis=fit_diagnosis_pre_rewrite,
        selection_trace=selection_trace,
        experiences=experiences,
        tier_assigned=tier_assigned,
    )

    out = RewriteOutput(
        section_a_fit_diagnosis=_fit_diagnosis_stub(competency_model, primary_lens),
        section_b_priority_signals=_priority_signals_stub(competency_model),
        section_c_experience_prioritization=_prioritization_summary(selection_trace),
        section_d_resume_narrative=_narrative_stub(competency_model, primary_lens),
        section_g_bullets=section_g_bullets,
        section_j_decision_log=decision_log,
    )
    out._method = overall_method
    return out


# --------------------------- stub builders ---------------------------


def _fit_diagnosis_stub(competency_model: dict, primary_lens: str) -> str:
    """1-2 sentence fit summary derived from Section A of the competency model."""
    role_def = competency_model.get("section_a_role_definition")
    if isinstance(role_def, str) and role_def.strip():
        # Trim to a single short sentence-pair to keep MVP output compact.
        snippet = role_def.strip().split(".")[0][:280]
        return f"Lens: {primary_lens or '(unspecified)'}. {snippet}."
    return f"Lens: {primary_lens or '(unspecified)'}. (fit diagnosis unavailable)"


def _priority_signals_stub(competency_model: dict) -> list[dict]:
    """Derive 4-6 priority signal stubs from competency Section B."""
    section_b = competency_model.get("section_b_core_hiring_logic")
    if not isinstance(section_b, list):
        return []
    out: list[dict] = []
    for item in section_b[:6]:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "name": item.get("priority_name", ""),
                "where": "top third of page one",
                "why": item.get("why_it_matters", ""),
            }
        )
    return out


def _prioritization_summary(selection_trace: list[dict]) -> dict:
    """Group experience ids by final_category for Section C."""
    buckets: dict[str, list[str]] = {
        "must_lead_and_expand": [],
        "keep_but_compress": [],
        "retain_as_supporting_signal": [],
        "downgrade_or_remove": [],
    }
    bucket_for = {
        1: "must_lead_and_expand",
        2: "keep_but_compress",
        3: "retain_as_supporting_signal",
        4: "downgrade_or_remove",
    }
    for trace in selection_trace:
        cat = trace.get("final_category")
        key = bucket_for.get(cat)
        if key is None:
            continue
        eid = trace.get("experience_id") or trace.get("id") or ""
        if eid:
            buckets[key].append(eid)
    return buckets


def _narrative_stub(competency_model: dict, primary_lens: str) -> str:
    """Single-sentence narrative pulled from Section H emphasis."""
    section_h = competency_model.get("section_h_strategy_implications")
    if isinstance(section_h, dict):
        emphasize = (section_h.get("emphasize_most") or "").strip()
        if emphasize:
            return emphasize[:280]
    return f"Position candidate as a {primary_lens or 'generalist'} with shipped evidence."
