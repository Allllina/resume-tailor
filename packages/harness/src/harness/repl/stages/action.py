"""ACTION stage."""
from pathlib import Path

from harness.competency.extractor import (
    section_d_keywords,
    section_h_strategy_hints,
)
from harness.rewrite import rewrite_bullets, UnsourcedClaimError
from harness.tier1.bullet_injector import inject_bullets
from harness.tier1.diff_extractor import extract_skills_block, extract_summary_block

from ..eval import Tier1Tools
from ..read import assemble_tier1_context
from ..state import RunState
from ._helpers import _emit_call_metrics


async def run_action(
    state: RunState,
    jd_text: str,
    target_market: str,
    repo_root: Path,
    tools: Tier1Tools,
    routing: dict,
    master_tex: str,
    target_industry: str,
    index_data: dict,
) -> str:
    """Mutates state. Returns final_tex (the tex string ready to write to disk)."""
    # WHY (W4 D.2b): Tier 2/3 dispatch to the rewrite engine first. The
    # engine returns a 10-section RewriteOutput; we inject Section G
    # bullets into the master tex via bullet_injector, then fall through
    # to Tier 1 light tailoring (skill_injector + summary_writer +
    # summary_injector) so the surface (skills row, summary) gets the
    # same treatment Tier 1 runs do — defense-in-depth per
    # ARCHITECTURE.md §9. Tier 1 path is unchanged: it skips the engine
    # block entirely.
    rewrite_output = None
    bullets_per_experience: dict[str, list[str]] = {}
    # D11 — pick raw experience dir (private real path preferred, sample fallback).
    raw_real = repo_root / "assets/experience-bank/raw"
    raw_sample = repo_root / "assets/experience-bank/raw.sample"
    raw_files_root = raw_real if raw_real.is_dir() and any(raw_real.iterdir()) else raw_sample
    if state.tier in (2, 3):
        try:
            rewrite_output = await rewrite_bullets(
                experiences=index_data.get("experiences", []),
                selection_trace=state.experience_selection_trace,
                competency_model=state.competency_model or {},
                jd_text=jd_text,
                primary_lens=routing.get("primary_lens", ""),
                target_industry=target_industry,
                tier_assigned=state.tier,
                raw_files_root=raw_files_root,
                llm=tools.llm,
            )
            state.rewrite_engine_output = rewrite_output.model_dump_jsonable()
            state.add_event(
                "action",
                "rewrite_engine_completed",
                {
                    "method": rewrite_output._method,
                    "bullet_count": len(rewrite_output.section_g_bullets),
                },
            )
            await _emit_call_metrics(state, tools, "action", "rewrite_engine_call")

            # Group Section G bullets by experience_id for the injector.
            for b in rewrite_output.section_g_bullets:
                eid = getattr(b, "experience_id", None)
                if not eid:
                    continue
                bullet_text = (b.text or "").strip()
                if b.disambiguator_parenthetical:
                    bullet_text = f"{bullet_text} ({b.disambiguator_parenthetical})"
                bullets_per_experience.setdefault(eid, []).append(bullet_text)
        except UnsourcedClaimError as e:
            # Defensive: the engine now drops unsourced bullets per-bullet
            # rather than raising, so this is unreachable from the normal
            # path — but a future strict mode (or a direct caller) may still
            # raise it, and test_repl_loop locks this graceful handling.
            state.add_degradation(
                "action",
                f"rewrite engine raised UnsourcedClaimError: {e.experience_id} / {e.claim!r}",
                "fall back to Tier 1 light tailoring (skip rewrite)",
            )
        except Exception as e:
            state.add_degradation(
                "action",
                f"rewrite engine failed: {e}",
                "fall back to Tier 1 light tailoring (skip rewrite)",
            )

    ctx = assemble_tier1_context(
        jd_text=jd_text,
        master_tex=master_tex,
        index_slice=index_data,
        target_industry=target_industry,
        target_lens=routing["primary_lens"],
    )

    # Inject rewritten bullets into the master tex BEFORE skill / summary
    # passes so the deterministic Tier 1 transforms operate on the latest
    # body. Failures are non-fatal: skipped experiences keep their master
    # bullets and we record a degradation.
    if bullets_per_experience:
        try:
            new_master_tex, skipped = inject_bullets(
                ctx["master_tex"],
                bullets_per_experience,
                index_data.get("experiences", []),
            )
            ctx["master_tex"] = new_master_tex
            state.add_event(
                "action",
                "bullets_injected",
                {
                    "injected_experience_count": len(bullets_per_experience) - len(skipped),
                    "skipped_count": len(skipped),
                },
            )
            if skipped:
                state.add_degradation(
                    "action",
                    f"rewrite engine produced bullets for {len(skipped)} experiences not locatable in tex: {skipped}",
                    "those experiences kept master bullets",
                )
        except Exception as e:
            state.add_degradation(
                "action",
                f"bullet injection failed: {e}",
                "tex without rewritten bullets",
            )

    # Skill injection (deterministic, no LLM)
    skills_before = extract_skills_block(ctx["master_tex"])
    competency_extra_keywords = section_d_keywords(state.competency_model)
    try:
        new_tex = tools.skill_injector.reorder_skills_section(
            ctx["master_tex"],
            jd_text,
            extra_keywords=competency_extra_keywords or None,
        )
        state.add_event("action", "skills_reordered", {})
        skills_after = extract_skills_block(new_tex)
        if skills_before and skills_after and skills_before != skills_after:
            state.change_cards.append({
                "title": "Skills row reordered",
                "before": skills_before,
                "after": skills_after,
                "note": "Items lifted toward front by JD relevance",
                "source_event": "skills_reordered",
            })
    except Exception as e:
        state.add_degradation("action", f"skill injector failed: {e}", "use master tex unchanged")
        new_tex = ctx["master_tex"]

    # Summary regeneration (LLM, optional — graceful degrade on failure)
    summary_text = ""
    try:
        candidate_tags: list[str] = []  # Wave 2: derive from index.json
        summary_strategy_hints = section_h_strategy_hints(state.competency_model)
        summary_text = await tools.summary_writer.write(
            jd_excerpt=jd_text[:500],
            lens=routing["primary_lens"],
            candidate_tags=candidate_tags,
            strategy_hints=summary_strategy_hints,
        )
        state.add_event("action", "summary_written", {"chars": len(summary_text)})
        await _emit_call_metrics(state, tools, "action", "summary_writer_call")
    except Exception as e:
        from harness.exceptions import SubSkillUnavailable
        if isinstance(e, SubSkillUnavailable):
            raise
        state.add_degradation("action", f"summary writer failed: {e}", "skip summary regen")

    # Inject Summary into tex (no-op if empty)
    if summary_text:
        summary_before = extract_summary_block(ctx["master_tex"]) or "(no Summary section)"
        try:
            new_tex = tools.summary_injector(new_tex, summary_text)
            state.add_event("action", "summary_injected", {"chars": len(summary_text)})
            state.change_cards.append({
                "title": "Summary regenerated",
                "before": summary_before,
                "after": summary_text,
                "note": f"Tone shifted toward {routing.get('primary_lens', '?')} vocabulary",
                "source_event": "summary_written",
            })
        except Exception as e:
            state.add_degradation("action", f"summary injection failed: {e}", "tex without Summary section")

    return new_tex
