"""Pass 3 LangGraph node factories (Wave 4 D.4a).

Four node factories — each returns an async callable bound to an
`LLMProvider` via closure (Option A from the D.4a spec). The compiled
graph in `graph.build_graph` wires them in a linear DAG.

The LLM is captured via closure rather than threaded through `VerifyState`
because LangGraph state must remain JSON-serializable for checkpointing,
and `LLMProvider` instances are not.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Awaitable, Callable

from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen, LLMProvider
from harness.rewrite.truthfulness import normalize_text, verify_claims_in_raw

from ._prompts import (
    CLASSIFY_UNSOURCED_SYSTEM_PROMPT,
    CLASSIFY_UNSOURCED_USER_TEMPLATE,
    EXTRACT_SYSTEM_PROMPT,
    EXTRACT_USER_PROMPT_TEMPLATE,
    GROUND_SNIPPET_MAX_CHARS,
    GROUND_SOURCE_MAX_CHARS,
    GROUND_SYSTEM_PROMPT,
    GROUND_USER_PROMPT_TEMPLATE,
)
from .state import VerifyState


# Valid action values for the classify_unsourced node.
_VALID_CLASSIFY_ACTIONS: frozenset[str] = frozenset({"remove", "mark_TBD", "ask_user"})


# --------------------------- Helpers ---------------------------


_NUMERIC_RE = re.compile(r"\d")

# Subjective-puffery lexicon (case-insensitive English + simplified Chinese).
# Keep small + curated — this is a heuristic gate, not a sentiment classifier.
_SUBJECTIVE_LEXICON: tuple[str, ...] = (
    "strong",
    "best",
    "leading",
    "innovative",
    "world-class",
    "world class",
    "顶级",
    "领先",
    "卓越",
)


def _strip_json_fences(text: str) -> str:
    """Best-effort: pull a JSON value out of ```json ...``` fences if present.

    Mirrors the helper in harness.competency.extractor / harness.rewrite.engine
    so behaviour is consistent across the harness.
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


def _looks_numeric_claim(claim: str) -> bool:
    """Claim contains a digit — flag for ask_user (stat claims need verification).

    D.4a heuristic; D.4b will replace with LLM-driven action choice.
    """
    return bool(_NUMERIC_RE.search(claim or ""))


def _looks_subjective(claim: str) -> bool:
    """Claim contains subjective puffery from the small lexicon → action=remove."""
    if not claim:
        return False
    low = claim.lower()
    for token in _SUBJECTIVE_LEXICON:
        if token.lower() in low:
            return True
    return False


def _short_snippet_for_layer1(claim: str, source_text: str) -> str:
    """Return a tight excerpt of `source_text` near the matched claim.

    Cheap windowed lookup on the normalized text. Approximate — caller knows
    this and the source is primarily for downstream display, not re-validation.
    """
    if not source_text or not claim:
        return ""
    norm_source = normalize_text(source_text)
    norm_claim = normalize_text(claim)
    if not norm_claim:
        return ""
    idx = norm_source.find(norm_claim)
    if idx < 0:
        # Substring didn't align after normalization — happens when match
        # came through percentage canonicalization. Return claim itself.
        return norm_claim[:80]
    end = min(len(norm_source), idx + len(norm_claim) + 24)
    start = max(0, idx - 8)
    return norm_source[start:end]


# --------------------------- Node 1: extract_claims ---------------------------


def _make_extract_claims_node(llm: LLMProvider | None) -> Callable[[VerifyState], Awaitable[dict]]:
    """Build node 1 with the LLM bound via closure.

    Behaviour:
      - If `bullet["claimed_facts"]` is non-empty list of strings → no LLM
        call; claims pass through verbatim.
      - Otherwise → ONE LLM call for atomic-claim extraction; on parse
        failure or LLM raise → fall back to single-claim list `[bullet["text"]]`
        with `extraction_degraded=True`.

    This node is a no-op for D.2's rewrite engine outputs (which already
    pre-extracts `claimed_facts` per Section G). The LLM path exists for
    callers passing raw bullet prose only.
    """

    async def extract_claims_node(state: VerifyState) -> dict:
        bullet = state.get("bullet") or {}
        pre_extracted = bullet.get("claimed_facts")
        text = (bullet.get("text") or "").strip()

        if isinstance(pre_extracted, list) and any(
            isinstance(c, str) and c.strip() for c in pre_extracted
        ):
            claims = [c for c in pre_extracted if isinstance(c, str) and c.strip()]
            return {"extracted_claims": claims, "extraction_degraded": False}

        if not text:
            return {"extracted_claims": [], "extraction_degraded": False}
        if llm is None:
            return {"extracted_claims": [text], "extraction_degraded": True}

        prompt = EXTRACT_USER_PROMPT_TEMPLATE.format(bullet_text=text)
        try:
            response = await llm.call(
                system=EXTRACT_SYSTEM_PROMPT,
                user=prompt,
                max_tokens=512,
                temperature=0.0,
            )
        except (
            asyncio.TimeoutError,
            ConnectionError,
            CircuitOpen,
            InjectionDetectedError,
        ):
            return {"extracted_claims": [text], "extraction_degraded": True}

        if not isinstance(response, str) or not response.strip():
            return {"extracted_claims": [text], "extraction_degraded": True}

        try:
            parsed = json.loads(_strip_json_fences(response))
        except (json.JSONDecodeError, ValueError):
            return {"extracted_claims": [text], "extraction_degraded": True}

        if not isinstance(parsed, list):
            return {"extracted_claims": [text], "extraction_degraded": True}

        claims = [c.strip() for c in parsed if isinstance(c, str) and c.strip()]
        if not claims:
            # Empty list from LLM = degradation (bullet text non-empty here).
            return {"extracted_claims": [text], "extraction_degraded": True}
        return {"extracted_claims": claims, "extraction_degraded": False}

    return extract_claims_node


# --------------------------- Node 2: ground_claim ---------------------------


def _try_parse_ground_response(response: str) -> dict:
    """Best-effort JSON parse for the Layer 2 LLM response.

    Always returns a dict of shape `{"verified": bool, "source_snippet": str|None}`.
    Failure mode is fail-safe: returns `{"verified": False, "source_snippet": None}`
    so an unparseable response leaves the claim unsourced (never raises).

    Precedence (tightened in D.4b):
      1. Strip markdown fences with `_strip_json_fences`, then `json.loads`.
         If the result is a dict with a bool `verified` key → use it.
      2. Otherwise, scan for the literal substring `"verified": true|false`
         (case-insensitive). If found, set `verified` to that bool. Then
         try a non-greedy quote-bounded capture for `source_snippet`.
      3. If neither path yields a `verified` bool → return the unsourced
         fail-safe dict.

    `source_snippet` is trimmed to `GROUND_SNIPPET_MAX_CHARS` defensively
    even when the LLM returns a longer string.
    """
    failsafe = {"verified": False, "source_snippet": None}
    if not isinstance(response, str) or not response.strip():
        return failsafe

    stripped = _strip_json_fences(response)

    # Path 1 — clean JSON parse.
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        parsed = None

    if isinstance(parsed, dict) and isinstance(parsed.get("verified"), bool):
        snippet = parsed.get("source_snippet")
        snippet_out: str | None
        if isinstance(snippet, str) and snippet.strip():
            snippet_out = snippet.strip()[:GROUND_SNIPPET_MAX_CHARS]
        else:
            snippet_out = None
        return {"verified": parsed["verified"], "source_snippet": snippet_out}

    # Path 2 — single-pass scan for the literal `verified` boolean.
    m = re.search(r'"verified"\s*:\s*(true|false)', stripped, flags=re.IGNORECASE)
    if not m:
        return failsafe
    verified_bool = m.group(1).lower() == "true"

    # Non-greedy quote-bounded capture for source_snippet.
    snippet_match = re.search(
        r'"source_snippet"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"',
        stripped,
    )
    snippet_str = snippet_match.group(1) if snippet_match else None
    if snippet_str is not None:
        snippet_str = snippet_str.strip()
        if not snippet_str:
            snippet_str = None
        else:
            snippet_str = snippet_str[:GROUND_SNIPPET_MAX_CHARS]
    return {"verified": verified_bool, "source_snippet": snippet_str}


def _make_ground_claim_node(llm: LLMProvider | None) -> Callable[[VerifyState], Awaitable[dict]]:
    """Build node 2 with LLM bound via closure.

    Layer 1 (deterministic): substring match via verify_claims_in_raw.
    Layer 2 (LLM, per unsourced claim): paraphrase check.

    Per-claim LLM failure (CircuitOpen / timeout / parse error) leaves the
    claim unsourced and records the claim string in `layer_2_failures` for
    downstream observability. D.4a MVP — does not retry.
    """

    async def ground_claim_node(state: VerifyState) -> dict:
        claims: list[str] = list(state.get("extracted_claims") or [])
        source_text: str = state.get("source_text") or ""
        layer_2_failures: list[str] = []

        if not claims:
            return {"grounded_results": [], "layer_2_failures": []}

        verified, unsourced = verify_claims_in_raw(claims, source_text)

        results: list[dict] = []
        for claim in verified:
            snippet = _short_snippet_for_layer1(claim, source_text)
            source_str = (
                f"raw § {snippet}" if snippet else "raw § (substring match)"
            )
            results.append(
                {"claim": claim, "verdict": "verified", "source": source_str}
            )

        if not unsourced:
            return {"grounded_results": results, "layer_2_failures": []}

        # Layer 2 — paraphrase match via LLM, one call per unsourced claim.
        # When llm is None or source_text empty, skip Layer 2 (claims stay unsourced).
        truncated_source = source_text[:GROUND_SOURCE_MAX_CHARS]

        for claim in unsourced:
            if llm is None or not truncated_source.strip():
                results.append(
                    {"claim": claim, "verdict": "unsourced", "source": None}
                )
                continue

            prompt = GROUND_USER_PROMPT_TEMPLATE.format(
                claim=claim, source_text=truncated_source
            )
            try:
                response = await llm.call(
                    system=GROUND_SYSTEM_PROMPT,
                    user=prompt,
                    max_tokens=256,
                    temperature=0.0,
                )
            except (
                asyncio.TimeoutError,
                ConnectionError,
                CircuitOpen,
                InjectionDetectedError,
            ):
                layer_2_failures.append(claim)
                results.append(
                    {"claim": claim, "verdict": "unsourced", "source": None}
                )
                continue

            parsed = _try_parse_ground_response(response)
            # Parser is fail-safe: always returns a dict. Any non-string /
            # empty response surfaces verified=False AND is recorded as a
            # Layer 2 failure for observability (visible degradation). Real
            # JSON-shaped responses that simply say `verified: false` flow
            # through the normal unsourced path below without recording
            # a failure (the LLM did its job — it just disagreed).
            if not isinstance(response, str) or not response.strip():
                layer_2_failures.append(claim)

            if parsed["verified"]:
                snippet = parsed["source_snippet"] or claim
                results.append(
                    {
                        "claim": claim,
                        "verdict": "verified",
                        "source": f"raw § paraphrase: {snippet}",
                    }
                )
            else:
                results.append(
                    {"claim": claim, "verdict": "unsourced", "source": None}
                )

        return {"grounded_results": results, "layer_2_failures": layer_2_failures}

    return ground_claim_node


# --------------------------- Node 3: classify_unsourced ---------------------------


def _heuristic_classify(claim: str) -> dict:
    """D.4a heuristic decision used as the LLM-fallback path.

      - Numeric claim (contains a digit) → `ask_user`.
      - Subjective puffery (lexicon hit) → `remove`.
      - Otherwise → `mark_TBD`.

    Returns a dict with keys `action` and `rationale` (no `claim` key —
    caller composes the final per-claim entry).
    """
    if _looks_numeric_claim(claim):
        return {
            "action": "ask_user",
            "rationale": (
                "Claim contains a numeric value; verification "
                "with the candidate is required."
            ),
        }
    if _looks_subjective(claim):
        return {
            "action": "remove",
            "rationale": (
                "Claim contains subjective puffery and can be "
                "removed without weakening factual content."
            ),
        }
    return {
        "action": "mark_TBD",
        "rationale": (
            "Claim is unsourced but factual; flagged TBD for "
            "the candidate to confirm or remove."
        ),
    }


def _try_parse_classify_response(response: str) -> dict | None:
    """Parse the classify_unsourced LLM response.

    Returns a dict with keys `action` (∈ _VALID_CLASSIFY_ACTIONS) and
    `rationale` (str) on success, or None on any failure (malformed JSON,
    missing fields, action outside the enum, non-string types).

    Caller falls back to heuristics on None.
    """
    if not isinstance(response, str) or not response.strip():
        return None

    stripped = _strip_json_fences(response)
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None

    action = parsed.get("action")
    rationale = parsed.get("rationale")
    if not isinstance(action, str) or action not in _VALID_CLASSIFY_ACTIONS:
        return None
    if not isinstance(rationale, str) or not rationale.strip():
        # Tolerate missing rationale — synthesize one rather than fall back.
        rationale = "Classified by LLM (no rationale provided)."
    return {"action": action, "rationale": rationale.strip()}


def _make_classify_unsourced_node(
    llm: LLMProvider | None,
) -> Callable[[VerifyState], Awaitable[dict]]:
    """Build node 3 — LLM-driven action choice with heuristic fallback (D.4b).

    For each unsourced claim:
      1. Try one LLM call asking for `{"action": ..., "rationale": ...}` JSON.
      2. On LLM raise (CircuitOpen / TimeoutError / ConnectionError /
         InjectionDetectedError), malformed JSON, or action outside the
         allowed enum → fall back to deterministic heuristics
         (`_heuristic_classify`) AND mark `state["classify_degraded"] = True`
         on the returned partial state. This mirrors `extraction_degraded`.
      3. When `llm is None` → all claims go through heuristics; this is
         the deterministic path used by tests and by the D.4a behaviour
         the suite already expects.

    The degradation flag is set on the FIRST fallback in the per-bullet
    run; subsequent fallbacks within the same call don't re-flip it.
    """

    async def classify_unsourced_node(state: VerifyState) -> dict:
        grounded: list[dict] = list(state.get("grounded_results") or [])
        unsourced_claims = [
            entry.get("claim", "")
            for entry in grounded
            if entry.get("verdict") == "unsourced"
        ]

        out: list[dict] = []
        degraded = False

        for claim in unsourced_claims:
            # No LLM at all → use heuristics directly. This is NOT considered
            # a degradation event (the caller intentionally chose llm=None).
            if llm is None:
                decision = _heuristic_classify(claim)
                out.append(
                    {
                        "claim": claim,
                        "action": decision["action"],
                        "rationale": decision["rationale"],
                    }
                )
                continue

            prompt = CLASSIFY_UNSOURCED_USER_TEMPLATE.format(claim=claim)
            try:
                response = await llm.call(
                    system=CLASSIFY_UNSOURCED_SYSTEM_PROMPT,
                    user=prompt,
                    max_tokens=200,
                    temperature=0.0,
                )
            except (
                asyncio.TimeoutError,
                ConnectionError,
                CircuitOpen,
                InjectionDetectedError,
            ):
                degraded = True
                decision = _heuristic_classify(claim)
                out.append(
                    {
                        "claim": claim,
                        "action": decision["action"],
                        "rationale": decision["rationale"],
                    }
                )
                continue

            parsed = _try_parse_classify_response(response)
            if parsed is None:
                degraded = True
                decision = _heuristic_classify(claim)
                out.append(
                    {
                        "claim": claim,
                        "action": decision["action"],
                        "rationale": decision["rationale"],
                    }
                )
                continue

            out.append(
                {
                    "claim": claim,
                    "action": parsed["action"],
                    "rationale": parsed["rationale"],
                }
            )

        return {"classified_unsourced": out, "classify_degraded": degraded}

    return classify_unsourced_node


# --------------------------- Node 4: aggregate_verdict ---------------------------


def _make_aggregate_verdict_node() -> Callable[[VerifyState], Awaitable[dict]]:
    """Build node 4 — pure function over state; no LLM, no closure deps.

    Bullet-level verdict rules:
      - All claims verified → `complete`.
      - Any classified action == `ask_user` → `partial`.
      - Any unsourced AND all such actions ∈ {remove, mark_TBD} → `complete`.
      - `failed` only on unhandled crash (D.4a never sets it).
    """

    async def aggregate_verdict_node(state: VerifyState) -> dict:
        bullet: dict = state.get("bullet") or {}
        bullet_id: str = str(bullet.get("id") or "")

        grounded: list[dict] = list(state.get("grounded_results") or [])
        classified: list[dict] = list(state.get("classified_unsourced") or [])

        verified_facts: list[dict] = []
        for entry in grounded:
            if entry.get("verdict") != "verified":
                continue
            verified_facts.append(
                {
                    "claim": entry.get("claim", ""),
                    "source": entry.get("source") or "raw § (substring match)",
                }
            )

        unsourced_claims: list[dict] = []
        for entry in classified:
            unsourced_claims.append(
                {
                    "claim": entry.get("claim", ""),
                    "action": entry.get("action", "mark_TBD"),
                    "rationale": entry.get("rationale", ""),
                }
            )

        ask_user: list[dict] = []
        for entry in classified:
            if entry.get("action") != "ask_user":
                continue
            ask_user.append(
                {
                    "question": (
                        f"Can you confirm the figure in: \"{entry.get('claim', '')}\"?"
                    ),
                    "context": (
                        entry.get("rationale", "")
                        or "Numeric claim could not be grounded automatically."
                    ),
                }
            )

        any_unsourced = bool(unsourced_claims)
        any_ask_user = any(c.get("action") == "ask_user" for c in classified)

        if not any_unsourced:
            verdict = "complete"
        elif any_ask_user:
            verdict = "partial"
        else:
            verdict = "complete"

        final = {
            "bullet_id": bullet_id,
            "verdict": verdict,
            "verified_facts": verified_facts,
            "unsourced_claims": unsourced_claims,
            "ask_user": ask_user,
        }
        return {"final_verdict": final}

    return aggregate_verdict_node


__all__ = [
    "_make_extract_claims_node",
    "_make_ground_claim_node",
    "_make_classify_unsourced_node",
    "_make_aggregate_verdict_node",
]
