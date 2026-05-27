"""Pass 3 verifier LLM prompts (Wave 4 D.4a).

Module-level constants kept separate from `nodes.py` to keep the node bodies
readable and to make prompt-engineering changes (planned for D.4b) trivial
to locate. No logic here — just templates.
"""

EXTRACT_SYSTEM_PROMPT = (
    "You decompose resume bullet prose into atomic factual claims. "
    "Output ONLY a JSON list of strings, one claim per element. No prose, "
    "no Markdown fences."
)


EXTRACT_USER_PROMPT_TEMPLATE = """Decompose the bullet below into atomic factual claims. Each claim must
be a self-contained statement that can be independently verified against
source documents. Skip transitions and meta-commentary.

Bullet:
\"\"\"
{bullet_text}
\"\"\"

Output: JSON list of strings only, e.g. ["claim 1", "claim 2"].
"""


GROUND_SYSTEM_PROMPT = (
    "You judge whether a single claim is supported by a source document, "
    "possibly via paraphrase. Output JSON only. No prose. No markdown fences. "
    "No explanation. Exactly two fields: `verified` (bool) and "
    "`source_snippet` (string or null, max 100 characters)."
)


GROUND_USER_PROMPT_TEMPLATE = """Claim:
\"\"\"
{claim}
\"\"\"

Source text:
\"\"\"
{source_text}
\"\"\"

Question: does the source text support the claim, allowing paraphrase
(different words, same meaning)?

Output rules:
- JSON object only, no prose, no markdown fences.
- `verified` must be a literal boolean (true | false).
- `source_snippet` must be an EXACT contiguous substring of the source text,
  ≤100 characters. Use null when verified is false.

Example:
{{"verified": true, "source_snippet": "supervised five engineers"}}

Now produce the JSON for the inputs above:
"""


# Cap source text we send into the per-claim Layer 2 prompt to keep tokens
# bounded. D.4a is structural; D.4b will tune retrieval / chunking.
GROUND_SOURCE_MAX_CHARS = 4000

# Cap on `source_snippet` length emitted by Layer 2; we trim defensively in
# the parser so a non-compliant model can't blow up downstream payloads.
GROUND_SNIPPET_MAX_CHARS = 100


CLASSIFY_UNSOURCED_SYSTEM_PROMPT = (
    "You categorize unsourced resume claims to decide how to clean them up. "
    "You MUST output JSON only — no prose, no markdown fences, no explanation. "
    "Exactly two fields: `action` (one of \"remove\", \"mark_TBD\", \"ask_user\") "
    "and `rationale` (one short sentence)."
)


CLASSIFY_UNSOURCED_USER_TEMPLATE = """An unsourced claim needs an action chosen.

Claim:
\"\"\"
{claim}
\"\"\"

Decision rubric:
- `ask_user` — the claim contains a verifiable specific (numbers, percentages,
  dates, named entities, scope figures). The candidate can confirm or correct.
- `remove` — the claim is subjective puffery or marketing language with no
  verifiable substance (e.g. "world-class", "industry-leading", "顶级",
  "卓越的", vague superlatives without metrics).
- `mark_TBD` — the claim is descriptive prose without specific numbers and
  without subjective puffery. The candidate should fill in or confirm later.

Output rules:
- JSON object only. No prose. No markdown fences.
- `action` must be exactly one of: "remove", "mark_TBD", "ask_user".
- `rationale` is a single short sentence (≤25 words).

Example:
{{"action": "ask_user", "rationale": "Claim cites a 30% reduction; the candidate can confirm the figure."}}

Now produce the JSON for the claim above:
"""


__all__ = [
    "EXTRACT_SYSTEM_PROMPT",
    "EXTRACT_USER_PROMPT_TEMPLATE",
    "GROUND_SYSTEM_PROMPT",
    "GROUND_USER_PROMPT_TEMPLATE",
    "GROUND_SOURCE_MAX_CHARS",
    "GROUND_SNIPPET_MAX_CHARS",
    "CLASSIFY_UNSOURCED_SYSTEM_PROMPT",
    "CLASSIFY_UNSOURCED_USER_TEMPLATE",
]
