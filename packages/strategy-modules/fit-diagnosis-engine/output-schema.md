# Fit Diagnosis Engine — Output Schema

Structured output emitted by the sub-skill at the end of its 10-step
workflow. The schema bifurcates by `mode`. Both branches share a common
header for traceability.

All sections within a mode are required. Confidence and timing metadata
are required at the top level.

---

## Common header (both modes)

```yaml
sub_skill: fit-diagnosis-engine
mode: pre_rewrite | post_rewrite
target_market: north-america | mainland-china | hong-kong
ppaf_stage: planning | late_feedback        # pre_rewrite → planning; post_rewrite → late_feedback
invoked_at: <ISO 8601 timestamp>
inputs_signature:
  jd_analysis_id: <id>
  competency_profile_id: <id>
  current_resume_hash: <sha256 or null>     # null when mode == pre_rewrite
multi_jd: true | false
confidence: high | moderate | low
competitiveness_rating: high | above_mid | mid | below_mid | low    # both modes; 5-level enum
_method: llm | llm_partial | fallback_no_llm                        # LLM degradation marker (aligned with harness/forecast and harness/review)
```

`competitiveness_rating` is the top-level fit verdict; it appears in
both `pre_rewrite` (mirrors harness/forecast) and `post_rewrite`
(mirrors harness/review) outputs. The 5-level enum is more granular
than a 3-level fit/mixed/stretch axis and aligns with the harness
implementation contract.

`_method` is set by the LLM caller layer, not by the sub-skill author;
it surfaces whether the structured output was fully LLM-driven, partially
fallback-filled, or entirely placeholder. Downstream consumers use it to
decide whether to record a degradation event.

The `inputs_signature` block lets downstream consumers (orchestrator,
review queue, harness audit log) verify the diagnosis was computed against
the expected upstream artifacts.

---

## Mode `pre_rewrite` schema

### Section 4-A — Matching Matrix

Array of objects, one per JD requirement. Required. Aligned with
`harness/forecast/matrix.py` field names and verdict enum.

```yaml
matching_matrix:
  - text: "<JD line>"                              # short field name aligned with harness
    evidence: "<experience or asset; cite source inline if needed>"
    verdict: strong_match | transferable | missing # aligned with harness; transferable = original "partial"
    source: section_b_priority | section_c_tier_1 | section_c_tier_2 | section_c_tier_3
    bridging_or_closure: "<empty if strong_match; otherwise '<tier>; <body>' where tier is 'hard' or 'preferred', body is one-sentence bridge plan (transferable) or closure horizon label (missing, one of: short_term | long_term | not_closeable)>"
```

Field semantics:
- `text` — the JD requirement line, verbatim or paraphrased.
- `evidence` — candidate's specific experience or asset that proves
  fit. Cite source inline (experience-bank entry id or resume section).
- `verdict` — three-value enum aligned with harness:
  - `strong_match` — direct, recent, comparable scope.
  - `transferable` — adjacent, older, or smaller scope but bridgeable.
  - `missing` — no candidate evidence found.
- `source` — links back to the upstream competency profile section that
  generated this requirement. `section_b_priority` for top-priority items,
  `section_c_tier_N` for tiered Must/Should/Nice qualifications.
- `bridging_or_closure` — see constraints below.

Constraints:
- Verdict `strong_match` → `bridging_or_closure` empty.
- Verdict `transferable` → `bridging_or_closure` starts with `hard;` or `preferred;` prefix, then one-sentence bridge plan.
- Verdict `missing` → `bridging_or_closure` starts with `hard;` or `preferred;` prefix, then a closure horizon label.
- Matrix has 0 to 12 items; harness imposes the 12 cap on LLM-generated rows.

Examples:
- `strong_match`: `bridging_or_closure: ""`
- `transferable` against preferred requirement: `"preferred; 面试侧重 Columbia + GPA 3.9 抵消专业差异"`
- `transferable` against hard requirement: `"hard; cover letter 确认时间窗口"`
- `missing` against preferred requirement: `"preferred; long_term"`

The `tier` prefix surfaces hard-requirement risk without adding a separate
schema field; downstream consumers (Inbox UI) render `hard;` rows in red
warning style and `preferred;` rows in yellow informational style.

### Section 4-B — Integrated Assessment

3-5 sentence prose paragraph. Required.

```yaml
integrated_assessment: "<3-5 sentences covering biggest strength, biggest gap, and pool position>"
```

The prose must be readable as a standalone paragraph and must explicitly
cover the candidate's biggest strength, biggest gap, and estimated pool
position. The verdict (strong/mixed/stretch) was previously a separate
field but has been folded into the top-level `competitiveness_rating`
in the common header to align with harness.

### Section 4-C — Optimization Boundary

Two parallel arrays. Required.

```yaml
optimization_boundary:
  rewriting_can_solve:
    - "<short label>: <one-line description>"
  rewriting_cannot_solve:
    - "<short label>: <one-line description>; <closure path: supplement | accept>"
```

Format constraints:
- Each item starts with a short label (≤ 8 chars) followed by `:`,
  then a one-line description.
- Each `cannot_solve` item must end with `;` followed by a closure path
  (one of: `supplement` | `accept`).

Examples:
- can_solve: `"关键词显化: 行业研究 / 市场参与者等 4 个核心 keyword 注入 bullet 标题"`
- cannot_solve: `"无大厂战略 returner: 用 AI Agent 项目对冲差异化; accept"`

### Section 4-D — Multi-JD Coverage Matrix (only when `multi_jd == true`)

```yaml
multi_jd_coverage:
  - jd_id: <id>
    jd_title: "<short title>"
    coverage_pct: <0-100>
    note: "<one-line callout, ≤ 50 chars; empty if coverage is in expected range>"
spread_flag: true | false      # true if (max - min) coverage > 30 percentage points; downstream consumer surfaces remediation
```

Format constraints:
- `note` length ≤ 50 chars (one short line, not a paragraph).
- `note` empty when coverage is in expected range; populated only for
  unusually high or low coverage.

Counts (strong / partial / missing) are intentionally omitted; downstream
consumers can derive them from Section 4-A matrix when needed.

---

## Mode `post_rewrite` schema

### Section 8-A — Hiring Manager Simulation

Aligned with `harness/review/dual_perspective.py` field names.

```yaml
hm:                                       # field key aligned with harness
  highlights:
    - "<bullet the HM would react to positively>"
  concerns:
    - "<area HM would probe in interview>"
  comparison_risk: "<one sentence on where this resume loses to direct-fit candidates>"
```

Each `highlights` and `concerns` item must reference a specific resume
bullet or section by short citation (e.g., "Kearney 1.1" or "summary").
Field name `comparison_risk` (not `comparative_risk`) matches harness
contract; the spec was previously typo'd.

### Section 8-B — HRBP Simulation

Aligned with `harness/review/dual_perspective.py` field names and enums.

```yaml
hrbp:
  keyword_hit_rate: <float 0.0-1.0>          # e.g., 0.667 for 8 of 12 Tier 1 keywords surfaced; UI may render as "8/12"
  hard_filter_match:                          # dict aligned with harness; key = JD requirement, value = match | mismatch | uncertain
    "<JD requirement>": match | mismatch | uncertain
  advance_decision: push_direct | push_with_note | screen_out  # 3-value enum aligned with harness
  decision_rationale: "<one sentence>"
```

Field semantics:
- `keyword_hit_rate` — float 0.0-1.0 stored at schema level; UI surfaces
  as "X/Y" form by multiplying by `tier1_keyword_count` available from
  upstream competency profile.
- `hard_filter_match` — dict with JD requirements as keys. Values:
  - `match` — clearly satisfies the requirement.
  - `mismatch` — clearly fails.
  - `uncertain` — needs verification; surface to user.
- `advance_decision` semantics:
  - `push_direct` — push to business reviewer immediately.
  - `push_with_note` — push to business with annotated concerns.
  - `screen_out` — decline at first pass.

`advance_decision` semantics:
- `direct_pass` — push to business reviewer immediately.
- `pass_with_flags` — push to business with annotated concerns.
- `hold_cohort` — wait for cohort comparison before deciding.
- `reject` — decline at first pass.

### Section 8-C — Six-Axis Radar

Aligned with `harness/review/dual_perspective.py` radar contract.
Default axes (in order): 行业经验, 核心技能, 数据能力, 沟通协作, 文化匹配, JD匹配.

```yaml
radar:
  dimensions:                            # exactly 6 items, key aligned with harness
    - name: "<axis name>"                # e.g., 行业经验; sixth axis can be JD-specific
      resume_score: <int 0-100>          # candidate's score on this axis
      jd_required: <int 0-100>           # JD's expected level on this axis
      citation: "<one-line evidence; spec extension over harness>"
```

Field semantics:
- `name` — axis label. First 5 are conventional (`行业经验 / 核心技能 /
  数据能力 / 沟通协作 / 文化匹配`); the sixth is JD-driven (e.g.,
  "本地生活业务理解" for Douyin local services). Default sixth axis
  in harness is "JD匹配" when no JD-specific name is provided.
- `resume_score` — 0-100 integer; candidate's score on this axis.
- `jd_required` — 0-100 integer; JD's expected level. Gap between
  `resume_score` and `jd_required` drives improvement_suggestions
  prioritization.
- `citation` — one-line evidence justifying `resume_score`. **Spec
  extension over harness**; harness may emit empty string when no
  citation is available, but new wiring should populate this.

Score conventions (apply to both `resume_score` and `jd_required`):
- 90-100 — multiple converging pieces of evidence; outstanding.
- 75-89 — solid evidence; competitive.
- 60-74 — partial evidence; bridgeable in interview.
- 40-59 — weak evidence; significant gap.
- < 40 — minimal evidence; structural issue.

### Section 8-D — Improvement Suggestions

Aligned with `harness/review/dual_perspective.py` field name
`improvement_suggestions` and effort enum.

```yaml
improvement_suggestions:                       # field key aligned with harness
  - text: "<one-line actionable recommendation, target + change inline>"
    effort: wording | supplement_project | long_term
```

Format constraints:
- Up to 5 suggestions (harness imposes the cap).
- `text` is a single line: target (bullet/section reference) + change
  description, joined inline. Rationale and timeline fold into `text`.
- `effort` semantics:
  - `wording` — wording-level change; ~1 hour investment.
  - `supplement_project` — add a project, certification, or short-term
    work; days to weeks.
  - `long_term` — multi-week or longer commitment (new internship,
    coursework, etc.).

Spec note: an earlier version organized recommendations into 3 buckets
(`wording_level / structure_level / project_level`). This was harmonized
to a flat array with `effort` label to match harness contract; UI can
group by `effort` value at render time if a bucket layout is desired.

---

## Confidence rating

Required at common-header level. Definitions:

- `high` — Multiple JDs (≥4) analyzed, complete competency profile loaded,
  market-context file loaded, all citations source-traceable.
- `moderate` — 1-3 JDs, complete competency profile, but some inferences
  about hidden criteria or pool composition; market-context loaded.
- `low` — Single JD, partial competency profile, or default-market
  fallback. Output is provisional and should be re-run after better inputs
  are available.

Confidence MUST be reflected in downstream consumers — review queue should
flag `low` confidence runs for human review even in Mode L.

---

## Schema versioning

```yaml
schema_version: 1.0.0
backward_compatible_with: null     # first version
```

Any schema change requires bumping the major version and updating
downstream consumers (orchestrator, review queue, harness, UI) in lockstep.
