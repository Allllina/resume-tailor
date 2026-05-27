"""Unit tests for harness.verify (Wave 4 D.4a).

Covers the 4 LangGraph node functions individually + the verify_bullets
orchestrator + a build_graph smoke test. Mock LLMs via AsyncMock — no real
API calls.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from harness.llm.protocol import CircuitOpen
from harness.verify import build_graph, verify_bullets
from harness.verify.nodes import (
    _make_aggregate_verdict_node,
    _make_classify_unsourced_node,
    _make_extract_claims_node,
    _make_ground_claim_node,
)
from harness.verify.state import VerifyState


# =========================================================================
# Node 1 — extract_claims_node
# =========================================================================


@pytest.mark.asyncio
async def test_extract_claims_passes_through_pre_extracted_facts():
    """When bullet has non-empty claimed_facts → no LLM call, claims pass through."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock()  # spy: should NOT be called

    node = _make_extract_claims_node(mock_llm)
    state: VerifyState = {
        "bullet": {
            "id": "b1",
            "text": "Led 5-person team to deliver Q3 launch.",
            "claimed_facts": ["Led 5-person team", "Delivered Q3 launch"],
        },
    }

    out = await node(state)

    assert out["extracted_claims"] == ["Led 5-person team", "Delivered Q3 launch"]
    assert out["extraction_degraded"] is False
    mock_llm.call.assert_not_called()


@pytest.mark.asyncio
async def test_extract_claims_calls_llm_when_claimed_facts_empty():
    """Empty claimed_facts + valid LLM JSON list → parsed claims, no degradation."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value='["Built data pipeline", "Reduced latency by 30%"]'
    )

    node = _make_extract_claims_node(mock_llm)
    state: VerifyState = {
        "bullet": {
            "id": "b1",
            "text": "Built a data pipeline that reduced latency 30%.",
            "claimed_facts": [],
        },
    }

    out = await node(state)

    assert out["extracted_claims"] == ["Built data pipeline", "Reduced latency by 30%"]
    assert out["extraction_degraded"] is False
    mock_llm.call.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_claims_falls_back_when_llm_raises():
    """LLM raises CircuitOpen → fallback single-claim list + degradation flag."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=CircuitOpen("breaker open"))

    node = _make_extract_claims_node(mock_llm)
    state: VerifyState = {
        "bullet": {
            "id": "b1",
            "text": "Did some thing involving widgets.",
            "claimed_facts": None,
        },
    }

    out = await node(state)

    assert out["extracted_claims"] == ["Did some thing involving widgets."]
    assert out["extraction_degraded"] is True


@pytest.mark.asyncio
async def test_extract_claims_falls_back_on_malformed_json():
    """LLM returns non-JSON garbage → fallback to single-claim list."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value="not json {{{")

    node = _make_extract_claims_node(mock_llm)
    state: VerifyState = {
        "bullet": {
            "id": "b1",
            "text": "Bullet prose without pre-extraction.",
            "claimed_facts": [],
        },
    }

    out = await node(state)

    assert out["extracted_claims"] == ["Bullet prose without pre-extraction."]
    assert out["extraction_degraded"] is True


# =========================================================================
# Node 2 — ground_claim_node
# =========================================================================


@pytest.mark.asyncio
async def test_ground_claim_all_substring_matches_no_llm():
    """All claims pass Layer 1 substring → no LLM call, all verified."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock()

    node = _make_ground_claim_node(mock_llm)
    state: VerifyState = {
        "extracted_claims": ["led the team", "deliver Q3"],
        "source_text": "I led the team to deliver Q3 with on-time targets.",
    }

    out = await node(state)

    results = out["grounded_results"]
    assert len(results) == 2
    assert all(r["verdict"] == "verified" for r in results)
    assert out["layer_2_failures"] == []
    mock_llm.call.assert_not_called()


@pytest.mark.asyncio
async def test_ground_claim_layer2_promotes_paraphrase_to_verified():
    """Layer 2 LLM says verified → claim moves from unsourced to verified."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=json.dumps(
            {"verified": True, "source_snippet": "supervised five engineers"}
        )
    )

    node = _make_ground_claim_node(mock_llm)
    state: VerifyState = {
        "extracted_claims": ["managed 5 engineers"],
        "source_text": "I supervised five engineers across two squads.",
    }

    out = await node(state)

    results = out["grounded_results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "verified"
    assert "paraphrase" in (results[0]["source"] or "")
    assert out["layer_2_failures"] == []


@pytest.mark.asyncio
async def test_ground_claim_layer2_unverified_stays_unsourced():
    """Layer 2 LLM says unverified → claim stays unsourced."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=json.dumps({"verified": False, "source_snippet": None})
    )

    node = _make_ground_claim_node(mock_llm)
    state: VerifyState = {
        "extracted_claims": ["fabricated stat 99%"],
        "source_text": "Some unrelated source content here.",
    }

    out = await node(state)

    results = out["grounded_results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "unsourced"
    assert results[0]["source"] is None


@pytest.mark.asyncio
async def test_ground_claim_records_layer2_failure_on_llm_raise():
    """LLM CircuitOpen during Layer 2 → claim unsourced + recorded in failures."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=CircuitOpen("breaker open"))

    node = _make_ground_claim_node(mock_llm)
    state: VerifyState = {
        "extracted_claims": ["claim that needs paraphrase check"],
        "source_text": "Source that does not contain the claim verbatim.",
    }

    out = await node(state)

    results = out["grounded_results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "unsourced"
    assert results[0]["claim"] in out["layer_2_failures"]


@pytest.mark.asyncio
async def test_ground_claim_empty_source_marks_all_unsourced():
    """Empty source_text → no Layer 1 hit, no LLM call, all unsourced."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock()

    node = _make_ground_claim_node(mock_llm)
    state: VerifyState = {
        "extracted_claims": ["any claim"],
        "source_text": "",
    }

    out = await node(state)

    results = out["grounded_results"]
    assert len(results) == 1
    assert results[0]["verdict"] == "unsourced"
    # llm not called because source_text is empty (skip-Layer-2 guard).
    mock_llm.call.assert_not_called()


@pytest.mark.asyncio
async def test_ground_claim_empty_input_yields_empty_output():
    """No claims → no results, no LLM."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock()

    node = _make_ground_claim_node(mock_llm)
    state: VerifyState = {
        "extracted_claims": [],
        "source_text": "irrelevant",
    }

    out = await node(state)

    assert out["grounded_results"] == []
    assert out["layer_2_failures"] == []
    mock_llm.call.assert_not_called()


# =========================================================================
# Node 3 — classify_unsourced_node
# =========================================================================


@pytest.mark.asyncio
async def test_classify_numeric_claim_routes_to_ask_user():
    node = _make_classify_unsourced_node(llm=None)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "increased revenue by 42%", "verdict": "unsourced", "source": None},
        ],
    }
    out = await node(state)
    assert len(out["classified_unsourced"]) == 1
    assert out["classified_unsourced"][0]["action"] == "ask_user"


@pytest.mark.asyncio
async def test_classify_subjective_claim_routes_to_remove():
    node = _make_classify_unsourced_node(llm=None)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "world-class delivery cadence", "verdict": "unsourced", "source": None},
        ],
    }
    out = await node(state)
    assert out["classified_unsourced"][0]["action"] == "remove"


@pytest.mark.asyncio
async def test_classify_plain_claim_routes_to_mark_tbd():
    node = _make_classify_unsourced_node(llm=None)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "led migration to new platform", "verdict": "unsourced", "source": None},
        ],
    }
    out = await node(state)
    assert out["classified_unsourced"][0]["action"] == "mark_TBD"


@pytest.mark.asyncio
async def test_classify_empty_input_yields_empty_output():
    node = _make_classify_unsourced_node(llm=None)
    state: VerifyState = {"grounded_results": []}
    out = await node(state)
    assert out["classified_unsourced"] == []


@pytest.mark.asyncio
async def test_classify_multiple_types_each_get_their_own_action():
    """Mixed unsourced claims → each gets its own action by heuristic."""
    node = _make_classify_unsourced_node(llm=None)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "improved efficiency by 20%", "verdict": "unsourced", "source": None},
            {"claim": "industry-leading platform", "verdict": "unsourced", "source": None},
            {"claim": "owned the migration end-to-end", "verdict": "unsourced", "source": None},
            {"claim": "verified by substring", "verdict": "verified", "source": "raw § ..."},
        ],
    }
    out = await node(state)
    actions = [c["action"] for c in out["classified_unsourced"]]
    assert actions == ["ask_user", "remove", "mark_TBD"]


# ---- D.4b: LLM-driven classify_unsourced ----


@pytest.mark.asyncio
async def test_classify_unsourced_uses_llm_when_available():
    """LLM returns valid JSON → its action is honoured (not the heuristic)."""
    # Numeric claim would heuristically map to ask_user; we make the LLM
    # disagree and pick mark_TBD to prove the LLM path is taken.
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=json.dumps(
            {"action": "mark_TBD", "rationale": "LLM-chosen rationale here."}
        )
    )

    node = _make_classify_unsourced_node(mock_llm)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "increased revenue by 42%", "verdict": "unsourced", "source": None},
        ],
    }

    out = await node(state)

    assert len(out["classified_unsourced"]) == 1
    assert out["classified_unsourced"][0]["action"] == "mark_TBD"
    assert out["classified_unsourced"][0]["rationale"] == "LLM-chosen rationale here."
    assert out["classify_degraded"] is False
    mock_llm.call.assert_awaited_once()


@pytest.mark.asyncio
async def test_classify_unsourced_falls_back_to_heuristics_on_llm_raise():
    """LLM CircuitOpen → heuristic decides; degraded flag flips to True."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(side_effect=CircuitOpen("breaker open"))

    node = _make_classify_unsourced_node(mock_llm)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "world-class delivery cadence", "verdict": "unsourced", "source": None},
        ],
    }

    out = await node(state)

    # Heuristic path: subjective lexicon hit → remove.
    assert out["classified_unsourced"][0]["action"] == "remove"
    assert out["classify_degraded"] is True


@pytest.mark.asyncio
async def test_classify_unsourced_falls_back_on_malformed_json():
    """LLM returns non-JSON garbage → heuristic decides; degraded=True."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value="not really json {[")

    node = _make_classify_unsourced_node(mock_llm)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "increased revenue by 42%", "verdict": "unsourced", "source": None},
        ],
    }

    out = await node(state)

    # Heuristic for numeric claim → ask_user.
    assert out["classified_unsourced"][0]["action"] == "ask_user"
    assert out["classify_degraded"] is True


@pytest.mark.asyncio
async def test_classify_unsourced_falls_back_on_invalid_action_value():
    """LLM returns valid JSON with `action` outside enum → fallback + degraded."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=json.dumps({"action": "bogus", "rationale": "?"})
    )

    node = _make_classify_unsourced_node(mock_llm)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "owned the migration end-to-end", "verdict": "unsourced", "source": None},
        ],
    }

    out = await node(state)

    # Heuristic for plain claim → mark_TBD.
    assert out["classified_unsourced"][0]["action"] == "mark_TBD"
    assert out["classify_degraded"] is True


@pytest.mark.asyncio
async def test_classify_unsourced_records_degradation_on_fallback():
    """When ANY claim falls back, classify_degraded flips True for the bullet."""
    # Mix: LLM raises on the first call, returns valid JSON on the second.
    responses = [
        CircuitOpen("breaker open"),
        json.dumps({"action": "mark_TBD", "rationale": "LLM ok this time."}),
    ]

    async def fake_call(*args, **kwargs):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    mock_llm = AsyncMock()
    mock_llm.call = fake_call  # bypass AsyncMock for stateful side effect

    node = _make_classify_unsourced_node(mock_llm)
    state: VerifyState = {
        "grounded_results": [
            {"claim": "world-class system", "verdict": "unsourced", "source": None},
            {"claim": "owned the migration", "verdict": "unsourced", "source": None},
        ],
    }

    out = await node(state)

    # First claim → fallback (heuristic = remove for "world-class").
    # Second claim → LLM returns mark_TBD.
    actions = [c["action"] for c in out["classified_unsourced"]]
    assert actions == ["remove", "mark_TBD"]
    assert out["classify_degraded"] is True


# ---- D.4b: Layer 2 paraphrase parser ----


def test_layer_2_parser_handles_clean_json():
    """Clean JSON object with proper bool → parsed verbatim."""
    from harness.verify.nodes import _try_parse_ground_response

    response = json.dumps({"verified": True, "source_snippet": "matched phrase"})
    parsed = _try_parse_ground_response(response)
    assert parsed["verified"] is True
    assert parsed["source_snippet"] == "matched phrase"


def test_layer_2_parser_handles_fenced_json():
    """```json ... ``` markdown fences are stripped before parse."""
    from harness.verify.nodes import _try_parse_ground_response

    response = (
        '```json\n{"verified": false, "source_snippet": null}\n```'
    )
    parsed = _try_parse_ground_response(response)
    assert parsed["verified"] is False
    assert parsed["source_snippet"] is None


def test_layer_2_parser_fails_safe_on_garbage():
    """Random non-JSON without a `verified:` token → unsourced fail-safe."""
    from harness.verify.nodes import _try_parse_ground_response

    parsed = _try_parse_ground_response("totally random text without keywords")
    assert parsed == {"verified": False, "source_snippet": None}

    # Also: empty string → fail-safe.
    parsed_empty = _try_parse_ground_response("")
    assert parsed_empty == {"verified": False, "source_snippet": None}


def test_layer_2_parser_truncates_oversize_snippet():
    """source_snippet over 100 chars is trimmed defensively."""
    from harness.verify.nodes import _try_parse_ground_response

    long = "x" * 250
    response = json.dumps({"verified": True, "source_snippet": long})
    parsed = _try_parse_ground_response(response)
    assert parsed["verified"] is True
    assert len(parsed["source_snippet"]) == 100


# =========================================================================
# Node 4 — aggregate_verdict_node
# =========================================================================


@pytest.mark.asyncio
async def test_aggregate_all_verified_yields_complete():
    node = _make_aggregate_verdict_node()
    state: VerifyState = {
        "bullet": {"id": "b1"},
        "grounded_results": [
            {"claim": "c1", "verdict": "verified", "source": "raw § snippet"},
            {"claim": "c2", "verdict": "verified", "source": "raw § snippet 2"},
        ],
        "classified_unsourced": [],
    }
    out = await node(state)
    final = out["final_verdict"]
    assert final["bullet_id"] == "b1"
    assert final["verdict"] == "complete"
    assert len(final["verified_facts"]) == 2
    assert final["unsourced_claims"] == []
    assert final["ask_user"] == []


@pytest.mark.asyncio
async def test_aggregate_ask_user_yields_partial():
    node = _make_aggregate_verdict_node()
    state: VerifyState = {
        "bullet": {"id": "b2"},
        "grounded_results": [
            {"claim": "increased revenue by 42%", "verdict": "unsourced", "source": None},
        ],
        "classified_unsourced": [
            {
                "claim": "increased revenue by 42%",
                "action": "ask_user",
                "rationale": "numeric",
            }
        ],
    }
    out = await node(state)
    final = out["final_verdict"]
    assert final["verdict"] == "partial"
    assert len(final["ask_user"]) == 1


@pytest.mark.asyncio
async def test_aggregate_only_remove_or_mark_tbd_yields_complete():
    """Unsourced claims with no ask_user → caller can clean them up → complete."""
    node = _make_aggregate_verdict_node()
    state: VerifyState = {
        "bullet": {"id": "b3"},
        "grounded_results": [
            {"claim": "world-class system", "verdict": "unsourced", "source": None},
            {"claim": "reorganized teams", "verdict": "unsourced", "source": None},
        ],
        "classified_unsourced": [
            {"claim": "world-class system", "action": "remove", "rationale": "subjective"},
            {"claim": "reorganized teams", "action": "mark_TBD", "rationale": "factual"},
        ],
    }
    out = await node(state)
    final = out["final_verdict"]
    assert final["verdict"] == "complete"
    assert len(final["unsourced_claims"]) == 2


@pytest.mark.asyncio
async def test_aggregate_mixed_actions_partial_wins():
    """If ANY ask_user is present, partial wins regardless of remove/mark_TBD."""
    node = _make_aggregate_verdict_node()
    state: VerifyState = {
        "bullet": {"id": "b4"},
        "grounded_results": [
            {"claim": "c1", "verdict": "verified", "source": "raw § s"},
            {"claim": "increased revenue by 99%", "verdict": "unsourced", "source": None},
            {"claim": "world-class team", "verdict": "unsourced", "source": None},
        ],
        "classified_unsourced": [
            {"claim": "increased revenue by 99%", "action": "ask_user", "rationale": "n"},
            {"claim": "world-class team", "action": "remove", "rationale": "s"},
        ],
    }
    out = await node(state)
    final = out["final_verdict"]
    assert final["verdict"] == "partial"
    assert len(final["ask_user"]) == 1
    assert len(final["verified_facts"]) == 1


@pytest.mark.asyncio
async def test_aggregate_output_dict_shape_matches_schema_keys():
    """Output dict has exactly the keys required by pass3-verifier-io.schema."""
    node = _make_aggregate_verdict_node()
    state: VerifyState = {
        "bullet": {"id": "schema-test"},
        "grounded_results": [],
        "classified_unsourced": [],
    }
    out = await node(state)
    final = out["final_verdict"]
    # Required by the "Pass 3 Output (per bullet)" schema branch:
    assert set(final.keys()) >= {
        "bullet_id",
        "verdict",
        "verified_facts",
        "unsourced_claims",
        "ask_user",
    }
    assert isinstance(final["bullet_id"], str)
    assert final["verdict"] in {"complete", "partial", "failed"}
    assert isinstance(final["verified_facts"], list)
    assert isinstance(final["unsourced_claims"], list)
    assert isinstance(final["ask_user"], list)


# =========================================================================
# verify_bullets orchestrator
# =========================================================================


@pytest.mark.asyncio
async def test_verify_bullets_single_bullet_all_verified(tmp_path: Path):
    """Single bullet with pre-extracted facts that all substring-match → complete."""
    raw_path = tmp_path / "raw.md"
    raw_path.write_text(
        "Project alpha: led the team and delivered Q3 launch on time.",
        encoding="utf-8",
    )
    rubric_path = tmp_path / "rubric.md"
    rubric_path.write_text("# rubric placeholder", encoding="utf-8")

    bullets = [
        {
            "id": "b1",
            "text": "Led the team to deliver Q3 launch.",
            "claimed_facts": ["led the team", "delivered Q3 launch"],
            "experience_ref": "exp-1",
        }
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[raw_path],
        rubric_path=rubric_path,
        llm=None,
    )

    assert len(results) == 1
    assert results[0]["bullet_id"] == "b1"
    assert results[0]["verdict"] == "complete"
    assert len(results[0]["verified_facts"]) == 2


@pytest.mark.asyncio
async def test_verify_bullets_two_bullets_both_verified(tmp_path: Path):
    """Two bullets with grounded facts → two output dicts, all complete."""
    raw_path = tmp_path / "raw.md"
    raw_path.write_text(
        "Built data pipeline reducing latency. Mentored junior engineers.",
        encoding="utf-8",
    )

    bullets = [
        {
            "id": "b1",
            "text": "Built data pipeline reducing latency.",
            "claimed_facts": ["Built data pipeline", "reducing latency"],
        },
        {
            "id": "b2",
            "text": "Mentored junior engineers.",
            "claimed_facts": ["Mentored junior engineers"],
        },
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[raw_path],
        rubric_path=None,
        llm=None,
    )

    assert len(results) == 2
    assert {r["bullet_id"] for r in results} == {"b1", "b2"}
    assert all(r["verdict"] == "complete" for r in results)


@pytest.mark.asyncio
async def test_verify_bullets_mixed_result_yields_partial(tmp_path: Path):
    """One bullet with verified + numeric-unsourced claims → partial verdict."""
    raw_path = tmp_path / "raw.md"
    raw_path.write_text(
        "Delivered Q3 launch on schedule with cross-team coordination.",
        encoding="utf-8",
    )

    bullets = [
        {
            "id": "b1",
            "text": "Delivered Q3 launch and saved 100M.",
            "claimed_facts": ["Delivered Q3 launch", "saved 100M"],
        },
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[raw_path],
        rubric_path=None,
        llm=None,  # no LLM → Layer 2 skipped → numeric stat stays unsourced
    )

    assert len(results) == 1
    final = results[0]
    assert final["verdict"] == "partial"
    # The numeric "saved 100M" should land in ask_user.
    assert len(final["ask_user"]) == 1
    # The verified one should be in verified_facts.
    assert any("Q3" in vf["claim"] for vf in final["verified_facts"])


# =========================================================================
# build_graph smoke test
# =========================================================================


def test_build_graph_has_expected_nodes():
    """Compiled graph exposes the 4 node names + START/END."""
    g = build_graph(llm=None)
    nodes = set(g.get_graph().nodes.keys())
    expected = {
        "extract_claims",
        "ground_claim",
        "classify_unsourced",
        "aggregate_verdict",
    }
    assert expected.issubset(nodes)


@pytest.mark.asyncio
async def test_verify_bullets_empty_input_returns_empty():
    """No bullets → no results, no graph invocation needed."""
    results = await verify_bullets(
        bullets=[],
        source_files=[],
        rubric_path=None,
        llm=None,
    )
    assert results == []
