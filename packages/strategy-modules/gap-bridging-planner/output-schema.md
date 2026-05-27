# Gap Bridging Planner — Output Schema

Structured output emitted by the sub-skill at the end of its 10-step
workflow. Schema is flat (no mode bifurcation) since this sub-skill has
only one invocation pattern (forward-looking, between diagnosis and
rewrite).

All sections are required. Confidence is required at the top level.

---

## Common header

```yaml
sub_skill: gap-bridging-planner
target_market: north-america | mainland-china | hong-kong
ppaf_stage: planning
invoked_at: <ISO 8601 timestamp>
inputs_signature:
  fit_diagnosis_id: <id>
  competency_profile_id: <id>
application_timeline: immediate | near | mid
confidence: high | moderate | low
multi_jd_conflict_flag: true | false
```

---

## Section 5a — Reframe Directives

Array of directives, one per `partial` row in fit-diagnosis Section 4-A.

```yaml
reframe_directives:
  - matrix_row_id: <id>                   # cross-reference to fit-diagnosis Section 4-A row
    target_experience: "<experience-bank entry id, e.g., 01-kearney.md project 1>"
    target_bullet_id: "<resume bullet id, e.g., kearney_1.1>"
    keyword_to_inject: "<JD keyword phrase, e.g., 行业研究>"
    framing_directive: "<one sentence on how to inject without fabrication>"
    source_evidence: "<one-line experience-bank citation that justifies the injection>"
```

Format constraints:
- `framing_directive` ≤ 80 chars (one sentence, not a paragraph).
- `source_evidence` must be a real experience-bank reference; if no
  source exists, the row should be in 5b (Add) instead, not here.

Example:
```yaml
- matrix_row_id: 4a_row_01
  target_experience: 01-kearney.md project 1
  target_bullet_id: kearney_1.1
  keyword_to_inject: 行业研究
  framing_directive: 在 1.1 标题加入"下游应用行业研究"使行业研究 keyword 显化
  source_evidence: 01-kearney.md L9 项目 1 长电科技十五五战略规划，研究范围包含下游应用赛道
```

---

## Section 5b — Add Suggestions

Array of supplemental work items, classified by horizon and timeline-aware
action flag.

```yaml
add_suggestions:
  - gap_label: "<short label of the gap, e.g., 0 互联网增长经验>"
    horizon: short_term | mid_term | not_closeable
    action: plan_now | defer | accept
    suggestion: "<one sentence on what to do, time investment, surface location>"
```

Format constraints:
- `suggestion` ≤ 100 chars.
- `action` derives from `horizon` × `application_timeline`:
  - horizon `short_term` → action `plan_now` (regardless of timeline)
  - horizon `mid_term` + timeline `immediate` → action `defer`
  - horizon `mid_term` + timeline `near` or `mid` → action `plan_now`
  - horizon `not_closeable` → action `accept`

Example:
```yaml
- gap_label: 0 本地生活业务理解
  horizon: short_term
  action: plan_now
  suggestion: 投递前 5-7 天读 5 篇本地生活白皮书 + 写 1-2 篇抖音生活服务 case 拆解，面试用
```

---

## Section 5c — Skill Gap + Structural Plan

Three sub-sections.

### 5c-1 Skill Bar Adjustments

```yaml
skill_bar_adjustments:
  add_to_bar:
    - skill: "<skill name>"
      tier: A | B
      placement_row: technical | ai | language | other
      rationale: "<one line; cite experience evidence>"
  remove_from_bar:
    - skill: "<skill name>"
      reason: "<one line; e.g., low JD relevance, low candidate proficiency>"
  do_not_add:
    - skill: "<skill name>"
      reason: "<Tier C — does not have the skill, do not list>"
```

Format constraints:
- `tier`: only `A` (会但没写) or `B` (会一点) appear here. Tier C skills
  appear in `do_not_add` if the JD lists them; otherwise they are absent.
- `rationale` ≤ 80 chars.

### 5c-2 Section Ordering Recommendations

```yaml
section_ordering:
  experience_section_order: ["<exp_id>", "<exp_id>", ...]
  experience_section_emphasis:
    - exp_id: "<id>"
      bullet_count_recommendation: <int>
      rationale: "<one line>"
  missing_sections:
    - section_name: "<e.g., self_introduction, language_proficiency>"
      action: add | acknowledge_absence
      rationale: "<one line>"
```

Format constraints:
- `experience_section_order` is the recommended top-down ordering of
  experience sections in the resume, by experience id.
- `bullet_count_recommendation` is a positive integer; resume-rewrite-engine
  uses this as a soft target.

### 5c-3 Multi-JD Conflict (only when `multi_jd_conflict_flag == true`)

```yaml
multi_jd_conflict:
  conflicting_directives:
    - jd_a: "<id>"
      jd_b: "<id>"
      conflict_summary: "<one line>"
  proposed_resolution: master_with_jd_specific | branch_versions | accept_compromise
  rationale: "<one sentence>"
```

Format constraints:
- `conflict_summary` ≤ 80 chars.
- `proposed_resolution` semantics:
  - `master_with_jd_specific`: one master version covers most JDs; small
    JD-specific tweaks at submit time.
  - `branch_versions`: build separate resume versions for each JD cluster.
  - `accept_compromise`: accept a slight under-fit to maintain a single
    version.

---

## Confidence rating

```yaml
confidence: high | moderate | low
```

Definitions:
- `high` — every `partial` matrix row has a concrete reframe directive
  with strong source evidence; every `missing` row has a clear add
  suggestion or accept-as-gap rationale.
- `moderate` — most rows handled; some directives have weaker source
  evidence or ambiguous bridging hypothesis.
- `low` — multiple weak directives; recommend re-running upstream
  (`fit-diagnosis-engine` or `role-competency-extractor`) before
  rewrite engine consumes this plan.

`low` confidence triggers a Mode F review-queue flag even in Mode L.

---

## Schema versioning

```yaml
schema_version: 1.0.0
backward_compatible_with: null
```
