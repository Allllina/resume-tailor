"""Integration tests for harness.verify against real experience-bank markdown.

D11 update: post-isolation these tests load the COMMITTED sample raw
files (assets/experience-bank/raw.sample/*.md) when the real raw/ tree is
absent (fresh clone). Maintainer-local runs continue to use the private
raw/ files when present; the LLM is always mocked via AsyncMock.

The point is to exercise the real-text grounding paths (Layer 1 substring
+ Layer 2 paraphrase fallback) against ground-truth source text that
actually has the persona content, not synthetic fixtures.

Wave 4 D.4b — companion to the unit tests in
`tests/unit/test_pass3_verify.py` which use synthetic source text.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from harness.verify import build_graph, verify_bullets


# Resolve the assets dir from the repo root. This file lives at
# packages/harness/tests/integration/test_pass3_real_grounding.py — four
# parents up is the repo root.
_REPO = Path(__file__).resolve().parents[4]
_ASSETS_RAW_SAMPLE = _REPO / "assets" / "experience-bank" / "raw.sample"

# D11 — these tests verify Pass 3 grounding against the COMMITTED sample
# experience bank, NOT the maintainer's gitignored real data. Reasons:
# (a) reproducible across clones (CI / public users have only sample data),
# (b) claim substrings below are sample-content-tuned, not real-content-tuned,
# (c) maintainer's real data is for personal dogfood, not the test bench.
# Resisting the temptation to "prefer real if present" — that breaks the
# contract that tests are reproducible against committed assets only.
_STRATEGY = _ASSETS_RAW_SAMPLE / "01-strategy-consulting.md"
_ANALYTICS = _ASSETS_RAW_SAMPLE / "02-data-analytics.md"


@pytest.fixture(scope="module")
def strategy_path() -> Path:
    """Path to the strategy-consulting raw ground-truth file (sample or
    private real)."""
    assert _STRATEGY.is_file(), f"Missing fixture: {_STRATEGY}"
    return _STRATEGY


@pytest.fixture(scope="module")
def analytics_path() -> Path:
    """Path to the data-analytics raw ground-truth file (sample or
    private real)."""
    assert _ANALYTICS.is_file(), f"Missing fixture: {_ANALYTICS}"
    return _ANALYTICS


# =========================================================================
# Item 3.1 — Layer 1 substring match against real strategy text
# =========================================================================


@pytest.mark.asyncio
async def test_real_strategy_layer1_grounds_substring_without_llm(strategy_path):
    """A claim that is a literal substring of the strategy raw file → verified by Layer 1.

    No LLM calls expected (all claims pass Layer 1).
    """
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock()  # spy

    bullets = [
        {
            "id": "b1",
            "text": "Worked on EV OEM five-year strategy framework at Acme Strategy Group.",
            "claimed_facts": ["战略框架研究", "12 家行业 leader"],
            "experience_ref": "01-strategy-consulting",
        }
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[strategy_path],
        rubric_path=None,
        llm=mock_llm,
    )

    assert len(results) == 1
    assert results[0]["bullet_id"] == "b1"
    assert results[0]["verdict"] == "complete"
    assert len(results[0]["verified_facts"]) == 2
    # Layer 1 hit means Layer 2 LLM is never reached.
    mock_llm.call.assert_not_called()


# =========================================================================
# Item 3.2 — Layer 1 substring match against real analytics text
# =========================================================================


@pytest.mark.asyncio
async def test_real_analytics_layer1_grounds_substring_without_llm(analytics_path):
    """Claims that are substrings of 02-data-analytics.md → verified deterministically."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock()

    bullets = [
        {
            "id": "b1",
            "text": "Built A/B pricing experiment at BlueWave SaaS.",
            "claimed_facts": ["1.2M users", "8% lift", "p<0.05"],
            "experience_ref": "02-data-analytics",
        }
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[analytics_path],
        rubric_path=None,
        llm=mock_llm,
    )

    assert results[0]["verdict"] == "complete"
    assert len(results[0]["verified_facts"]) == 3
    mock_llm.call.assert_not_called()


# =========================================================================
# Item 3.3 — Fabricated claim not in any raw file lands in unsourced
# =========================================================================


@pytest.mark.asyncio
async def test_real_unsourced_fabrication_lands_in_ask_user(strategy_path, analytics_path):
    """A fabricated metric appears in no raw file → Layer 1 fails, Layer 2
    LLM mocked to also say unsourced → final verdict 'partial' with the
    claim routed to ask_user (numeric heuristic).
    """
    layer_2_response = json.dumps({"verified": False, "source_snippet": None})
    classify_response = json.dumps(
        {
            "action": "ask_user",
            "rationale": "Specific dollar figure that the candidate can confirm.",
        }
    )
    responses = [layer_2_response, classify_response]

    async def fake_call(*args, **kwargs):
        return responses.pop(0)

    mock_llm = AsyncMock()
    mock_llm.call = fake_call

    bullets = [
        {
            "id": "b1",
            "text": "Delivered 200M ARR for FabricatedCo in unrelated industry.",
            "claimed_facts": ["delivered 200M ARR for FabricatedCo"],
            "experience_ref": "fabricated",
        }
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[strategy_path, analytics_path],
        rubric_path=None,
        llm=mock_llm,
    )

    final = results[0]
    assert final["verdict"] == "partial"
    assert len(final["ask_user"]) == 1
    assert "200M" in final["ask_user"][0]["question"] or "ARR" in (
        final["ask_user"][0]["question"]
    )


# =========================================================================
# Item 3.4 — Layer 1 fail + Layer 2 LLM mock VERIFIED → verdict flips
# =========================================================================


@pytest.mark.asyncio
async def test_real_paraphrase_promoted_to_verified_via_layer2(strategy_path):
    """Paraphrased claim (no exact substring) → Layer 1 fails, mock LLM
    returns verified=true → Layer 2 promotes claim to verified."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(
        return_value=json.dumps(
            {
                "verified": True,
                "source_snippet": "战略框架研究",
            }
        )
    )

    bullets = [
        {
            "id": "b1",
            "text": "Led EV-industry strategy framework research at Acme.",
            # Phrasing not present verbatim in 01-strategy-consulting.md
            # (English vs the file's mostly Chinese prose).
            "claimed_facts": ["led EV-industry strategy framework research"],
            "experience_ref": "01-strategy-consulting",
        }
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[strategy_path],
        rubric_path=None,
        llm=mock_llm,
    )

    final = results[0]
    assert final["verdict"] == "complete"
    assert len(final["verified_facts"]) == 1
    assert "paraphrase" in final["verified_facts"][0]["source"]
    mock_llm.call.assert_awaited_once()


# =========================================================================
# Item 3.5 — Full path: Layer 1 fail + Layer 2 unverified + classify=ask_user
# =========================================================================


@pytest.mark.asyncio
async def test_real_full_path_layer2_unverified_then_classify_ask_user(strategy_path):
    """Layer 1 misses → Layer 2 LLM says unverified → classify LLM says ask_user.

    Full traversal of all 4 nodes with real source text. Final verdict 'partial'.
    """
    layer_2_response = json.dumps({"verified": False, "source_snippet": None})
    classify_response = json.dumps(
        {
            "action": "ask_user",
            "rationale": "Headcount figure that requires candidate confirmation.",
        }
    )
    responses = [layer_2_response, classify_response]

    async def fake_call(*args, **kwargs):
        return responses.pop(0)

    mock_llm = AsyncMock()
    mock_llm.call = fake_call

    bullets = [
        {
            "id": "b1",
            "text": "Coordinated 12-person delivery squad at Acme.",
            "claimed_facts": ["coordinated 12-person delivery squad"],
            "experience_ref": "01-strategy-consulting",
        }
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[strategy_path],
        rubric_path=None,
        llm=mock_llm,
    )

    final = results[0]
    assert final["verdict"] == "partial"
    assert len(final["ask_user"]) == 1
    assert len(final["unsourced_claims"]) == 1
    assert final["unsourced_claims"][0]["action"] == "ask_user"


# =========================================================================
# Item 3.6 — verify_bullets end-to-end across multiple raw files
# =========================================================================


@pytest.mark.asyncio
async def test_real_multi_file_orchestration(strategy_path, analytics_path):
    """Three bullets — strategy-grounded, analytics-grounded, fabricated.

    Verifies the orchestrator concatenates source text from multiple files
    and routes each bullet correctly.
    """
    layer_2_response = json.dumps({"verified": False, "source_snippet": None})
    classify_response = json.dumps(
        {
            "action": "ask_user",
            "rationale": "Numeric metric requires confirmation.",
        }
    )
    responses = [layer_2_response, classify_response]

    async def fake_call(*args, **kwargs):
        # The strategy + analytics bullets' claims pass Layer 1 → no LLM call.
        # Only the fabricated bullet's claim reaches Layer 2 + classify.
        if not responses:
            return json.dumps({"verified": False, "source_snippet": None})
        return responses.pop(0)

    mock_llm = AsyncMock()
    mock_llm.call = fake_call

    bullets = [
        {
            "id": "strategy-b",
            "text": "Researched EV OEM strategy framework.",
            "claimed_facts": ["战略框架研究"],
            "experience_ref": "01-strategy-consulting",
        },
        {
            "id": "analytics-b",
            "text": "Ran A/B test across 1.2M users.",
            "claimed_facts": ["1.2M users"],
            "experience_ref": "02-data-analytics",
        },
        {
            "id": "fabricated-b",
            "text": "Doubled platform revenue 200% in one quarter.",
            "claimed_facts": ["doubled platform revenue 200% in one quarter"],
            "experience_ref": "fabricated",
        },
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[strategy_path, analytics_path],
        rubric_path=None,
        llm=mock_llm,
    )

    assert len(results) == 3
    by_id = {r["bullet_id"]: r for r in results}

    assert by_id["strategy-b"]["verdict"] == "complete"
    assert len(by_id["strategy-b"]["verified_facts"]) == 1

    assert by_id["analytics-b"]["verdict"] == "complete"
    assert len(by_id["analytics-b"]["verified_facts"]) == 1

    # Fabricated bullet → classify LLM mocked to ask_user → partial.
    assert by_id["fabricated-b"]["verdict"] == "partial"
    assert len(by_id["fabricated-b"]["ask_user"]) == 1


# =========================================================================
# Item 3.7 — Empty source_files → all claims unsourced (fail-soft)
# =========================================================================


@pytest.mark.asyncio
async def test_real_empty_source_files_fails_soft():
    """No raw markdown loaded → no Layer 1 hits, no Layer 2 calls (no source
    to ground in), all claims fall through to classify."""
    classify_response = json.dumps(
        {
            "action": "mark_TBD",
            "rationale": "No source available to verify.",
        }
    )
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock(return_value=classify_response)

    bullets = [
        {
            "id": "b1",
            "text": "Did some thing.",
            "claimed_facts": ["some claim"],
            "experience_ref": "missing",
        }
    ]

    results = await verify_bullets(
        bullets=bullets,
        source_files=[],
        rubric_path=None,
        llm=mock_llm,
    )

    final = results[0]
    # No source → claim unsourced → classify LLM picks mark_TBD → complete
    # (mark_TBD does NOT trigger ask_user / partial path).
    assert final["verdict"] == "complete"
    assert len(final["unsourced_claims"]) == 1
    assert final["unsourced_claims"][0]["action"] == "mark_TBD"


# =========================================================================
# Item 3.8 — build_graph compiles cleanly with real LLMProvider Protocol
# =========================================================================


def test_real_build_graph_with_mock_llm_provider():
    """Smoke test: build_graph accepts an AsyncMock that quacks like LLMProvider."""
    mock_llm = AsyncMock()
    mock_llm.call = AsyncMock()
    g = build_graph(mock_llm)
    nodes = set(g.get_graph().nodes.keys())
    assert {
        "extract_claims",
        "ground_claim",
        "classify_unsourced",
        "aggregate_verdict",
    }.issubset(nodes)
