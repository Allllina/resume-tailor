"""Project-wide harness exceptions.

Currently holds `SubSkillUnavailable` — the contract between critical
sub-skills (competency_extractor, fit_diagnosis_*, master_gen, rewrite_engine,
gap_bridging_planner, pass3_verifier, summary_writer) and the API surface
under Phase 2 of the fail-fast refactor.

See `docs/plans/2026-05-12-phase2-remove-per-subskill-fallback.md` (Phase 2.A).
Until Phase 2.B lands, sub-skills still return fallback outputs; this class
exists so the API layer can be wired ahead of the sub-skill conversions.
"""
from __future__ import annotations


class SubSkillUnavailable(Exception):
    """A critical sub-skill could not produce usable output.

    Raised by sub-skills (replacing the previous "graceful fallback" pattern)
    when the LLM is unreachable, returns malformed output, or ground truth
    is missing in a way that makes the requested output meaningless. The
    API layer catches this and returns HTTP 503 with structured detail per
    `docs/plans/2026-05-12-phase2-remove-per-subskill-fallback.md` Phase 2.D.

    Parameters
    ----------
    sub_skill:
        Stable identifier matching the sub-skill name used in
        `substance_check.diagnostic_failed_sub_skills` and SKILL.md (e.g.
        ``"fit_diagnosis_post_rewrite"``, ``"rewrite_engine"``,
        ``"competency_extractor"``).
    reason:
        Human-readable cause — pass through ``str(underlying_exception)`` or
        a short phrase like ``"empty LLM response"``. Surfaced verbatim to
        the UI in the 503 body, so keep it user-meaningful.
    llm_unreachable:
        True iff the underlying error indicates the LLM transport itself
        failed (``ConnectionError``, ``CircuitOpen``, ``asyncio.TimeoutError``).
        UI uses this to pick the "LLM is down" copy variant vs. "sub-skill
        returned bad data" variant.
    """

    def __init__(
        self,
        sub_skill: str,
        reason: str,
        llm_unreachable: bool = False,
    ) -> None:
        self.sub_skill = sub_skill
        self.reason = reason
        self.llm_unreachable = llm_unreachable
        super().__init__(f"{sub_skill}: {reason}")

    def to_503_detail(self, retry_after: int = 30) -> dict:
        """Build the structured detail dict returned in HTTP 503 responses.

        Shape matches Phase 2.D in the plan + the UI's expected envelope.
        """
        return {
            "code": "sub_skill_unavailable",
            "sub_skill": self.sub_skill,
            "reason": self.reason,
            "llm_unreachable": self.llm_unreachable,
            "retry_after": retry_after,
        }
