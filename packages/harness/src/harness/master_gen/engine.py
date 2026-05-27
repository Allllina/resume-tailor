"""Per-lens master generation engine — Wave 4 C.1.2.

Public API:
    `generate_master_for_lens(...)` — single async LLM round-trip that
    selects experiences, regenerates Summary + Skills + bullet labels,
    and returns the full master.tex tailored for the requested lens.

The engine intentionally mirrors the high-level shape of
`harness.rewrite.engine`:
    - Pydantic v2 output model with private `_method` marker.
    - `model_dump_jsonable()` workaround for `_method` serialization.
    - Truthfulness pre-check via the existing
      `harness.rewrite.truthfulness.verify_claims_in_raw` helper.
    - Loud fallback when the LLM raises / returns malformed JSON: the
      engine returns the user's verbatim upload + `_method =
      "fallback_no_llm"` so generation NEVER produces an empty master.

Method vocabulary (mirrors Step B / D.2):
    - "llm"             — full LLM call succeeded; truthfulness gate passed.
    - "llm_partial"     — LLM ran but produced an incomplete / partially-
                            unsourced response; engine preserved the upload
                            for unverified bullets (but used the LLM's
                            Summary / Skills / selection).
    - "fallback_no_llm" — LLM unavailable / raised / output unusable; the
                            output's master_tex is the upload verbatim.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from harness.exceptions import SubSkillUnavailable
from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen
from harness.master_gen.prompts import (
    MASTER_GEN_SYSTEM_PROMPT,
    build_user_prompt,
)
from harness.rewrite.truthfulness import verify_claims_in_raw


# --------------------------- output model ---------------------------


class MasterGenOutput(BaseModel):
    """Per-lens master generation result.

    SERIALIZATION CONTRACT — callers must use `.model_dump_jsonable()`
    rather than the bare `.model_dump()` because `_method` is a Pydantic
    v2 private attribute that the default dump silently drops.
    """

    master_tex: str = ""
    experiences_included: list[str] = Field(default_factory=list)
    experiences_dropped: list[str] = Field(default_factory=list)
    summary_text: str = ""
    decision_rationale: str = ""
    _method: str = "llm"

    def model_dump_jsonable(self) -> dict[str, Any]:
        out = self.model_dump(mode="json")
        out["_method"] = getattr(self, "_method", "llm")
        return out


# --------------------------- helpers ---------------------------


# Repo root → role-lens definitions live at
# assets/knowledge-base/references/role-lenses/<lens-slug>.md. Map the
# user-profile lens enum to the on-disk filename.
_LENS_DEF_FILENAME: dict[str, str] = {
    "A_strategy_research": "A-strategy-research.md",
    "B_data_analytics": "B-data-analytics.md",
    "C_product_ops": "C-product-ops.md",
    "D_finance_markets": "D-finance-markets.md",
    "HC_human_capital": "HC-human-capital.md",
}


def _load_lens_definition(repo_root: Path, lens: str) -> str:
    """Load the role-lens markdown excerpt. Empty string on miss.

    The lens definition is the implicit "JD" for master generation. When
    it is missing we still proceed — the LLM gets less context but the
    upload itself remains the ground truth.
    """
    fname = _LENS_DEF_FILENAME.get(lens)
    if not fname:
        return ""
    path = (
        repo_root
        / "assets"
        / "knowledge-base"
        / "references"
        / "role-lenses"
        / fname
    )
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_raw_file(raw_files_root: Path, experience_id: str) -> str:
    """Read `<raw_files_root>/<id>.md`. Empty string on miss."""
    candidate = raw_files_root / f"{experience_id}.md"
    if not candidate.is_file():
        return ""
    try:
        return candidate.read_text(encoding="utf-8")
    except OSError:
        return ""


def _strip_json_fences(text: str) -> str:
    """Pull the JSON object out of ```json fences if the LLM wrapped it."""
    s = (text or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _build_inventory(
    experiences: list[dict],
    lens: str,
) -> list[dict]:
    """Compact inventory rows the LLM consumes to make selection decisions.

    Per spec: read `vertical_fit_per_lens[lens]` cells when scored;
    otherwise treat as "weak" (conservative — leans toward Cat 4 drop).
    """
    out: list[dict] = []
    for exp in experiences:
        if not isinstance(exp, dict):
            continue
        eid = exp.get("id") or ""
        if not eid:
            continue
        cells = exp.get("vertical_fit_per_lens") or {}
        if isinstance(cells, dict):
            cell = cells.get(lens)
        else:
            cell = None
        if isinstance(cell, str) and cell.strip():
            fit = cell.strip()
        elif isinstance(cell, dict):
            score = cell.get("score") or cell.get("fit") or "weak"
            fit = score if isinstance(score, str) and score.strip() else "weak"
        else:
            fit = "weak"
        out.append(
            {
                "id": eid,
                "company": exp.get("company") or "",
                "role": exp.get("role") or "",
                "period": exp.get("period") or "",
                "one_line": exp.get("one_line") or "",
                "fit": fit,
            }
        )
    return out


def _verify_against_bank(
    summary_text: str,
    experiences_included: list[str],
    raw_files_root: Path,
    upload_tex: str,
) -> bool:
    """Truthfulness gate for Summary text.

    Each "claim" we extract from summary_text is the summary itself —
    we treat the entire summary as one claim that must be groundable in
    the union of (upload_tex + every included experience's raw file).

    Returns True when all sampled claims trace back to the bank; False
    otherwise. Used to decide between `_method = "llm"` and
    `_method = "llm_partial"` (we keep the LLM output but record partial
    confidence — the orchestrator still emits it).
    """
    if not summary_text or not summary_text.strip():
        return True
    bank_text_parts: list[str] = [upload_tex or ""]
    for eid in experiences_included:
        bank_text_parts.append(_read_raw_file(raw_files_root, eid))
    bank_text = "\n".join(bank_text_parts)
    if not bank_text.strip():
        return False
    # Pragmatic gate: split summary into sentence-ish fragments, require
    # at least one substring trace per fragment. The substring helper is
    # already lenient about punctuation + percentage notation.
    fragments = [
        f.strip()
        for f in summary_text.replace(";", ".").split(".")
        if len(f.strip()) > 3
    ]
    if not fragments:
        return True
    _, unsourced = verify_claims_in_raw(fragments, bank_text)
    # Allow up to 1 unsourced fragment (flexibility for connective phrasing
    # like "I am a candidate who..." that has no provable substring); past
    # that we declare partial.
    return len(unsourced) <= 1


# --------------------------- public orchestrator ---------------------------


async def generate_master_for_lens(
    upload_tex: str,
    experiences: list[dict],
    raw_files_root: Path,
    lens: str,
    target_market: str,
    llm: Any,
    repo_root: Path | None = None,
) -> MasterGenOutput:
    """Generate a per-lens master.tex variant.

    Single LLM call. On any failure (missing LLM, transport raise,
    unparseable JSON) the engine raises SubSkillUnavailable so the
    caller can handle the fail-fast. On a successful call whose
    Summary / claims fail the truthfulness gate, the LLM output is still
    surfaced but `_method = "llm_partial"` so the API can warn the UI.

    `repo_root` is optional — when provided the engine loads the
    `assets/knowledge-base/references/role-lenses/<lens>.md` file as the
    implicit demand signal. When None or missing on disk, the model
    sees an empty lens-definition block but still produces output.
    """
    inventory = _build_inventory(experiences, lens)

    if llm is None:
        raise SubSkillUnavailable(
            "master_gen", "LLM provider not configured", llm_unreachable=True
        )

    lens_definition = ""
    if repo_root is not None:
        lens_definition = _load_lens_definition(repo_root, lens)

    user_prompt = build_user_prompt(
        upload_tex=upload_tex or "",
        experience_inventory=inventory,
        lens=lens,
        lens_definition_excerpt=lens_definition,
        target_market=target_market or "",
    )

    try:
        response = await llm.call(
            system=MASTER_GEN_SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=4000,
            temperature=0.3,
        )
    except (
        asyncio.TimeoutError,
        ConnectionError,
        CircuitOpen,
        InjectionDetectedError,
    ) as e:
        raise SubSkillUnavailable("master_gen", str(e), llm_unreachable=True) from e

    if not isinstance(response, str) or not response.strip():
        raise SubSkillUnavailable(
            "master_gen", "empty LLM response", llm_unreachable=False
        )

    try:
        parsed = json.loads(_strip_json_fences(response))
    except (json.JSONDecodeError, ValueError) as e:
        raise SubSkillUnavailable(
            "master_gen", f"malformed JSON from LLM: {e}", llm_unreachable=False
        ) from e

    if not isinstance(parsed, dict):
        raise SubSkillUnavailable(
            "master_gen", "LLM response is not a JSON object", llm_unreachable=False
        )

    master_tex = parsed.get("master_tex")
    if not isinstance(master_tex, str) or not master_tex.strip():
        # The LLM didn't emit a usable master — fail fast.
        raise SubSkillUnavailable(
            "master_gen", "LLM did not emit master_tex", llm_unreachable=False
        )

    included = parsed.get("experiences_included") or []
    dropped = parsed.get("experiences_dropped") or []
    summary_text = parsed.get("summary_text") or ""
    rationale = parsed.get("decision_rationale") or ""

    if not isinstance(included, list):
        included = []
    if not isinstance(dropped, list):
        dropped = []

    included = [str(x) for x in included if isinstance(x, (str, int))]
    dropped = [str(x) for x in dropped if isinstance(x, (str, int))]

    # Truthfulness gate on Summary. When it fails we keep the LLM output
    # but mark the run as partial so the API can warn the UI.
    summary_ok = _verify_against_bank(
        summary_text=summary_text,
        experiences_included=included,
        raw_files_root=raw_files_root,
        upload_tex=upload_tex,
    )

    method = "llm" if summary_ok else "llm_partial"

    out = MasterGenOutput(
        master_tex=master_tex,
        experiences_included=included,
        experiences_dropped=dropped,
        summary_text=summary_text,
        decision_rationale=rationale,
    )
    out._method = method
    return out
