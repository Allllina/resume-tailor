"""Unit tests for harness.master_gen.engine (Wave 4 C.1.2).

The engine is the LLM-driven port of the per-lens master generator. Every
test mocks the LLM — no real API calls. The truthfulness gate reuses the
substring helper from `harness.rewrite.truthfulness`; we exercise it via
fragments of a generated Summary.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from harness.llm.protocol import CircuitOpen
from harness.exceptions import SubSkillUnavailable
from harness.master_gen import MasterGenOutput, generate_master_for_lens


# --------------------------- fixtures ---------------------------


@pytest.fixture
def raw_files_root(tmp_path: Path) -> Path:
    root = tmp_path / "experiences"
    root.mkdir()
    (root / "01-anker.md").write_text(
        "# Anker Innovations\n\nSenior Product Manager. Built AIGC pipeline. "
        "Shipped 3 product lines. Increased GMV 25% in 12 months.",
        encoding="utf-8",
    )
    (root / "02-kearney.md").write_text(
        "# 科尔尼\n\nStrategy intern. OSAT 五年战略规划. Led downstream "
        "value chain analysis. M&A long-list screening.",
        encoding="utf-8",
    )
    (root / "03-mercer.md").write_text(
        "# Mercer\n\nHR consulting intern. Comp benchmark. Salary survey "
        "across 200 firms.",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def experiences() -> list[dict]:
    return [
        {
            "id": "01-anker",
            "company": "Anker",
            "role": "Senior PM",
            "period": "2023-2025",
            "one_line": "Built AIGC pipeline; shipped 3 product lines.",
            "vertical_fit_per_lens": {
                "C_product_ops": "core",
                "B_data_analytics": "adjacent",
                "A_strategy_research": "weak",
            },
        },
        {
            "id": "02-kearney",
            "company": "A.T. Kearney",
            "role": "Strategy Analyst Intern",
            "period": "2022",
            "one_line": "OSAT strategy and M&A longlist.",
            "vertical_fit_per_lens": {
                "A_strategy_research": "core",
                "C_product_ops": "adjacent",
                "B_data_analytics": "weak",
            },
        },
        {
            "id": "03-mercer",
            "company": "Mercer",
            "role": "HR Intern",
            "period": "2021",
            "one_line": "Comp benchmark; salary survey.",
            "vertical_fit_per_lens": {
                "HC_human_capital": "core",
                "C_product_ops": "weak",
                "A_strategy_research": "weak",
            },
        },
    ]


@pytest.fixture
def upload_tex() -> str:
    return (
        "\\documentclass{article}\n\\begin{document}\n"
        "\\section*{Summary}\nSenior PM with 3 years experience.\n"
        "\\section*{Skills}\nProduct, AIGC, GMV.\n"
        "\\section*{Experience}\n\\textbf{Anker} 2023-2025\n"
        "\\item Built AIGC pipeline; shipped 3 product lines.\n"
        "\\end{document}\n"
    )


def _llm_response(
    *,
    master_tex: str = "% generated master\n\\section*{Summary}\nLens-tailored.\n",
    included: list[str] | None = None,
    dropped: list[str] | None = None,
    summary: str = "Senior PM. Built AIGC pipeline.",
    rationale: str = "Lens fits product-ops emphasis.",
) -> str:
    return json.dumps(
        {
            "master_tex": master_tex,
            "experiences_included": included or ["01-anker"],
            "experiences_dropped": dropped or ["03-mercer"],
            "summary_text": summary,
            "decision_rationale": rationale,
        }
    )


# --------------------------- 1. happy path: single LLM call ---------------------------


@pytest.mark.asyncio
async def test_happy_path_returns_llm_method(
    upload_tex, experiences, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=_llm_response(
            master_tex="% C-tailored master tex content here",
            included=["01-anker", "02-kearney"],
            dropped=["03-mercer"],
            summary="Built AIGC pipeline. Shipped 3 product lines.",
        )
    )

    out = await generate_master_for_lens(
        upload_tex=upload_tex,
        experiences=experiences,
        raw_files_root=raw_files_root,
        lens="C_product_ops",
        target_market="mainland-china",
        llm=mock_llm,
    )

    assert isinstance(out, MasterGenOutput)
    assert out._method == "llm"
    assert out.master_tex.strip()
    assert "01-anker" in out.experiences_included
    assert "03-mercer" in out.experiences_dropped
    mock_llm.call.assert_awaited_once()


# --------------------------- 2. fail-fast on LLM CircuitOpen ---------------------------


@pytest.mark.asyncio
async def test_circuit_open_raises_subskill_unavailable(
    upload_tex, experiences, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=CircuitOpen("circuit open"))

    with pytest.raises(SubSkillUnavailable) as exc:
        await generate_master_for_lens(
            upload_tex=upload_tex,
            experiences=experiences,
            raw_files_root=raw_files_root,
            lens="C_product_ops",
            target_market="mainland-china",
            llm=mock_llm,
        )

    assert exc.value.sub_skill == "master_gen"
    assert exc.value.llm_unreachable is True


# --------------------------- 3. fail-fast on TimeoutError ---------------------------


@pytest.mark.asyncio
async def test_timeout_raises_subskill_unavailable(upload_tex, experiences, raw_files_root):
    import asyncio

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=asyncio.TimeoutError())

    with pytest.raises(SubSkillUnavailable) as exc:
        await generate_master_for_lens(
            upload_tex=upload_tex,
            experiences=experiences,
            raw_files_root=raw_files_root,
            lens="A_strategy_research",
            target_market="north-america",
            llm=mock_llm,
        )

    assert exc.value.sub_skill == "master_gen"
    assert exc.value.llm_unreachable is True


# --------------------------- 4. fail-fast on malformed JSON ---------------------------


@pytest.mark.asyncio
async def test_malformed_json_raises_subskill_unavailable(
    upload_tex, experiences, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value="Sorry, I cannot comply.")

    with pytest.raises(SubSkillUnavailable) as exc:
        await generate_master_for_lens(
            upload_tex=upload_tex,
            experiences=experiences,
            raw_files_root=raw_files_root,
            lens="C_product_ops",
            target_market="mainland-china",
            llm=mock_llm,
        )

    assert exc.value.sub_skill == "master_gen"
    assert exc.value.llm_unreachable is False


# --------------------------- 5. fail-fast on missing master_tex key ---------------------------


@pytest.mark.asyncio
async def test_empty_master_tex_raises_subskill_unavailable(
    upload_tex, experiences, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=json.dumps(
            {
                "master_tex": "",
                "experiences_included": [],
                "experiences_dropped": [],
                "summary_text": "x",
                "decision_rationale": "y",
            }
        )
    )

    with pytest.raises(SubSkillUnavailable) as exc:
        await generate_master_for_lens(
            upload_tex=upload_tex,
            experiences=experiences,
            raw_files_root=raw_files_root,
            lens="C_product_ops",
            target_market="mainland-china",
            llm=mock_llm,
        )

    assert exc.value.sub_skill == "master_gen"
    assert exc.value.llm_unreachable is False


# --------------------------- 6. None LLM → fail-fast ---------------------------


@pytest.mark.asyncio
async def test_none_llm_raises_subskill_unavailable(upload_tex, experiences, raw_files_root):
    with pytest.raises(SubSkillUnavailable) as exc:
        await generate_master_for_lens(
            upload_tex=upload_tex,
            experiences=experiences,
            raw_files_root=raw_files_root,
            lens="C_product_ops",
            target_market="mainland-china",
            llm=None,
        )

    assert exc.value.sub_skill == "master_gen"
    assert exc.value.llm_unreachable is True


# --------------------------- 7. truthfulness gate: in-bank summary stays "llm" ---------------------------


@pytest.mark.asyncio
async def test_grounded_summary_keeps_method_llm(
    upload_tex, experiences, raw_files_root
):
    mock_llm = AsyncMock()
    # Every fragment in this summary is a substring of the upload + raw bank.
    mock_llm.call = AsyncMock(
        return_value=_llm_response(
            summary="Built AIGC pipeline. Shipped 3 product lines."
        )
    )

    out = await generate_master_for_lens(
        upload_tex=upload_tex,
        experiences=experiences,
        raw_files_root=raw_files_root,
        lens="C_product_ops",
        target_market="mainland-china",
        llm=mock_llm,
    )
    assert out._method == "llm"


# --------------------------- 8. truthfulness gate: unsourced summary → llm_partial ---------------------------


@pytest.mark.asyncio
async def test_unsourced_summary_demotes_to_llm_partial(
    upload_tex, experiences, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=_llm_response(
            included=["01-anker"],
            dropped=["02-kearney", "03-mercer"],
            summary=(
                "Led $500M acquisition of unrelated company. "
                "Trained ten thousand engineers. "
                "Sold cars to outer space."
            ),
        )
    )

    out = await generate_master_for_lens(
        upload_tex=upload_tex,
        experiences=experiences,
        raw_files_root=raw_files_root,
        lens="C_product_ops",
        target_market="mainland-china",
        llm=mock_llm,
    )
    assert out._method == "llm_partial"
    # Output is still surfaced
    assert out.master_tex.strip()


# --------------------------- 9. llm=None → fail-fast (Phase 2) ---------------------------


@pytest.mark.asyncio
async def test_missing_llm_raises_sub_skill_unavailable(
    upload_tex, experiences, raw_files_root
):
    """Phase 2: master_gen no longer emits a fallback master when LLM is
    absent — it raises SubSkillUnavailable so the API layer can return
    503. The earlier "weak/missing fit → dropped on fallback path" test
    is gone because the `_excluded_by_default` helper it covered has
    been removed."""
    with pytest.raises(SubSkillUnavailable) as exc:
        await generate_master_for_lens(
            upload_tex=upload_tex,
            experiences=experiences,
            raw_files_root=raw_files_root,
            lens="A_strategy_research",
            target_market="north-america",
            llm=None,
        )
    assert exc.value.sub_skill == "master_gen"
    assert exc.value.llm_unreachable is True


# --------------------------- 10. _method round-trips through model_dump_jsonable ---------------------------


@pytest.mark.asyncio
async def test_method_round_trips_through_model_dump_jsonable(
    upload_tex, experiences, raw_files_root
):
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=_llm_response())
    out = await generate_master_for_lens(
        upload_tex=upload_tex,
        experiences=experiences,
        raw_files_root=raw_files_root,
        lens="C_product_ops",
        target_market="mainland-china",
        llm=mock_llm,
    )
    payload = out.model_dump_jsonable()
    assert payload["_method"] == out._method
    assert payload["master_tex"] == out.master_tex
    # The bare model_dump() drops _method (Pydantic v2 private attr).
    assert "_method" not in out.model_dump()


# --------------------------- 11. lens definition file loaded when repo_root present ---------------------------


@pytest.mark.asyncio
async def test_lens_definition_loaded_when_repo_root_provided(
    upload_tex, experiences, raw_files_root, repo_root
):
    """The lens definition .md should be substring-present in the user prompt."""
    captured: dict[str, str] = {}

    async def capture_call(*, system, user, max_tokens, temperature):
        captured["user"] = user
        return _llm_response()

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=capture_call)

    out = await generate_master_for_lens(
        upload_tex=upload_tex,
        experiences=experiences,
        raw_files_root=raw_files_root,
        lens="A_strategy_research",
        target_market="north-america",
        llm=mock_llm,
        repo_root=repo_root,
    )
    # Lens definition file content is embedded in the user prompt.
    assert "Lens A" in captured["user"] or "Strategy" in captured["user"]
    assert out._method in ("llm", "llm_partial")


# --------------------------- 12. invalid lens with no LLM → raises (Phase 2) ---------------------------


@pytest.mark.asyncio
async def test_unknown_lens_with_no_llm_raises(
    upload_tex, experiences, raw_files_root
):
    """Phase 2: the engine still doesn't enforce the lens enum (the API
    does), but with `llm=None` it fail-fasts before any lens-specific
    logic runs. The pre-Phase-2 contract that this test enforced ("an
    unknown lens still produces verbatim-copy output") is gone."""
    with pytest.raises(SubSkillUnavailable) as exc:
        await generate_master_for_lens(
            upload_tex=upload_tex,
            experiences=experiences,
            raw_files_root=raw_files_root,
            lens="Z_unknown_lens",
            target_market="mainland-china",
            llm=None,
        )
    assert exc.value.sub_skill == "master_gen"


# --------------------------- 13. inventory shape passed to LLM ---------------------------


@pytest.mark.asyncio
async def test_inventory_appears_in_prompt(
    upload_tex, experiences, raw_files_root
):
    captured: dict[str, str] = {}

    async def capture_call(*, system, user, max_tokens, temperature):
        captured["user"] = user
        return _llm_response()

    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=capture_call)

    await generate_master_for_lens(
        upload_tex=upload_tex,
        experiences=experiences,
        raw_files_root=raw_files_root,
        lens="C_product_ops",
        target_market="mainland-china",
        llm=mock_llm,
    )
    # All three experience ids must appear in the inventory block.
    for eid in ("01-anker", "02-kearney", "03-mercer"):
        assert eid in captured["user"]
    # Lens-fit cells must surface.
    assert "core" in captured["user"]


# --------------------------- 14. JSON wrapped in code fences is unwrapped ---------------------------


@pytest.mark.asyncio
async def test_json_in_code_fences_is_parsed(
    upload_tex, experiences, raw_files_root
):
    fenced = "```json\n" + _llm_response() + "\n```"
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=fenced)

    out = await generate_master_for_lens(
        upload_tex=upload_tex,
        experiences=experiences,
        raw_files_root=raw_files_root,
        lens="C_product_ops",
        target_market="mainland-china",
        llm=mock_llm,
    )
    assert out._method in ("llm", "llm_partial")
    assert out.master_tex.strip()
