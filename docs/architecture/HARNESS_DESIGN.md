# Harness Design — `jobsearch-ops-agent`

> **Status:** v0.3.3 foundation (2026-05-04). Canonical reference.
> **Companion docs:** `ARCHITECTURE.md` (system architecture), `decisions/0003-harness-as-architectural-foundation.md` (ADR), 6 schemas in `contracts/schemas/`.
> **Sunset criteria:** see ADR 0003 §"Sunset criteria".

This document defines how Harness Engineering is operationalized in this project. It is the canonical vocabulary — when ARCHITECTURE.md / SKILL.md / future plans use terms like "REPL container", "policy gateway", "control plane", they refer to the definitions here.

---

## 1. Introduction

**Harness Engineering** = engineering machinery wrapping an LLM that turns its non-deterministic output into a controllable, observable, auditable system. The harness is not the model; it surrounds the model with ordered constraints (contracts, retries, timeouts, fallbacks, metrics, policies) so that LLM behavior becomes a predictable component of a larger pipeline.

**Why this project needs it.** The end goal is 20-JD/天 stable投递 under truthfulness护栏 — see `docs/plans/archive/2026-05-04-harness-foundation.md` Wave 1-5. At that scale:

- Pure prompt engineering is too brittle (米哈游试跑 7 处编造、Anker 1 处 5 维框架 fail)
- One-shot Claude session per JD is too expensive in user time (5-10 min/JD vs target 3-5 min Tier 1)
- Cross-session memory cannot live in conversation history (state must outlive any one Claude call)
- Reputation risk requires audit trail (every claim → which source file / which evidence)

Harness machinery solves all four. Source idea: industry essay on Harness Engineering (Anthropic 2026).

**Sunset clause.** Each harness layer is provisional. As Claude internalizes capabilities (better self-grounding for Pass 3, better long-context coherence for state, better tool selection for routing), specific harness primitives retire. Harness is means, not end. Re-evaluate quarterly.

---

## 2. PPAF cycle mapped to project

The Agent core loop is **Perception → Planning → Action → Feedback** (PPAF). Each tailoring run executes one or more PPAF cycles. Mode A (auto pipeline) and Mode B (manual customize) both run the same cycle; they differ only in user-intervention frequency.

> **Implementation note (Wave 4 D.3+).** The harness implements a **five-stage variant** with FEEDBACK split into "early" (verdict scoring + tier routing — runs between PLANNING and ACTION so ACTION can dispatch Tier 1 vs Tier 2/3) and "late" (artifact write, lifecycle seed, Pass 3 verifier output). Handler files in `harness/repl/stages/` (perception / planning / early_feedback / action / late_feedback) reflect this. Events emitted from `early_feedback.py` are **tagged `"planning"`** in the wire format for backward compatibility with trace consumers; the conceptual four-stage taxonomy in this section is unchanged. See ADR 0005.

### 2.1 Perception (感知)

What the harness reads to assemble situational awareness before LLM is called:

| Source | Content | Storage |
|---|---|---|
| JD input | raw text + metadata (company / role title / location / source URL) | `harness-tailor-input.schema.json` |
| Candidate state | long-term: `assets/profile/user-profile.md` + `experience-bank/index.json` v0.2.0+ + `experience-bank/raw/*.md` | Control plane (this repo) |
| Lens / scenario / market context | `assets/knowledge-base/references/role-lenses/`, `scenarios/`, `market-contexts/` | Control plane |
| Hard rules | `packages/strategy-modules/resume-rewrite-engine/SKILL.md` R-1 to R-8 + `quality-pass.md` | Control plane |
| Recent feedback | latest `feedback-ingestion` records relevant to (lens × industry) under question | Data plane (DB) |
| Prior tailoring trace | last `harness-tailor-output` for similar JD (deduplication / language reuse) | Data plane (DB) |

The Perception stage's output is a **fully assembled prompt** for the next Planning stage. It does NOT make decisions — it only gathers and structures.

### 2.2 Planning (规划)

Where the LLM (or a deterministic algorithm) makes decisions. Project-specific planning sub-stages:

| Sub-stage | Decision | Algorithm |
|---|---|---|
| Step 3 lens routing | Which `role_family` (A/B/C/D/HC) + scenario + market | keyword-scan → 5 lens score → highest match (deterministic; LLM as fallback for ambiguous JDs) |
| Step 3.5 capability extraction | Required competencies from JD (9-section structured output) | LLM via `role-competency-extractor` module |
| Step 4 Tier assignment | Tier 1 / 2 / 3 based on JD-master match score | deterministic 3-pass algorithm (R-8) |
| Step 4 经历筛选 | For each experience: 必上 / 上 / backup / 砍 | 3-pass + 4×3 matrix |
| Step 5 master selection | Which `resume-bank/versions/<lens>` master to派生 from | match primary lens → fall back to blended if multi-lens JD |
| Step 6 light injection plan | (Tier 1) Skills行 reorder + bullet 标签 rewrite + Summary rewrite + disambiguator add | LLM with strict prompt + master language preserved |
| Step 6 bullet rewrite plan | (Tier 2/3) per-bullet reframe, action / context / method / contribution / outcome / scale 6-元素 | LLM via `resume-rewrite-engine` module |

Planning output is **structured action list** — what to do in Action stage, not actually doing it yet.

### 2.3 Action (行动)

Execute the action list:

| Action | Tool / Service | Sandbox |
|---|---|---|
| Light injection | string transformations on .tex template | local process |
| Bullet rewrite (Tier 2/3) | LLM call with grounding constraint | policy gateway |
| LaTeX render | `xelatex` in Docker container | Level 2 container |
| Save artifact | filesystem write | local |
| DB persistence | Postgres / SQLite write | local |
| Submit to ATS | manual (user) / browser agent / email — never auto by harness | N/A — outside harness |

Every Action call passes through the **policy gateway** (R-1 to R-8 + PII filter + RBAC) before execution. See §6.

### 2.4 Feedback (反思)

Where the harness verifies action results and feeds back into next perception:

| Feedback type | Source | Effect |
|---|---|---|
| Pass 3 verifier verdict | Wave 2 Pass 3 agent | complete → emit .tex / partial → ask_user / failed → degrade |
| Schema validation result | every action emits structured output validated against schema | invalid → retry / fail → graceful degrade |
| User review at Inbox | Mode A drafted state → user reviews | accept → submit / edit → re-action / discard |
| Submission outcome | Gmail tracking (Wave 5) | application lifecycle update |
| Rejection / interview feedback | external email / user note | `feedback-ingestion.schema.json` → rubric update proposal (Wave 5) |
| Metrics events | every stage emits `metrics-event.schema.json` | aggregation → dashboard → drives Wave-N priority |

Feedback closes the loop. **Without explicit feedback assembly, the harness degenerates into one-shot prompt + hope.**

---

## 3. REPL container abstraction

The harness wraps each tailoring run as a **Read-Eval-Print-Loop** container:

```text
┌─────────────────────────────────────────────────────────┐
│  REPL CONTAINER (Wave 1+ implementation)               │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  READ    │───►│  EVAL    │───►│  PRINT   │          │
│  │ (token   │    │ (call    │    │ (feedback│          │
│  │ pipeline)│    │ intercept│    │ assembler│          │
│  │          │    │ + tool   │    │          │          │
│  │          │    │ router)  │    │          │          │
│  └──────────┘    └──────────┘    └──────────┘          │
│        ▲                              │                 │
│        └──────── LOOP ◄───────────────┘                 │
│  (until verdict ∈ {complete, partial+ask_user,          │
│   failed, budget_exhausted, degraded})                  │
└─────────────────────────────────────────────────────────┘
       ▲                                    │
       │                                    ▼
   Control plane                       Data plane
   (read-only)                         (read-write)
```

### 3.1 READ — Token transformation pipeline

The Read stage assembles each prompt according to deterministic rules — see §9 for the 5-stage pipeline. Output: a fully formed Claude API request payload. **Never raw concatenation of files**.

Key invariants:
- Token budget allocated per category (system prompt / hard rules / index.json slice / JD body / examples)
- Injection boundary: high-priority info (R-1 to R-8 + JD body) at start AND end of context (avoid Lost-in-the-Middle)
- Compression: rubric MD files are pre-summarized to JSON before injection (avoid feeding 6700 tokens of rubric prose into every call)

### 3.2 EVAL — Call interceptor + tool router

When LLM emits a tool/function call:

1. **Capture** — call interceptor extracts the JSON
2. **Schema-validate** — against the tool's input schema; on fail → retry or degrade
3. **Policy-check** — pass through policy gateway (§6)
4. **Route** — tool router dispatches to the appropriate executor (string transform, LaTeX render, DB query, etc.)
5. **Execute** — with timeout, retry, circuit breaker
6. **Capture output** — for PRINT stage

Each step has explicit failure path. See §11 for the full degradation table.

### 3.3 PRINT — Feedback assembler

The Print stage:
1. Receives raw tool execution result (success data or exception)
2. Wraps it as an "observation" — structured text the LLM can consume
3. Logs the round to audit trail (`harness-tailor-output.trace.{stage}_events`)
4. Emits a `metrics-event` per `metrics-event.schema.json`
5. Decides: continue loop (feed observation back to READ) or terminate

### 3.4 LOOP — Termination conditions

The loop continues until one of:

| Termination | Action |
|---|---|
| Verdict = `complete` (Pass 3 ✓ + .tex ready) | emit `harness-tailor-output` with `verdict=complete` |
| Verdict = `partial_pending_user` (Pass 3 has `[需人工]`) | emit output, freeze, surface to user via Inbox |
| Token / API / time budget exhausted | emit `verdict=degraded_to_manual` + checkpoint state |
| Schema validation failed N times | emit `verdict=failed` with full trace |
| User aborts (Mode B wizard) | emit `verdict=user_aborted` + save partial state |

**State persistence per termination type** is in §10 memory layering.

---

## 4. Bidirectional state mapping (Infinite ↔ Finite Token)

The world state is large:
- 6 raw experience files (~50K tokens total across raw/*.md)
- index.json v0.2.0 (~10K tokens with all 三轴 + disambiguator data)
- 5 lens files × 5K each = 25K
- 14 scenario files × 3K = 42K
- 3 market context files × 5K = 15K
- Hard rules R-1 to R-8 + workflow methodology = 20K
- Rubrics (recognition + vertical-fit) = 7K
- Recent feedback / trace from prior runs = variable

Total addressable: ~170K+ tokens. Single Claude call window: ~200K (with caching). One-shot dump impossible at 20-JD/天 (cost + latency).

**Solution: Reduction Rules.** Each tailoring stage gets a curated slice. The Token Pipeline (§9) is the implementation.

### Reduction priority for each call

When budget tight, sacrifice in this order (last to be cut = most important):

1. (Cut first) Generic examples / few-shot demonstrations
2. Cross-references (e.g., "see also scenarios/...")
3. Verbose rationale strings in scoring objects (keep score, drop rationale)
4. Inactive lens / scenario files (only load primary + secondary)
5. Inactive industry columns (only load target_industry + 1-2 secondary)
6. Inactive experience entries (only load Cat 1/2 candidates from Pass A)
7. (Never cut) Hard rules R-1 to R-8
8. (Never cut) JD body
9. (Never cut) Truthfulness rubric (truthfulness-checklist.json)

### Injection boundary

Per the Lost-in-the-Middle problem: place high-priority info at extremes:

```text
┌─ START ─────────────────────────────┐
│ system prompt (5K)                  │
│ hard rules R-1 to R-8 (2K)          │  ← bullet must NOT lie
│ truthfulness checklist (1K)         │
├─ MIDDLE ────────────────────────────┤
│ index.json relevant slice (4K)      │
│ scenario context (3K)               │
│ examples (2K)                       │
├─ END ───────────────────────────────┤
│ JD body (2K)                        │  ← what to tailor for
│ specific instruction (1K)           │  ← what to do
└─────────────────────────────────────┘
Total: ~20K context per Step 6 invocation (Tier 1)
```

For Tier 2/3 multi-bullet rewrite: ~40-50K (full experience raw file added).

---

## 5. Six design principles — current project compliance

| Principle | Definition | Project examples (✓ compliant) | Gaps (✗ / Partial) |
|---|---|---|---|
| **Design for Failure** | Every component has explicit fallback. Failures are the norm, not the exception. | • `evidence_strength: inferred unverified=true` flag — represents "we know this score is shaky"<br>• Pass 3 verdict enum has `partial_pending_user` — explicit graceful degrade<br>• `[请确认]` markers in bullet output | ✗ No retry budget per Claude call<br>✗ No timeout enforcement<br>✗ No circuit breaker on scraper |
| **Contract-First** | All interfaces machine-readable schemas, not prose docs. | • `index.json` schema 0.2.0 explicit<br>• `contracts/schemas/job-score.schema.json` exists<br>• `recognition-rubric.md` enums defined | ⚠ Hard rules R-1 to R-8 still prose-only — needs JSON encoding<br>⚠ Pass 3 input/output not schema-validated yet (ADR 0003 + Wave 0 schemas address this) |
| **Secure by Default** | Least privilege, zero trust, defense in depth. | • Repo private, `.env` gitignored<br>• No secrets in code<br>• `recognition-rubric.md` rule:"行业地位形容词必须有事实支撑" | ✗ No PII filter (resume contains personal info — leak risk in agent traces)<br>✗ No RBAC on submit action<br>✗ No injection defense on user-pasted JD content |
| **Decision vs Execution** | "What to do" (planning) decoupled from "how to do" (execution). | • Resume_Optimizer = decision rules<br>• JobOps + new runtime = execution<br>• Mode A drafted state separates plan from submit | ⚠ Currently no enforcement — all in Claude session, no plane boundary |
| **Everything is Measurable** | Every action emits metrics. | • `metadata.json` per resume captures routing decisions<br>• v0.3.2 米哈游 / Amazon trace记录了 user 干预次数 (7 / 0)<br>• VERSION_LOG records milestone-level decisions | ✗ No aggregate metrics dashboard<br>✗ No per-action latency / token / cost capture<br>✗ No automated Pass 3 通过率 trend |
| **Data-driven Evolution** | Feedback → updates rubrics / rules automatically. | • 京东 BA 反馈 → Ipsos consumer_research = high (manual update)<br>• v0.3.2 米哈游试跑 → R-7/R-8 rules added<br>• Anker 试跑 → R-7 round 3 修订 | ✗ Manual ingestion — no `feedback-ingestion` pipeline<br>✗ Rubric updates not version-tracked separately from code commits |

**Compliance summary at v0.3.3 entry:** 6/12 ✓, 4/12 ⚠, 8/12 ✗ across the 6 principles × 6 components evaluated above. Wave 0 closes most ✗ via schemas. Waves 1-5 close ⚠ via runtime implementation.

Detailed audit in `docs/architecture/HARNESS_COMPLIANCE_AUDIT.md`.

---

## 6. Control / Data / Harness 3-plane architecture

```text
┌───────────────────────────────────────────────────────────────┐
│ CONTROL PLANE — Resume_Optimizer (this repo, read-only at run)│
├───────────────────────────────────────────────────────────────┤
│ • Rules: SKILL.md + R-1 to R-8 hard rules                     │
│ • Rubrics: recognition / vertical-fit / quality-pass          │
│ • Knowledge: 5 lens / 14 scenarios / 3 market-contexts        │
│ • Profile: user-profile.md, experience-bank/raw/*.md          │
│ • Index: experience-bank/index.json v0.2.0+                   │
│ • Schemas: contracts/schemas/*.json                           │
│ • Resume bases: assets/resume-bank/versions/{A,B,C,D,HC}/     │
│ • Speedlearn whitelist                                        │
│ • Forbidden patterns / verb bank (planned JSONified)          │
└───────────────────────────┬───────────────────────────────────┘
                            │ read-only
                            ▼
┌───────────────────────────────────────────────────────────────┐
│ HARNESS LAYER — new (Wave 1+)                                 │
├───────────────────────────────────────────────────────────────┤
│ • REPL container (read → eval → print → loop)                 │
│ • Token transformation pipeline (5-stage)                     │
│ • Call interceptor + tool router                              │
│ • Policy gateway (R-1 to R-8 + PII + RBAC + rate limit)       │
│ • Feedback assembler                                          │
│ • Pass 3 verifier agent (Wave 2, LangGraph)                   │
│ • Metrics emitter                                             │
│ • Graceful degradation handlers                               │
│ • Sandbox executor (LaTeX render container, scraper container)│
│                                                               │
│ The ONLY component that calls Claude API.                     │
└───────────────────────────┬───────────────────────────────────┘
                            │ read-write
                            ▼
┌───────────────────────────────────────────────────────────────┐
│ DATA PLANE — JobOps + new runtime                             │
├───────────────────────────────────────────────────────────────┤
│ • Job database + lifecycle states                             │
│ • Generated artifacts (.tex / .pdf)                           │
│ • Review queue / Inbox (Mode A drafted)                       │
│ • Per-action audit logs (harness-tailor-output)               │
│ • Metrics events (metrics-event)                              │
│ • Feedback records (feedback-ingestion)                       │
│ • Postgres / SQLite                                           │
│ • Object storage (artifacts)                                  │
│ • Sandbox runtime (Docker containers)                         │
│ • Gmail tracking integration                                  │
└───────────────────────────────────────────────────────────────┘
```

**Plane boundaries enforced:**
- Control plane is mounted read-only at runtime. No mutation by Harness or Data plane.
- Harness reads control + reads/writes data; never mutates control.
- Data plane never makes decisions — it stores results.

---

## 7. Metrics taxonomy

Per ARCHITECTURE.md §15 + Anthropic harness essay §5.5. Four categories:

### 7.1 Task Effectiveness

| Metric | Capture point | Target |
|---|---|---|
| `task_success_rate` | drafted → submitted without override | ≥80% Tier 1 |
| `pass3_pass_rate` | Pass 3 first-attempt verdict = complete | ≥90% Tier 1 / ≥75% Tier 2/3 |
| `tier_assignment_accuracy` | post-hoc compared to user override | ≥85% |
| `master_selection_correctness` | post-hoc compared to user override | ≥90% |
| `tool_use_effectiveness` | tool calls that produced usable result / total | ≥85% |

### 7.2 Quality of Service

| Metric | Capture point | Target (Wave 5) |
|---|---|---|
| `end_to_end_latency_p50` / `p95` | JD ingest → drafted | p50 < 30s Tier 1 / p95 < 90s |
| `time_to_first_action` | request → first Claude call | p50 < 5s |
| `error_rate` | per stage (perception / planning / action / feedback) | <2% per stage |

### 7.3 Resource Efficiency

| Metric | Capture point | Target |
|---|---|---|
| `avg_token_consumption` | per Tier | Tier 1 < 8K / Tier 2 < 20K / Tier 3 < 50K |
| `avg_claude_api_calls` | per JD | Tier 1 ≤ 3 / Tier 2 ≤ 8 / Tier 3 ≤ 15 |
| `avg_cost_usd` | per JD | Tier 1 < $0.05 / Tier 2 < $0.15 / Tier 3 < $0.30 |
| `avg_tool_calls` | Pass 3 verifier internal | ≤ 5 per bullet |

### 7.4 Security & Compliance

| Metric | Capture point | Target |
|---|---|---|
| `policy_gateway_denial_rate` | denied / total action attempts | <5% (high = either rules too strict or LLM behaving badly) |
| `pii_leak_incidents` | PII detected in agent traces | 0 (zero tolerance) |
| `truthfulness_violations` | Pass 3 caught + post-feedback caught | <1/100 JD |
| `rate_limit_violations` | scraper / submit | <1/day |

Storage: SQLite traces table; aggregation via materialized views.
Schema: `contracts/schemas/metrics-event.schema.json`.

---

## 8. Sandbox isolation policy

Per HARNESS_DESIGN essay §5.4.1. Project tools mapped to isolation levels:

| Tool | Level | Justification |
|---|---|---|
| LaTeX render (`xelatex`) | **L2 — Container** (Docker) | Runs untrusted-ish content (user resume), needs filesystem isolation, but trusted binary |
| Scraper (国内招聘网站) | **L2 — Container** | Network-egress-only, rate-limited, no host filesystem access |
| Pass 3 verifier agent | **L1 — Process isolation** (initially) | Runs trusted code (our own); upgrade to L2 if it gains write access to disk |
| Browser agent (OpenClaw / Hermes) | **L2 — Container** with display forwarding | Runs untrusted browser sessions; isolate to prevent cookie / fingerprint cross-contamination |
| Submit action | **N/A — outside sandbox** | Manual paste = user's own browser; email = user's own client |
| Pass 3 LLM call (via Claude API) | **N/A — remote** | Anthropic-managed |

**No L3 / L4 (microVM / full VM) needed at current scale.** Containers + read-only root filesystem + seccomp-bpf for scraper sufficient.

---

## 9. Token transformation pipeline (5 stages)

Per HARNESS_DESIGN essay §5.2.2. Implementation in Wave 1 `packages/harness/token-pipeline/`:

```text
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: 信息源收集 (Source aggregation)                     │
│  - JD text                                                  │
│  - target_industry + target_lens (from input)               │
│  - relevant index.json slice (only target columns + AI)     │
│  - relevant raw experience files (only those Cat 1-3 from   │
│    Pass A)                                                  │
│  - relevant scenario / role-lens / market-context files     │
│  - hard rules R-1 to R-8                                    │
│  - rubrics (truthfulness-checklist + lens-routing)          │
│  - recent feedback for (lens × industry)                    │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: 相关性排序 (Relevance ranking)                      │
│  - Each source scored on (semantic similarity to JD,        │
│    recency, evidence_strength)                              │
│  - Output: ordered list of (content, weight) pairs          │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: 压缩与摘要 (Compression / summarization)            │
│  - rubric MD files → pre-built JSON summary                 │
│  - long raw experience files → only relevant project        │
│    sections (per Pass A tier filtering)                     │
│  - rationale strings >50 chars → first sentence only        │
│  - Verbose explanations → checklist form                    │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 4: 预算分配 (Budget allocation)                        │
│  - Per category: system_prompt / hard_rules / candidate_ctx │
│    / jd_body / examples / instruction                       │
│  - Tier 1: 8K total budget; Tier 2: 20K; Tier 3: 50K        │
│  - If over budget: drop lowest-priority sources first       │
└────────────────────┬────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 5: 模板组装 (Template assembly)                        │
│  - Slot content into a structured prompt template with      │
│    explicit section markers ([HARD_RULES], [JD_BODY],       │
│    [INDEX_SLICE], [INSTRUCTION], etc.)                      │
│  - Inject high-priority at start AND end (Lost-in-the-Middle│
│    mitigation)                                              │
│  - Output: Claude API request payload                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Memory layering

Three layers, each with explicit storage and retention:

| Layer | Holds | Retention | Storage | Read access | Write access |
|---|---|---|---|---|---|
| **Working memory** | per-call observation buffer (within one REPL loop iteration) | seconds — until termination | in-process RAM | Harness REPL | Harness REPL |
| **Short-term memory** | per-tailoring-run state (1 run = many loop iterations) | minutes — until run termination | in-process or Redis | Harness REPL | Harness REPL |
| **Long-term memory** | cross-run state (投递记录, scoring cache, Pass 3 trace history, feedback records, rubric versions) | indefinite | Postgres / SQLite + filesystem (artifacts) | Harness READ + user UI | Harness PRINT (post-run) + user explicit edits |

**State separation principle (critical):** the LLM is a stateless compute unit. All cross-call state lives in long-term memory, not in conversation history. This enables:
- Resumable runs (kill the harness mid-run, restart from checkpoint)
- Reproducibility (same input + same control plane state → same output, modulo LLM stochasticity)
- Auditability (long-term memory IS the audit trail)

Anti-pattern: trying to make Claude "remember" across calls via verbose conversation history. This conflates state with reasoning context and breaks at scale.

---

## 11. Failure modes & graceful degradation

Per Anthropic harness essay §5.4.2. Eight project-relevant failure modes:

| Failure mode | Detection | Degradation path |
|---|---|---|
| **Pass 3 verifier crashes** (Wave 2+) | Process exit code ≠ 0 OR schema validation fails | Mark all bullets `[低置信度需人工]`, emit `verdict=partial_pending_user`, freeze for user review |
| **Claude API timeout / rate limit** | HTTP 429 / 5xx after retry budget | Fall back to most recent successful master version, no light injection; emit `verdict=degraded_to_manual` |
| **Token budget exceeded** | pre-call budget check | Drop lowest-priority context (per §4 reduction rules), retry; if still over → `verdict=degraded_to_manual` |
| **Schema validation fails 3x** | output schema check | Emit `verdict=failed` with full conversation trace for offline debugging |
| **Disambiguator absent for low-recognition exp** | Step 4 Pass B lookup → null | Continue without disambiguator; surface warning in trace; do NOT fabricate disambiguator text |
| **Master file missing for selected lens** | Step 5 file check | Fall back to next-best lens master + log `master_fallback` event; if no fallback → `verdict=failed` |
| **LaTeX render fails** | xelatex non-zero exit | Emit `.tex` to user with render error; user falls back to Overleaf manually; `verdict=partial` |
| **Scraper blocked / 403** (Wave 3+) | HTTP 403 / 429 | Move that source to backoff queue; continue with other scrapers; alert if all blocked |
| **PII detected in JD or output** | policy gateway pre-flight | Block action; emit `policy_denial` metric; ask user to redact |

**Common pattern:** every failure path emits a metric event + audit log entry + actionable user message. No silent failures.

---

## 12. Cross-references

- `docs/architecture/ARCHITECTURE.md` — system-level architecture (this doc is the engineering layer detail)
- `docs/decisions/0003-harness-as-architectural-foundation.md` — ADR recording adoption + sunset criteria
- `docs/architecture/HARNESS_COMPLIANCE_AUDIT.md` — 13 components × 6 principles audit
- `contracts/schemas/harness-tailor-input.schema.json` — REPL input contract
- `contracts/schemas/harness-tailor-output.schema.json` — REPL output contract
- `contracts/schemas/pass3-verifier-io.schema.json` — Pass 3 agent I/O
- `contracts/schemas/policy-gateway-decision.schema.json` — gate decision record
- `contracts/schemas/metrics-event.schema.json` — observability event
- `contracts/schemas/feedback-ingestion.schema.json` — feedback → rubric pipeline
- `packages/strategy-modules/resume-rewrite-engine/SKILL.md` — Hard rules R-1 to R-8 (policy gateway constraints)
- `docs/plans/archive/2026-05-04-harness-foundation.md` — Wave 0 implementation plan (this doc is part of)
- `docs/plans/archive/2026-04-27-agentify-with-harness.md` — superseded by Wave 0 + Wave 2

---

## Appendix A: Strategic positioning matrix

Per Anthropic essay §3. Two-axis maturity model:

```text
                  Cognitive Loop
              React            Proactive
              ────             ─────────
   高效 (沙盒+全自动注入)
        │      第二象限          第一象限
        │     (我们要去的地方,   (理想终态:
Context  │      Wave 5+)         Mode A 跑通 +
Efficiency      高效被动:       feedback loop)
        │     scraper+Inbox+    自动 search +
        │     auto Tier 1       自动调整规则
        ─────┼───────────────┼─────────────
   低效 (人工/单点投喂)
        │      第三象限          第四象限
        │    (当前位置)        (Wave 1-2 后)
        │     低效被动:         主动但低效:
        │   Claude session     Pass 3 verifier
        │   手动 trigger        + Mode B PoC
        │     React             有 reflect 但
                                ctx 仍人工注入
```

**Current position: 第三象限 (低效被动)**.
**Wave 1-2 target: 第四象限 (主动但仍部分人工)**.
**Wave 5 target: 第二/一象限 (高效+主动)** — 20-JD/天 stable 投递达成。

Maturity advancement = Harness component coverage advancement.

---

## Appendix B: Glossary

- **PPAF**: Perception / Planning / Action / Feedback — the 4 stages of one Agent loop iteration
- **REPL container**: Read / Eval / Print / Loop — the harness's wrapper around LLM
- **Control plane**: read-only rules / contracts / rubrics living in this repo
- **Data plane**: read-write runtime state living in JobOps + DB
- **Harness layer**: the new code (Wave 1+) that wraps LLM, calls control, writes data
- **Tier 1/2/3**: tailoring depth — light (Skills+labels+Summary) / medium (1-2 bullet body changes) / heavy (multi-bullet rewrite)
- **3-pass selection**: Step 4 Pass A base → Pass B disambiguator booster → Pass C JD AI hard 筛 (R-8)
- **Disambiguator**: parenthetical text after company name校正招聘方 brand认知 (R-7)
- **Lens**: A 战略研究 / B 数据分析 / C 产品运营 / D 金融市场 / HC 人力资本 (5 base resume versions)
- **Sprint contract**: input/output schema agreed before agent starts; agent output must validate or run rejected (Pass 3, Step 4 capability matcher)
- **Sunset criteria**: each harness component has explicit retire-when conditions (per ADR 0003)

---

End of HARNESS_DESIGN.md v0.3.3.
