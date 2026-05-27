"""LLM prompt templates for the per-lens master generator (Wave 4 C.1.2).

Single LLM call per generation. The lens definition file (passed as a
truncated text excerpt) substitutes for a JD: the model uses it to decide
which experiences to include, what bullet labels (粗体开头总结词) to write,
and how to phrase Summary + Skills. Bullet bodies are NOT rewritten — the
spec is "keep bullet bodies verbatim from the user's upload" (R-1).

Conceptual differences from `harness.rewrite.prompts`:

    - No JD. Lens definition acts as the demand signal.
    - Single round trip. The user prompt carries the entire upload_tex
      plus a compact experience inventory; the model returns a full
      master.tex string + selection metadata.
    - Bullet bodies are verbatim from the upload. The model only
      regenerates bullet labels, Summary, and Skills section.

Hard rules (paraphrased; keep aligned with general-rules.md):
    R-1: Truthfulness — Summary / Skills / labels must be supported by
         the upload + experience markdown. No fabricated stats, titles,
         metrics, dates.
    R-2: Single resume version per generation request.
    R-3: Risk flags (decision_rationale) are mandatory.
    R-4: Lens / scenario / market contexts are read-only.
    R-5: Output the master_tex as plain LaTeX-compatible text — preserve
         the user's structure (\\section, \\textbf, \\item, etc.).
    R-6: HC lens hard-sell positioning (loose; the model MAY emphasize
         employer-impact framing if the lens definition surfaces it).
    R-7: Brand-recognition disambiguator — the orchestrator handles R-7
         outside this prompt; the prompt does not regenerate parentheticals.
    R-8: Disambiguator-aware selection — same as R-7, handled outside.
"""
from __future__ import annotations


MASTER_GEN_SYSTEM_PROMPT = (
    "You are a senior resume writer producing a per-direction master "
    "résumé variant. You operate under strict truthfulness rules: every "
    "claim must be supported by the candidate's uploaded resume + "
    "experience bank. NEVER fabricate stats, titles, scopes, dates, or "
    "outcomes. Output ONLY a JSON object — no Markdown fences, no prose. "
    "Avoid AI-style punctuation (em dashes, arrows, decorative bullets); "
    "use plain ASCII (commas, periods, semicolons) only."
)


_HARD_RULES_PARAPHRASE = (
    "Hard rules:\n"
    "1. Truthfulness: every fact in Summary / Skills / bullet labels must "
    "trace back to the uploaded resume or the experience bank. No "
    "fabrication.\n"
    "2. Bullet bodies are VERBATIM from the upload. You do NOT rewrite "
    "the body of any bullet; you only regenerate the bold leading label "
    "(粗体开头总结词) for lens fit.\n"
    "3. Summary section regen: 2-4 sentences, lens-aligned, surfaces "
    "the candidate's most lens-relevant strengths.\n"
    "4. Skills section regen: order skills so lens-relevant items lead. "
    "Do not add skills the candidate has not demonstrated.\n"
    "5. Experience selection (use vertical_fit_per_lens cells when "
    "present): Cat 1 = include / lead; Cat 2 = include / compress; "
    "Cat 3 = include as backup line; Cat 4 = drop. Treat missing or "
    "weak fit as Cat 4 (drop).\n"
    "6. No AI punctuation: no em dash, no arrows, no decorative bullets. "
    "Plain ASCII.\n"
    "7. Output the full master_tex as a single string preserving the "
    "user's LaTeX structure (\\section, \\textbf, \\item, etc.). Drop "
    "blocks for excluded experiences."
)


_OUTPUT_CONTRACT = (
    "Output a JSON object with EXACTLY these keys:\n"
    "  master_tex: string (the full per-lens master resume; LaTeX-"
    "compatible, plain-text)\n"
    "  experiences_included: array of experience id strings (ordered "
    "lens-priority-first)\n"
    "  experiences_dropped: array of experience id strings\n"
    "  summary_text: string (the Summary section text only — for QA)\n"
    "  decision_rationale: 2-3 sentences explaining why these experiences "
    "fit the lens"
)


def build_user_prompt(
    upload_tex: str,
    experience_inventory: list[dict],
    lens: str,
    lens_definition_excerpt: str,
    target_market: str,
) -> str:
    """Build the single LLM user prompt for per-lens master generation.

    `experience_inventory` is a compact list of `{id, role, company,
    period, one_line, fit}` dicts the orchestrator pre-built from the
    experiences-index — `fit` is the `vertical_fit_per_lens[lens]` cell
    score (or "missing" when the cell is absent / unscored).
    """
    # Truncate aggressively so the user prompt stays under ~12k chars.
    upload_block = (upload_tex or "")[:6000]
    lens_block = (lens_definition_excerpt or "")[:1800]

    inv_lines: list[str] = []
    for entry in experience_inventory[:30]:
        inv_lines.append(
            "- id={id} | company={company} | role={role} | period={period} | "
            "fit={fit} | one_line={one_line}".format(
                id=entry.get("id", ""),
                company=(entry.get("company") or "")[:80],
                role=(entry.get("role") or "")[:80],
                period=(entry.get("period") or "")[:40],
                fit=entry.get("fit", "missing"),
                one_line=(entry.get("one_line") or "")[:160],
            )
        )
    inventory_block = "\n".join(inv_lines) or "(no experience inventory)"

    parts = [
        f"Target lens: {lens}",
        f"Target market: {target_market or '(unspecified)'}",
        "",
        "Lens definition (truncated):",
        '"""',
        lens_block,
        '"""',
        "",
        "Candidate uploaded resume (truncated; treat as ground truth for "
        "bullet bodies):",
        '"""',
        upload_block,
        '"""',
        "",
        "Experience inventory (id → company / role / period / "
        "lens-fit cell / one_line):",
        inventory_block,
        "",
        _HARD_RULES_PARAPHRASE,
        "",
        _OUTPUT_CONTRACT,
    ]
    return "\n".join(parts)
