# Role Competency Extractor — Output Schema

9-section structured output emitted by `SKILL.md` Step 10. Persisted to JobOps
review queue and consumed by the scoring layer + `resume-rewrite-engine`.

All sections are required. Sections may be brief but must exist (Section I is
mandatory even at high confidence). The flat-field summary at the bottom maps to
`contracts/schemas/job-score.schema.json` for type validation.

---

## Section A — Role Definition

3-5 sentences. Authoritative briefing of what the role fundamentally hires for,
what business problem it solves, and what candidate profile is most likely to
succeed. Tone: like briefing a recruiter in 30 seconds.

## Section B — Core Hiring Logic

4-6 numbered items, ordered from highest to lowest screening priority. Per item:

1. Priority name (concise label)
2. What it means in practice (2-3 sentences)
3. Why it matters for the role (1-2 sentences)
4. Credible proof signals (what evidence on a resume satisfies it)

The first item must be the single most important thing the employer is looking
for.

## Section C — Unified Qualification Model (3 Tiers)

Per `workflow/competency-framework.md §5`:

### Tier 1: Must-Have
### Tier 2: Strongly Preferred
### Tier 3: Nice-to-Have

Per item in every tier:
- Qualification / capability name
- Practical meaning (what it looks like day-to-day)
- Credible proof signals

Items must be specific and role-contextualized — not "strong analytical skills"
but "ability to independently structure an ambiguous business question into a
testable analytical framework using available data."

## Section D — ATS / AI Keyword Architecture

Per `workflow/keyword-extraction.md` 5-tier:

### Tier 1: Core Role Keywords
### Tier 2: Capability Keywords
### Tier 3: Tools / Methods / Frameworks
### Tier 4: Action Verbs
### Tier 5: Semantic Equivalents

For each tier, mark the 3-5 highest-value terms (frequency × placement weight).
Keywords are emitted in the JD's source language; for blended `target_market`
cases (e.g., bilingual roles) emit both forms.

## Section E — Shared Patterns vs Company-Specific Differences

Required for multi-JD analysis. Single-JD analysis: emit "single-JD; cross-company
patterns not derivable" + skip subsection content.

### Cross-Company Consensus
Requirements appearing consistently across the JDs (role family baseline).

### Company-Specific Variations
Requirements unique to individual employers. Note the company (or JD #) and
explain what differs.

Also note: industry / employer-type / team-function variation drivers.

## Section F — Hidden Screening Criteria

3-5 items per `workflow/competency-framework.md §6`. Per item:

1. The inferred criterion
2. The signal in the JDs that led to the inference
3. The implication (how a candidate addresses this on resume / in interviews)

Tone: analytical, evidence-based. Every inference cites JD language or
structural patterns.

## Section G — Market-Specific Interpretation

Apply `assets/knowledge-base/references/market-contexts/<target_market>.md` JD
解读 layer. Must address:
- What gets prioritized in this market's screening norms
- How experience should be framed (achievement / scope / credential orientation)
- Which proof signals matter most in this market
- Resume style choices that work
- Cultural / linguistic conventions affecting how qualifications are perceived

If `target_market` was not specified, default to `north-america` and note this.

## Section H — Resume Strategy Implications

Actionable guidance for `resume-rewrite-engine`:

### Emphasize Most
What dominates the top half of the resume + strongest bullets.

### De-Emphasize
What to minimize / omit because it dilutes perceived fit.

### Top-Half Resume Content
Specific content for summary / headline / first experience entry.

### Natural Keyword Placement
Where Section D's highest-value keywords should appear without forcing.

### Common Mistakes
3-5 role-specific pitfalls (not generic resume advice).

## Section I — Limitations and Confidence

1-3 paragraphs. Mandatory, even at high confidence.

Must address:
- Number of JDs analyzed and whether sufficient for stable conclusions
- Inconsistencies across JDs that reduce confidence
- Whether role family was cleanly validated or showed instability
- Areas where analysis is inferential rather than directly supported
- Seniority spread effects (if applicable)

Confidence rating (one of):
- **High** — 4+ well-aligned JDs, consistent patterns
- **Moderate** — 2-3 JDs or some alignment issues; directionally sound but may not generalize
- **Low** — 1 JD, significant inconsistencies, or unstable role family; conclusions provisional

---

## Flat-field summary (for JobOps consumption)

Emit at the end as a JSON-shaped block for downstream type validation against
`contracts/schemas/job-score.schema.json`:

```yaml
job_id: <jobops-assigned id>
role_family: A_strategy_research | B_data_analytics | C_product_ops | D_finance_markets | HC_human_capital | other
target_market: north-america | mainland-china | hong-kong
primary_lens: A | B | C | D | HC
scenario_loaded: <single scenario filename, e.g. consulting>
secondary_lens: A | B | C | D | HC | null
blend_ratio: <number 0-100 or null>     # primary lens %
visa_risk: clear | generic_authorized_neutral | sponsor_positive | blocked | unknown
competency_tags: [list]                  # business / analytics / stakeholder / org / product / research / finance
evidence_requirements: [list]            # proof types this resume must show
resume_version_hints: [A | B | C | D | HC, ...]   # ordered by fit
scoring_notes: <free-form text; includes blend rationale, hidden screening
                summary, market-localization summary>
confidence: high | moderate | low
```

The flat-field summary must be internally consistent with sections A-I. If
`scoring_notes` mentions a secondary lens, `secondary_lens` and `blend_ratio`
must be populated.
