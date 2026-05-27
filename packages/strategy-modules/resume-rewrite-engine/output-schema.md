# Resume Rewrite Engine — Output Schema

10-section structured output (A-J) emitted by `SKILL.md` Step 10. Persisted to
the JobOps review queue. The LaTeX renderer is downstream and reads Section I as
its primary input. All sections required.

The flat-field summary at the bottom is consumed by JobOps to drive the review
queue UI and (when human approval lands) the artifact pipeline.

---

## Section A — Fit Diagnosis

4-6 sentences. Honest, constructive, specific. Like a senior mentor giving a
private assessment. Must address:
- Candidate's natural strengths for the target role (what already works)
- Main weaknesses or under-signaled areas (what's missing or buried)
- Overall packaging opportunity (what the rewrite can realistically achieve)

Not motivational, not harsh.

## Section B — Priority Signals for the Top Half

4-6 numbered items. The signals that must appear in the top third of page one,
based on upstream competency model's screening priorities and candidate's
strongest evidence. Per signal:
- What it is
- Where it should appear (summary / first experience entry / headline)
- What candidate evidence supports it

Ordered by screening priority, not candidate preference.

## Section C — Experience Prioritization and Tradeoff Decisions

Per `workflow/rewrite-methodology.md §3` four-category framework:

### 1. Must Lead and Expand
Each experience / project with reasoning for why it gets max space.

### 2. Keep but Compress
What's valuable, what gets cut.

### 3. Retain as Supporting Signal
How it appears (one-line / skills section).

### 4. Downgrade or Remove
Honest explanation. Required because candidates often have emotional attachment
to experiences that don't serve the target role.

## Section D — Resume Narrative Recommendation

2-4 sentences. Must include:
- Narrative in concrete terms (specific professional identity, not "strong
  candidate")
- How the narrative connects to upstream Section B core hiring logic
- The anti-narrative (what the resume must NOT accidentally read like)

Lens-specific exemplars from `role-lenses/<X>-*.md` §2.3.

## Section E — ATS / AI Optimization Plan

Structured keyword plan with placement guidance. Must include:
- Highest-value keywords (from upstream Section D, Tiers 1-2)
- Semantic equivalents for natural variation
- Tool / method terms candidate can credibly claim
- Action verbs matched to lens
- Specific placement: which keywords go where
- Credibility flags: terms that would reduce credibility if forced

## Section F — Section-by-Section Rewrite Guidance

For every major section / experience the candidate provided:

1. **Purpose statement** — what this section proves for the target role
2. **Keep / cut / emphasize decisions** — explicit
3. **Rewritten bullet points** — ready-to-use, fully rewritten

Bullet quality requirements:
- Each contains ≥3 of the 6 elements (Action / Context / Method / Contribution
  / Outcome / Scale)
- No "Responsible for" / "Duties included"
- Keywords integrated naturally
- Scannable in 3 seconds
- Length: 1.5-2.5 lines per bullet (shorter for supporting)

## Section G — Market Localization Notes

Apply `market-contexts/<target_market>.md` resume-side rules. Explain what
changes because of target market:
- What gets prioritized
- Which bullet styles work best (achievement / scope / credential)
- Length / density choices
- Bilingual or local-context signaling
- Formatting / content emphasis changes
- Platform-specific considerations

## Section H — Resume Structure Recommendation

- Optimal section ordering for this lens × market combination
- Whether a professional summary is useful (and what it contains)
- Skills section handling (grouped vs listed; what to include / exclude)
- Projects vs internships prominence
- What belongs in the first half of page one
- Page count recommendation

## Section I — Final Resume Draft

Polished, complete resume draft in **plain text** (the LaTeX renderer is
downstream and consumes this section). Format:
- Name and contact placeholder (or actual if provided)
- Summary (if recommended in Section H)
- Experience (in priority order from Section C)
- Education
- Skills
- Additional sections as recommended

All decisions from Sections A-H implemented. Keywords integrated per Section E.
Market localization applied per Section G.

**For Tier-1 light tailoring runs** (per `docs/architecture/ARCHITECTURE.md §9`):
only headline / summary / skills section change in this section; experience
bullets remain identical to the canonical resume. The diff is reviewed in the
queue.

## Section J — Risk Flags

Numbered list of weaknesses that **cannot be solved by rewriting alone**.
Required (≥1 item) — there are always some.

Categories to assess:
- Lack of quantification
- Unclear business impact
- Insufficient technical depth
- Insufficient role-specific evidence
- Fragmented narrative
- Weak seniority signaling
- Limited market-specific credibility
- Credential gaps

Per flag:
- The weakness
- Why it matters for this role
- What the candidate could do beyond rewriting (gain experience / certification
  / interview prep angle)

Tone: constructive. Frame as "what would make you even stronger" not "why you
won't get hired."

---

## Flat-field summary (for JobOps consumption)

Emit as YAML / JSON at the end:

```yaml
job_id: <jobops-assigned id, mirrors upstream>
matched_resume_version: A | B | C | D | HC
selected_experience_ids: [list]                 # ordered by Section C priority
protected_sections: [list]                       # untouched per identity locking
tailoring_tier: 1 | 2                            # per ARCHITECTURE.md §9
rewrite_plan_hash: <stable hash for queue dedup>
quality_checklist:
  pass_1_keyword_injection: complete | partial | failed
  pass_1_5_chinese_readability: complete | n/a   # n/a if english resume
  pass_2_ai_voice_cleanup: complete | partial | failed
  pass_3_truthfulness: complete | partial | failed
  unsourced_claims: [list]                       # any [请确认] markers in Section I
risk_flags: [list]                               # mirrors Section J entries
artifact_targets:                                # downstream rendering jobs
  - format: latex
    template: assets/knowledge-base/references/templates/resume-zh.tex | <other>
    output_path: <suggested filename, e.g. Alina_<role>.tex>
review_required: true                            # Tier 2 always; Tier 1 dry-run initially
```

`pass_3_truthfulness: failed` or any non-empty `unsourced_claims` → review
queue must hold the artifact for human approval before any LaTeX rendering or
submission. This is the final safety gate per root `SKILL.md` 真实性护栏.
