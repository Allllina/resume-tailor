"""Pass 3 verifier orchestrator (Wave 4 D.4a).

`verify_bullets(bullets, source_files, rubric_path, llm)` runs the LangGraph
verify cycle once per bullet and returns a list of per-bullet output dicts
matching the `pass3-verifier-io.schema.json` "Pass 3 Output (per bullet)"
branch.

D.4a scope: structural scaffolding + node functions. Loop integration,
artifact persistence, and full schema validation at boundaries land in
D.4c. This module is import-safe even when the optional `[verifier]`
extra is not installed — the LangGraph import only happens inside
`build_graph` (called from `verify_bullets`).
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from harness.exceptions import SubSkillUnavailable
from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen, LLMProvider

from .graph import build_graph


class Pass3VerifyError(Exception):
    """Raised when Pass 3 verification cannot produce per-bullet output.

    D.4a does not raise this for per-claim issues — those degrade to
    `unsourced` + classification. Reserved for hard-error paths (graph
    compile failure, malformed input, etc.) so D.4c's loop integration
    has a clean exception class to catch.
    """


def _load_source_text(source_files: list[Path]) -> str:
    """Concatenate raw markdown content from source files into one string.

    Each file is prefixed with a `# <filename>` header so the LLM (Layer 2
    grounding) can attribute snippets when source spans multiple files.
    Missing or unreadable files are skipped silently — D.4a is fail-soft
    on the source side; the worst case is "no grounding found" rather
    than a crash.

    D.4a MVP: no chunking, no retrieval. D.4b will introduce per-bullet
    `experience_ref`-driven file selection so we don't pay tokens for
    every file on every claim.
    """
    chunks: list[str] = []
    for path in source_files or []:
        try:
            p = Path(path)
        except TypeError:
            continue
        if not p.is_file():
            continue
        try:
            content = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not content.strip():
            continue
        chunks.append(f"# {p.name}\n\n{content.strip()}")
    return "\n\n".join(chunks)


def _load_rubric(rubric_path: Path | None) -> dict:
    """Load the quality-pass rubric.

    D.4a MVP: returns `{"raw_text": <markdown>}` if the path is a readable
    file, else an empty dict. Future waves may parse the markdown into
    structured rules; for now nodes that touch the rubric (none in D.4a)
    can read the raw markdown if needed.
    """
    if rubric_path is None:
        return {}
    try:
        p = Path(rubric_path)
    except TypeError:
        return {}
    if not p.is_file():
        return {}
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    if not text.strip():
        return {}
    return {"raw_text": text}


def _coerce_path_list(items: Any) -> list[Path]:
    """Best-effort conversion of mixed input (str/Path/None) to list[Path]."""
    if not items:
        return []
    out: list[Path] = []
    for item in items:
        if item is None:
            continue
        try:
            out.append(Path(item))
        except TypeError:
            continue
    return out


async def verify_bullets(
    bullets: list[dict],
    source_files: list[Path] | list[str],
    rubric_path: Path | str | None,
    llm: LLMProvider | None,
) -> list[dict]:
    """Run the Pass 3 verify cycle once per bullet; return per-bullet outputs.

    Args:
        bullets: list of `{id, text, claimed_facts, experience_ref}` dicts.
            Empty / missing `claimed_facts` triggers LLM-driven extraction
            in node 1; otherwise the pre-extracted list passes through.
        source_files: list of paths to raw experience markdown (and
            optionally user-profile, speedlearn-whitelist). Concatenated
            once per call.
        rubric_path: path to `quality-pass.md` or future JSON rubric.
            D.4a does not consume the contents; loaded into state for
            forward compatibility.
        llm: `LLMProvider` instance, or None to run in deterministic mode
            (no Layer 2 grounding, no LLM-driven claim extraction).

    Returns:
        List of per-bullet output dicts. Each validates against the
        `Pass 3 Output (per bullet)` branch of pass3-verifier-io.schema.json.
        Order matches `bullets` input order.

    Raises:
        SubSkillUnavailable: when the verifier itself crashes or the LLM
            is unreachable.
        Pass3VerifyError: on graph build failure (e.g., `[verifier]` extra
            not installed). Per-claim and per-bullet issues degrade to
            `unsourced` / `partial`, never raise.
    """
    if not bullets:
        return []

    paths = _coerce_path_list(source_files)
    source_text = _load_source_text(paths)
    rubric = _load_rubric(Path(rubric_path) if rubric_path else None)

    try:
        graph = build_graph(llm)
    except ImportError as e:
        # langgraph not installed — caller must `pip install -e ".[verifier]"`.
        raise Pass3VerifyError(
            "Pass 3 verifier requires langgraph (install with `pip install -e \".[verifier]\"`)."
        ) from e

    results: list[dict] = []
    for bullet in bullets:
        if not isinstance(bullet, dict):
            continue
        initial_state = {
            "bullet": bullet,
            "source_text": source_text,
            "rubric": rubric,
        }
        try:
            final = await graph.ainvoke(initial_state)
        except (asyncio.TimeoutError, ConnectionError, CircuitOpen) as e:
            raise SubSkillUnavailable("pass3_verifier", str(e), llm_unreachable=True) from e
        except InjectionDetectedError as e:
            raise SubSkillUnavailable(
                "pass3_verifier", f"injection detected: {e}", llm_unreachable=False
            ) from e
        except Exception as e:
            raise SubSkillUnavailable("pass3_verifier", str(e), llm_unreachable=False) from e

        verdict_dict = final.get("final_verdict")
        if not isinstance(verdict_dict, dict):
            raise SubSkillUnavailable(
                "pass3_verifier", "graph returned no verdict", llm_unreachable=False
            )
        results.append(verdict_dict)
    return results


__all__ = ["verify_bullets", "Pass3VerifyError"]
