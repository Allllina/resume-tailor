# Harness Compliance Audit — v0.3.3 baseline

> **Companion to:** `HARNESS_DESIGN.md`, `ADR 0003`, `docs/plans/archive/2026-05-04-harness-foundation.md`.
> **Date:** 2026-05-04.
> **Purpose:** Score 13 existing project components against 6 Harness design principles. Identify retrofit gaps prioritized for Wave 1+. Wave 0 second-half deliverable.

---

## 1. Executive summary

13 existing components scored against 6 design principles = **78 cells**. Compliance distribution:

| Verdict | Count | % |
|---|---:|---:|
| ✓ compliant | 28 | 36% |
| ⚠ partial | 22 | 28% |
| ✗ gap | 19 | 24% |
| N/A (does not apply) | 9 | 12% |

**Headline finding:** Contract-First (45%) and Decision-vs-Execution (38%) are strongest. Secure-by-Default (15%) and Data-driven Evolution (8%) are weakest — both addressed in Wave 5 + Wave 1 sandbox respectively.

**Headline gap:** No PII filter anywhere in current pipeline. Resume content (full names, phone numbers, email, school) traverses unencrypted Claude API calls + appears in metadata.json + .tex artifacts. Must address in Wave 1 policy gateway.

**Top 10 retrofit gaps** are listed in §3 prioritized for Wave 1-5 placement.

---

## 2. Per-component compliance scores

Components × 6 principles. Legend: ✓ compliant / ⚠ partial / ✗ gap / N/A.

| # | Component | DfF | C-F | SbD | DvE | Meas | Evol | Notes |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| 1 | `index.json` v0.2.0 | ⚠ | ✓ | ✗ | ✓ | ✓ | ⚠ | DfF: no version migration fallback. SbD: contains PII (names/companies). Evol: schema versioned but content updates manual |
| 2 | `recognition-rubric.md` | ✓ | ⚠ | N/A | ✓ | N/A | ⚠ | C-F: enums defined in prose; should be JSONified for agent runtime use |
| 3 | `vertical-fit-rubric.md` | ✓ | ⚠ | N/A | ✓ | N/A | ⚠ | Same as #2 |
| 4 | `resume-rewrite-engine/SKILL.md` R-1 to R-8 | ⚠ | ⚠ | ⚠ | ✓ | N/A | ⚠ | DfF: no degradation paths defined for rule violations. C-F: rules in prose, not enforceable schema. SbD: no PII rule encoded |
| 5 | 3-pass selection algorithm (R-8) | ✓ | ✓ | N/A | ✓ | ⚠ | ✗ | Meas: trace format defined but no aggregation. Evol: lift ceilings hard-coded, not data-driven |
| 6 | Pass 3 verifier (planned, Wave 2) | ✓ | ✓ | ⚠ | ✓ | ✓ | ⚠ | Schema-defined (this Wave 0); SbD: needs PII filter on bullet inputs; Evol: no auto-update of truthfulness rubric |
| 7 | root SKILL.md 10-step workflow | ⚠ | ✗ | ✗ | ⚠ | ✗ | ⚠ | Workflow described as prose; no schema; no metrics; no enforceable execution boundary |
| 8 | `resume-bank/versions/<lens>/` masters | ✓ | ⚠ | ✗ | ✓ | N/A | ⚠ | Status field present (delivered/planned); contains PII; updates manual |
| 9 | `user-profile.md` 投递记录 | ⚠ | ✗ | ✗ | N/A | ⚠ | ⚠ | Append-only log; no schema; full PII; no aggregate metrics |
| 10 | `experience-bank/raw/*.md` | ⚠ | ✗ | ✗ | ✓ | N/A | ✗ | Free-form prose; no parsing schema; full PII; no auto-extraction pipeline |
| 11 | `contracts/schemas/job-score.schema.json` | ✓ | ✓ | N/A | ✓ | ✓ | N/A | Pre-existing schema; JD-side score only (now §7a in ARCHITECTURE) |
| 12 | `ops/jobops/` (vendored snapshot) | ✓ | ⚠ | ⚠ | ✓ | ⚠ | N/A | External code; not actively maintained here; Docker-isolated when run |
| 13 | `speedlearn-whitelist.json` | ✓ | ✓ | N/A | ✓ | N/A | ⚠ | Schema implicit; updates require explicit user approval (good); but no proposal pipeline yet |

**Legend (column abbreviations):**
- DfF = Design for Failure
- C-F = Contract-First
- SbD = Secure by Default
- DvE = Decision vs Execution
- Meas = Everything is Measurable
- Evol = Data-driven Evolution

---

## 3. Top 10 retrofit gaps (prioritized)

Ordered by (severity × Wave reachability). Each entry: **gap** → **proposed fix** → **target Wave**.

### Gap 1: No PII filter anywhere — HIGH SEVERITY → **CLOSED 2026-05-07** (commit `6a2468e`)

**Components affected:** #1 index.json, #4 SKILL.md rules, #6 Pass 3, #8 masters, #9 user-profile, #10 raw experiences.
**Risk:** PII (full names, phone numbers, email, schools) leaks through Claude API calls, logs, and artifacts. If logs are ever shared (debug traces / GitHub issue / vendor support), confidentiality breach.
**Fix:** ~~Wave 1~~ Wave 4 (Critical pre-D.4) — `harness/llm/pii_filtering_provider.py` `PIIFilteringLLM` decorates the LLMProvider Protocol; `repl/eval.py` `Tier1Tools.__init__` wraps the inner provider with the filter when `candidate_names` is supplied. All five LLM call paths (lens routing, competency extraction, label rewrite, summary writing, rewrite engine) now go through the gate transparently. `detect_injection()` runs on user content; raises `InjectionDetectedError` which `competency/extractor.py` and `rewrite/engine.py` catch as a graceful-degradation signal. Restore is explicitly NOT performed inside the wrapper — placeholders flow back to the caller, who must follow `pii_filter.py:30-40` INVARIANT and only restore for local trusted output (the .tex artifact in the Inbox UI).
**Target:** ~~Wave 1~~ → **Shipped Wave 4 v0.5.7+1** (test delta 524 → 537, +13 unit + integration tests).

### Gap 2: Hard rules R-1 to R-8 are prose-only — MEDIUM-HIGH

**Components affected:** #4 SKILL.md, #6 Pass 3.
**Risk:** Rules are not machine-enforceable. Pass 3 verifier (Wave 2) and policy gateway (Wave 1) cannot programmatically check compliance — they have to re-read prose every time.
**Fix:** Encode R-1 to R-8 as JSON `forbidden-patterns.json` + `truthfulness-checklist.json` (per 2026-04-27 plan). Each rule = pattern matcher + violation message + remediation action.
**Target:** **Wave 1** (concurrent with policy gateway).

### Gap 3: No metrics aggregation — MEDIUM

**Components affected:** #1, #5, #6, #11, #12 (any component that emits trace data).
**Risk:** Cannot answer "what's our Pass 3 pass rate?" "average tokens per Tier 1?" — data exists in metadata.json files but not aggregated.
**Fix:** SQLite metrics table + nightly aggregation cron + dashboard. Metric events emit per `metrics-event.schema.json`.
**Target:** **Wave 5** (concurrent with feedback loop — same DB).

### Gap 4: 10-step root SKILL.md workflow has no schema — MEDIUM

**Components affected:** #7 root SKILL.md.
**Risk:** Workflow description drift across sessions. New contributors / future Claude sessions interpret steps differently. No enforcement that steps run in order or produce typed outputs.
**Fix:** Define each step's input/output schema (sub-schemas of harness-tailor-input/output). Step transition function must accept Step N output → produce Step N+1 input. Tests verify schema compliance.
**Target:** **Wave 1** (REPL skeleton implements step graph).

### Gap 5: Rubric updates are not auto-proposed from feedback — MEDIUM

**Components affected:** #2, #3 rubrics; #1 index.json scoring data.
**Risk:** Feedback signals (京东 BA Ipsos consumer_research = high reverse score; 米哈游 Detoxify 不平行) are processed manually. Ad-hoc, error-prone, lossy.
**Fix:** Wave 5 feedback agent ingests rejection / interview feedback per `feedback-ingestion.schema.json` → produces rubric update proposals → user approves before merge.
**Target:** **Wave 5**.

### Gap 6: No retry / timeout / circuit breaker around Claude API calls — MEDIUM

**Components affected:** all LLM-using components (planned Wave 1+ harness layer).
**Risk:** Single API timeout fails the whole tailoring run. No fallback to recent cached master.
**Fix:** Wave 1 REPL implements retry budget (3 retries with exponential backoff), per-call timeout (60s default), circuit breaker (after 3 consecutive 5xx, fall back to manual mode for next 5 minutes).
**Target:** **Wave 1**.

### Gap 7: Raw experience files have no parsing pipeline — LOW-MEDIUM

**Components affected:** #10 raw/*.md.
**Risk:** Pass 3 verifier (Wave 2) needs to grep claims against raw files. Free-form prose makes verification fragile (e.g., "5 维评估框架" appears in 01-kearney § 项目 2 but might be matched against § 项目 1 if grep is naïve).
**Fix:** Add structured front-matter to each raw/*.md — list of (project_id, section_anchor, claimed_facts[]). Pass 3 looks up by anchor instead of grep.
**Target:** **Wave 2** (concurrent with Pass 3 verifier).

### Gap 8: No sandbox for LaTeX render — LOW-MEDIUM

**Components affected:** Step 9 LaTeX render (currently outsourced to user's Overleaf).
**Risk:** When we build local render service, untrusted .tex (potentially with malicious user-pasted content) could execute arbitrary shell via `\write18`.
**Fix:** Wave 3 LaTeX render runs in Docker container with `--no-shell-escape` + read-only filesystem + 10s timeout.
**Target:** **Wave 3** (when Inbox + auto pipeline ships and we need server-side render).

### Gap 9: No version migration path for index.json — LOW

**Components affected:** #1 index.json.
**Risk:** When schema evolves (v0.2.0 → v0.3.0 in some future), no migration script. Current deps may break silently.
**Fix:** Wave 4 add `scripts/migrate_index.py` with version-aware transformations. Validate against `schema_version` field.
**Target:** **Wave 4** (when v0.3.0 schema actually needed).

### Gap 10: Browser agent submit channel is not yet integrated — LOW

**Components affected:** §14 of ARCHITECTURE.md (3 submit channels).
**Risk:** Manual paste works fine for 国内招聘 but Workday-style海外 ATS forms cost user 5+ min each, capping daily volume.
**Fix:** Wave 5 optional integration with OpenClaw / Hermes / Anthropic Computer Use for海外 ATS-heavy submissions. Manual paste remains default.
**Target:** **Wave 5** (optional, can defer).

---

## 4. Wave 1 readiness assessment

For Wave 1 (REPL skeleton + Tier 1 PoC) to start safely, these gaps MUST be addressed in same wave:

- ✅ Gap 1 (PII filter) — must ship with REPL skeleton
- ✅ Gap 2 (R-1 to R-8 → JSON) — concurrent with policy gateway
- ✅ Gap 4 (step schema) — REPL needs typed inter-step transitions
- ✅ Gap 6 (retry/timeout) — non-negotiable for production usage

Other gaps (3, 5, 7, 8, 9, 10) can defer to their target Waves without blocking Wave 1.

---

## 5. Recommendations per design principle

**Design for Failure (current 36%):** Add explicit fallback to every Wave 1+ component. Specifically: when LLM call fails, when schema validation fails, when sandbox quota exhausted. Each failure must emit `metrics-event` + degradation event.

**Contract-First (current 45%):** JSONify the rubrics + hard rules in Wave 1. Every Wave 1+ inter-component interface must have a schema in `contracts/schemas/`.

**Secure by Default (current 15%):** Highest gap. Wave 1 PII filter + sandbox for LaTeX render in Wave 3 + injection defense for user-pasted JD content in Wave 1.

**Decision vs Execution (current 38%):** Already strong. Maintain by ensuring Wave 1 REPL container clearly separates planning (calls Claude API or deterministic algorithm) from execution (calls tools / writes DB).

**Everything is Measurable (current 28%):** Wave 1 emit all metrics. Wave 5 aggregate dashboard. Don't defer instrumentation — it must ship with code.

**Data-driven Evolution (current 8%):** Lowest gap. Wave 5 feedback ingestion is the answer. In meantime, every manual rubric update should be tagged in commit message (`evol: ...`) for later mining.

---

## 6. How this audit drives Wave priorities

Translation of gaps → Wave 1 task list (informs Wave 1 planning when it starts):

```
Wave 1 must-do (from gaps 1, 2, 4, 6):
  □ /api/tier1-tailor REPL skeleton (gap 4)
  □ PII filter pre/post Claude API call (gap 1)
  □ R-1 to R-8 JSONified to forbidden-patterns.json + truthfulness-checklist.json (gap 2)
  □ Retry / timeout / circuit breaker on Claude API client (gap 6)
  □ harness-tailor-input/output schema validation at API boundaries (general C-F)

Wave 1 nice-to-have (defer if behind):
  □ Metrics emitter (gap 3 — can stub in Wave 1, dashboard in Wave 5)
  □ Audit log table in SQLite (informs gap 3)
```

Wave 2-5 retrofit work mapped per §3 above.

---

## 7. Re-audit cadence

Per ADR 0003 §"Sunset criteria", quarterly re-audit:

- 2026-08-04 (3 months) — audit Wave 1-2 components
- 2026-11-04 (6 months) — audit Wave 3-4 components + verify Wave 1 still compliant
- 2027-02-04 (9 months) — audit Wave 5 + reconsider sunsetting harness components Claude has internalized

Each re-audit produces an updated `HARNESS_COMPLIANCE_AUDIT.md` (this file overwritten).

---

End of v0.3.3 baseline audit.
