# Quality Pass Runner — Output Schema

Structured output emitted by the sub-skill at the end of its 10-step
workflow. Schema has 4 pass-level sections + 1 aggregate section.

All sections are required except `pass_1_5_chinese_readability`, which
is `null` when `target_market` is not Chinese.

---

## Common header

```yaml
sub_skill: quality-pass-runner
target_market: north-america | mainland-china | hong-kong
ppaf_stage: late_feedback
invoked_at: <ISO 8601 timestamp>
inputs_signature:
  rewritten_resume_hash: <sha256>
  competency_profile_id: <id>
  experience_bank_version: <id or commit sha>
final_resume_text: "<full cleansed resume text after all 4 passes>"
aggregate_verdict: pass | partial_pending_user | fail
pending_user_review_flag: true | false
confidence: high | moderate | low
```

`final_resume_text` is the text that downstream consumers
(`latex-renderer`, `fit-diagnosis-engine` `post_rewrite`) should use as
their input. It is NOT the same as the input `rewritten_resume`; it is
the post-pass version.

---

## Section Pass 1 — Keyword Injection

```yaml
pass_1_keyword_injection:
  injected_keywords:
    - keyword: "<keyword>"
      target_location: "<bullet/section ref where injected>"
      injection_method: title_keyword | inline_phrase | skill_bar | summary_addition
  hit_rate_before: "<int>/<int>"      # e.g., "5/12" before injection
  hit_rate_after: "<int>/<int>"       # e.g., "10/12" after injection
  unable_to_inject:
    - keyword: "<keyword>"
      reason: "<one line; e.g., no natural injection point in available experiences>"
  verdict: pass | partial | fail
```

Verdict criteria:
- `pass` — `hit_rate_after` ≥ 80% of Tier 1 + selected Tier 2 keywords.
- `partial` — `hit_rate_after` 60-80%, with all unable-to-inject items
  having defensible reasons.
- `fail` — `hit_rate_after` < 60% OR injection introduced fabricated
  content (R-1 violation).

---

## Section Pass 1.5 — Chinese Readability (conditional)

```yaml
pass_1_5_chinese_readability:
  enabled: true | false              # false when target_market is not Chinese
  flagged_phrases:
    - original: "<phrase>"
      replacement: "<idiomatic Chinese>"
      reason: english_direct_translation | non_universal_abbreviation
  preserved_english_terms:
    - term: "<term>"
      reason: "<one line; e.g., standard technical term>"
  verdict: pass | partial | fail
```

When `enabled: false`, all other fields in this section are `null` or
empty arrays. Verdict is `pass` by convention.

---

## Section Pass 2 — AI Taste Removal

```yaml
pass_2_ai_taste_removal:
  replacements_applied:
    - original: "<flagged term>"
      replacement: "<replacement>"
      location: "<bullet/section ref>"
  protected_skipped:
    - term: "<flagged term>"
      reason: in_jd | candidate_idiom_authentic
  verdict: pass | partial | fail
```

`protected_skipped` records every term that appears in
`quality-pass.md` replacement table BUT was preserved because it
appears in the JD or is part of the candidate's authentic voice.

Verdict criteria:
- `pass` — no AI-taste term remains except those in `protected_skipped`.
- `partial` — some terms remain but are borderline (one-off use, not
  pattern); user review recommended.
- `fail` — multiple AI-taste terms remain unaddressed.

---

## Section Pass 3 — Truthfulness Verification

```yaml
pass_3_truthfulness:
  verified_claims_count: <int>
  unsourced_claims:
    - claim: "<exact phrase from resume>"
      location: "<bullet/section ref>"
      severity: high | medium
      type: quantification | scope | role_description | other
  identity_lock_check: pass | fail
  identity_lock_violations:
    - field: "<company/position/school/degree/date>"
      resume_value: "<value>"
      source_value: "<value>"
  verdict: pass | partial_pending_user | fail
```

Verdict criteria:
- `pass` — zero unsourced claims; identity_lock_check `pass`.
- `partial_pending_user` — some unsourced claims, all severity
  `medium` or below; identity_lock_check `pass`. User must approve or
  amend each via Inbox UI.
- `fail` — any high-severity unsourced claim that user cannot resolve;
  OR identity_lock_check `fail`. Resume cannot be released.

`severity: high` triggers when:
- Claim is a quantified number / percentage / scope.
- Claim is a deliverable type / role description not present in source.

`severity: medium` triggers when:
- Claim is a qualitative phrase (e.g., "structured thinking") not
  directly cited but reasonable inference from source.

---

## Aggregate verdict logic

| Pass 1 | Pass 1.5 | Pass 2 | Pass 3 | aggregate |
|---|---|---|---|---|
| any | any | any | `fail` | `fail` |
| any | any | any | `partial_pending_user` | `partial_pending_user` |
| any `fail` | any | any | `pass` | `fail` |
| `pass` | `pass` | `pass` | `pass` | `pass` |
| `partial` | any | any | `pass` | `partial_pending_user` |
| any | `partial` | any | `pass` | `partial_pending_user` |
| any | any | `partial` | `pass` | `partial_pending_user` |

`pending_user_review_flag` is `true` whenever `aggregate_verdict` is
`partial_pending_user` or `fail`.

---

## Confidence rating

```yaml
confidence: high | moderate | low
```

Definitions:
- `high` — all 4 passes ran with full reference files loaded; Pass 3
  used live experience-bank source; all verdicts are deterministic.
- `moderate` — one or more passes used cached/stale reference; Pass 3
  source-grounding partial; verdicts are directionally correct but
  may need re-run.
- `low` — input validation marginal (e.g., very short resume, sparse
  experience-bank); strongly recommend re-run after upstream fix.

`low` confidence triggers `pending_user_review_flag = true` even when
all individual verdicts are `pass`.

---

## Schema versioning

```yaml
schema_version: 1.0.0
backward_compatible_with: null
```
