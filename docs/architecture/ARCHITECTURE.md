# Resume Operations Agent Architecture

> Updated: 2026-04-26  
> Status: foundation / pre-MVP  
> Decision: operations system first, agent second.

## 1. Product goal

Build a job-search operations system that can discover jobs, filter them, score fit, match the right resume version, produce low-risk tailoring suggestions, and track application outcomes.

The system should not behave like an unconstrained autonomous agent. Job search has reputation risk, so the architecture must prioritize traceability, state management, evidence grounding, and human review.

## 2. Core architecture decision

Three planes (per Harness Engineering — see `HARNESS_DESIGN.md`):

```text
CONTROL PLANE (this repo, Resume_Optimizer; read-only at runtime)
  Rules / contracts / rubrics / canonical knowledge
  - candidate profile (assets/profile/user-profile.md)
  - verified experience bank (assets/experience-bank/raw/*.md
    + index.json v0.2.0+)
  - resume base versions A/B/C/D/HC (assets/resume-bank/versions/)
  - 5 lens definitions (assets/knowledge-base/references/role-lenses/)
  - JD-analysis methodology + scenarios + market-contexts
  - recognition / vertical-fit / AI-fluency rubrics
  - hard rules R-1 to R-8 (resume-rewrite-engine/SKILL.md)
  - search keywords, blacklist, speedlearn whitelist
  - JSON schemas (contracts/schemas/)

DATA PLANE (JobOps + new runtime, to be deployed)
  Runtime instances + state + sandboxed execution
  - job discovery (scrapers in containers)
  - dedup + lifecycle states + pipeline runs
  - generated artifacts (.tex / .pdf)
  - review queue (Inbox UI, Mode A vs Mode B)
  - Gmail tracking
  - persistent state (Postgres / SQLite)
  - per-action audit logs (harness-tailor-output)
  - metrics events (metrics-event)

HARNESS LAYER (new code, Wave 1+)
  Engineering machinery wrapping LLM
  - REPL container (Read → Eval → Print → Loop)
  - Token transformation pipeline (5 stages, per HARNESS_DESIGN §9)
  - Call interceptor + tool router
  - Feedback assembler
  - Policy gateway (R-1 to R-8 enforcement, PII filter, RBAC)
  - Pass 3 verifier agent (Wave 2, LangGraph)
  - Metrics emitter
  - Graceful degradation handlers
```

The Harness Layer reads contracts from Control Plane and writes runtime state to Data Plane. **It is the only component that calls LLM APIs.** Control / Data plane separation is enforced — Harness never mutates Control plane (rule changes go through PR review); Data plane never makes decisions (it stores results).

## 2a. Sub-skill orchestration layer (added 2026-05-09 per ADR 0006)

Within the Control Plane, the resume-optimization methodology is
decomposed into **5 sub-skill packages** under
`packages/strategy-modules/`. The root `SKILL.md` (~120 lines) is a
thin orchestrator that dispatches to these 5 packages following Mode L
(lightweight, single-user) or Mode F (full, with review queue) execution
profile.

```text
packages/strategy-modules/
├── role-competency-extractor/      Step 3.5 — 9-section competency profile
├── fit-diagnosis-engine/           Step 4 (pre_rewrite) + Step 8 (post_rewrite)
├── gap-bridging-planner/           Step 5 + Step 7-1/7-2 (forward-looking advisory)
├── resume-rewrite-engine/          Step 6 + Step 8.5 (10-section A-J rewrite)
└── quality-pass-runner/            Step 6.5 (Pass 1 + 1.5 + 2 + 3 pipeline)
```

Coupling graph (data flow):

```text
fit-diagnosis-engine (pre_rewrite)
   ↓ Section 4-A matrix
   ↓ Section 4-C boundary
gap-bridging-planner
   ↓ Section 5a directives + 5c skill plan
resume-rewrite-engine
   ↓ rewritten_resume
quality-pass-runner
   ↓ final_resume_text
   ├→ latex-renderer (Mode L 终点)
   └→ fit-diagnosis-engine (post_rewrite, Mode F only)
       ↓ Section 8 review + radar
       review queue / Inbox UI
```

Each sub-skill has its own `SKILL.md` (10-step workflow),
`output-schema.md` (machine-readable contract), and `README.md`. The
schemas are stable across harness implementation; harness Python in
`packages/harness/` consumes them directly.

Mode L vs Mode F dispatch table is in root `SKILL.md`. Mode L skips
`fit-diagnosis-engine` `post_rewrite` mode + history recording + radar
chart rendering; Mode F runs everything. Mode upgrade from L → F
requires explicit user opt-in (R-17, no implicit promotion) to prevent
the compliance-drift class of incident documented in `docs/INCIDENTS.md`.

Step 7 (Supplementary recommendations) is dissolved: 7-1 (structural
ordering) and 7-2 (skill bar) live in `gap-bridging-planner`; 7-3
(targeted advice) and 7-4 (multi-JD coverage) live in
`fit-diagnosis-engine`.

See ADR 0006 (`docs/decisions/0006-skill-superpowers-refactor.md`) for
the full decomposition rationale, mismatch audit against existing
harness/forecast and harness/review backends, and Mode L/F dispatch
table.

## 3. Framework choice

> **Update 2026-05-08 (per `STATUS.md` deployment-model decision):**
> JobOps fork as a separate ops hub is **dropped**. The project is now
> self-hosted single-user — the harness backend (`packages/harness/`,
> FastAPI) and Inbox UI (same repo) ARE the runtime, and
> `ops/jobops/` is preserved as a reference snapshot, not a deployment
> dependency.

Currently in use:
- Harness backend (`packages/harness/`) as the operations runtime + LLM caller.
- LangGraph for Pass 3 truthfulness verifier (Wave 4 D.4) and planned for additional multi-agent stages.
- Pydantic + JSON Schema for contract validation across the 5 sub-skill packages.

Originally recommended (kept for reference):
- ~~JobOps fork/adaptation as the operations hub.~~ Dropped 2026-05-08.
- LangGraph, or a lightweight custom state graph first, for AI workflow orchestration. ✅ in use.
- LlamaIndex/RAG later for evidence retrieval over the experience bank.

Not recommended as the primary architecture:
- AutoGPT: too autonomous and hard to audit for job applications.
- AutoGen: useful for experiments, but the core product is a stateful pipeline rather than agents chatting.
- CrewAI: role-playing agents are less important than deterministic state transitions and evidence traceability.
- Full LangChain agent stack: useful components can be used, but avoid opaque agent/tool spaghetti.
- Semantic Kernel: no strong advantage unless the project becomes Azure/.NET-heavy.

## 4. Current repository role

This repository is the strategy layer, not the full operations app.

It should remain the ground truth for:
- `assets/profile/user-profile.md`
- `assets/experience-bank/raw/*.md`
- `assets/experience-bank/index.json`
- `assets/resume-bank/versions/*/metadata.json`
- `assets/knowledge-base/references/*`
- resume-tailoring methodology and quality rules

JobOps should read this repo as a versioned input. It should store cache/index snapshots, generated artifacts, and application status, but should not become the source-of-truth editor for personal experience at first.

## 5. Target workflow (PPAF cycle)

The pipeline is a PPAF (Perception / Planning / Action / Feedback) loop; each stage has explicit failure modes and degradation paths (see `HARNESS_DESIGN.md` §11).

```text
PERCEPTION
  - Discover jobs (scraper / paste / URL)
  - Dedupe + hard filter (visa / blacklist)
  - JD structured extraction (sections + keywords + lens hints)
  - Capability matching against assets/experience-bank/index.json

PLANNING
  - 3-pass selection (Pass A base → Pass B disambiguator booster
    → Pass C JD AI hard 筛, per R-8)
  - Tier assignment (1 / 2 / 3) based on JD-master match score
  - Resume version selection (A/B/C/D/HC master)
  - Light injection plan (Tier 1) or full rewrite plan (Tier 2/3)

ACTION
  - Tier 1: Skills reorder + bullet 标签 rewrite + Summary writer
    + disambiguator inject (per R-7)
  - Tier 2/3: Step 6 bullet rewrite + Step 7 ATS keyword integration
    + Step 6.5 Pass 1/2 polish
  - Step 9 LaTeX render (in container sandbox)
  - Drop into Inbox (drafted state)

FEEDBACK
  - Step 6.5 Pass 3 truthfulness verification (Wave 2 verifier agent)
  - User review at Inbox (5-10s scan / detailed override)
  - Submission via chosen channel (manual / browser agent / email
    — see §14)
  - Gmail tracking → application lifecycle update
  - Rejection / interview feedback → rubric update proposal
    (Wave 5, per feedback-ingestion.schema.json)
```

The loop continues until: Pass 3 verdict = `complete` + user submits, OR user discards, OR budget (Token / time / API) exhausted → graceful degrade to manual mode.

**Mode A (auto pipeline)** runs full PPAF unattended for Tier 1 candidates, holds Tier 2/3 for manual review.

**Mode B (manual customize)** walks user through each PPAF stage with override at every decision point.

## 6. Job lifecycle states

Keep lifecycle simple and operational:

```text
discovered
filtered
scored
ready_for_review
tailored
ready_to_apply
applied
oa
interview
rejected
offer
archived
```

Strategy-specific fields should be separate from lifecycle status:
- `tier`
- `matchedResumeVersion`
- `resumeMatchScore`
- `scoreDimensions`
- `visaRisk`
- `recommendedAction`
- `reviewStatus`

## 7. Scoring rubrics (two orthogonal axes)

The system runs two independent scoring rubrics:
- §7a JD-side: "Is this JD worth pursuing? Which Tier?"
- §7b Resume-side: "Which master + which experiences + how to tailor?"

Both feed into Step 4 selection (see `HARNESS_DESIGN.md` §3 Planning stage).

### 7a. JD-side scoring (decides 投 / 不投 + Tier)

Total score: 100.

| Dimension | Weight |
|---|---:|
| Skill match | 20 |
| Experience relevance | 20 |
| Industry fit | 15 |
| Level match | 15 |
| Location preference | 10 |
| Growth potential / company value | 10 |
| ATS pass likelihood | 10 |

Tier routing:
- Tier 1: total >= 90 AND resume match >= 85. Light tailoring.
- Tier 2: total 70-89 OR resume match 70-84. Deep review draft.
- Tier 3: total < 70 OR hard filter blocked. Archive or trend analysis.

(`resume_match_score` is computed per §7b; this is the bridging variable.)

### 7b. Resume-side scoring (decides which master + light injection content)

Per `assets/experience-bank/index.json` v0.2.0+:

- `recognition_per_industry[target_industry]` ∈ {high, medium, low, null}
  Brand recognition × 招聘方所在行业, 8 industry columns.
  Score判准 in `assets/knowledge-base/references/recognition-rubric.md`.

- `vertical_fit_per_lens[target_lens]` ∈ {core, adjacent, weak, missing}
  Content × lens 5 维 ability fit, 5 lens columns.
  Score判准 in `assets/knowledge-base/references/vertical-fit-rubric.md`.

- `ai_digital_fluency` ∈ {strong, moderate, weak, none}
  Cross-cutting layer (NOT a 6th lens). Triggers AI hard 筛 when JD contains AIGC / 生成式 AI / Agent / Prompt / RAG / NLP keywords.

- `disambiguator_per_industry[target_industry]` (optional)
  Brand 校正 (`mis_classification`) or recognition 锚定 (`pure_recognition`). Lift ceiling: mis_classification +1 level (low→medium / medium→high); pure_recognition +0.5~1 level (low→medium-low, ceiling = medium). Applied only in Cat 1/2 main bullets, **NOT** Cat 3 backup line.

The 3-pass selection algorithm (Pass A base → Pass B disambiguator booster → Pass C JD AI hard 筛) is enforced in `packages/strategy-modules/resume-rewrite-engine/SKILL.md` Hard rule R-8.

`resume_match_score` (used in §7a Tier routing) computed as:

```
resume_match_score =
  weighted_sum_of_per_experience_tier_after_pass_C
  / total_experience_count_in_resume

where each Cat 1 = 100, Cat 2 = 75, Cat 3 = 40, Cat 4 = 0.
```

Threshold mapping: ≥85 → Tier 1 light tailoring sufficient; 70-84 → Tier 2 review; <70 → Tier 3 heavy or archive.

## 8. Visa/work authorization rules

Generic wording such as "must be authorized to work in the U.S." or "eligible to work in the U.S." is neutral. It should not be treated as a visa penalty because F-1 work authorization can satisfy this language.

Explicit sponsorship availability is positive.

Explicit no-sponsorship, U.S. citizen only, permanent resident only, or security-clearance language is a hard skip unless manually overridden.

## 9. Resume tailoring policy (3 tiers)

Per Tier 1 dominant assumption (~85% of投递 should fit Tier 1):

### Tier 1 — Light tailoring (default, ~85% case)

May change ONLY:
- headline
- summary
- skills / keyword synonyms
- bullet 标签 (粗体开头总结词)
- 公司名 disambiguator (per R-7, see below)

May NOT change work-experience bullet body. Master version's verified language is preserved.

### Tier 2 — Medium tailoring (~10% case)

May change Tier 1 surface + 经历选取改 (砍 / 加 1-2 段) + 1-2 个 bullet body 微调. Every claim must be grounded in `assets/experience-bank/raw/*.md` and pass truthfulness verification before use.

### Tier 3 — Heavy tailoring (~5% case, dream / cross-lens / blended)

May change Tier 2 surface + multi-bullet rewrite + 重跑 Step 4 selection + 完整 Pass 3. Reserved for high-priority targets where standard masters don't fit.

### Hard rule references (in `packages/strategy-modules/resume-rewrite-engine/SKILL.md`)

- **R-1 to R-6**: truthfulness 护栏 (inherited from root SKILL.md)
- **R-7 Brand-Recognition Disambiguator**: parenthetical 校正 / 锚定 in Cat 1/2 main bullets, **NOT** in Cat 3 backup line. Two types: `mis_classification` (e.g., Ipsos→Ipsos Strategy3) and `pure_recognition` (e.g., Desay SV→头部汽车电子上市公司).
- **R-8 Disambiguator-aware Selection**: Step 4 must run 3-pass algorithm (Pass A base → Pass B booster → Pass C JD AI hard 筛). Disambiguator cannot promote to "必上展开" tier (requires base_recognition ≥ medium).

Pass 3 truthfulness verification (Wave 2 agent) is the enforcement point.

## 10. RAG policy

MVP does not need heavy RAG.

MVP retrieval should use:
- `assets/experience-bank/index.json`
- structured tags
- keyword/BM25 matching
- role-family matching
- LLM reranking over selected evidence

Later RAG can add:
- LlamaIndex
- pgvector or sqlite-vec
- hybrid retrieval: structured filters + keyword search + embedding similarity + reranking

RAG should be used for evidence retrieval, not for inventing new resume claims.

## 11. Interaction channels

Primary:
- JobOps Web UI
- Email/Gmail reports and tracking

Optional:
- WhatsApp short alerts

Not default:
- Telegram command workflow

## 12. Build order (Wave-based, current as of v0.3.3)

### Done (v0.0.x — v0.3.3)

- v0.0.x: legacy skill methodology
- v0.1.x: foundation structure + GitHub layout
- v0.2.x: JobOps fork imported (read-only snapshot at `ops/jobops/`)
- v0.3.0: skill methodology integration + 5 lens / 14 scenarios / 3 market contexts
- v0.3.2: business-loop rules + Amazon BA second e2e test
- v0.3.3: Harness foundation (this wave) — `HARNESS_DESIGN.md` + ARCHITECTURE patches + 6 contract schemas + ADR 0002 + R-7/R-8 hard rules + `index.json` v0.2.0 (recognition + vertical_fit + AI fluency + disambiguator axes)

### In flight (Wave 0 second half — compliance audit)

- `HARNESS_COMPLIANCE_AUDIT.md`: 13 existing components × 6 design principles, identifying retrofit gaps for Wave 1+

### Planned (Wave 1+, sequenced per Harness foundation)

- **Wave 1 — REPL skeleton + Tier 1 PoC** (1 week, TS or Python TBD)
- **Wave 2 — Pass 3 缩水版 verifier** (LangGraph, 1 week)
- **Wave 3 — Inbox + scraper (国内 5 站) + Mode A pipeline** (1-2 weeks)
- **Wave 4 — Tier 2/3 fallback + 完整 Pass 3** (1 week)
- **Wave 5 — Metrics + feedback loop + Gmail integration** (1-2 weeks)

Total runway to "20 JD/天 stable" target: 6-9 weeks from v0.3.3.

### v0.4.x agentify plan (2026-04-27) — superseded under Harness

Original plan listed 4 agents (Pass 3 / Step 4 / Step 3.5 / Step 5). Under Tier 1 dominant assumption, only Pass 3 verifier remains high-priority; Step 4 / 3.5 / 5 agentify deferred until Tier 2/3 volume materializes. See `docs/plans/archive/2026-05-04-harness-foundation.md`.

## 13. Historical docs

The previous architecture draft is archived at `docs/archive/ARCHITECTURE_legacy_2026-04-25.md`.

## 14. Submit channel architecture (3 channels)

The system itself does not auto-apply. Submit method is per-application user choice with risk-per-channel disclosure:

### Channel A — Manual paste (default)

User opens 招聘 portal in own browser, pastes .tex / .pdf, types message.
- Risk: minimal
- Time: 3-5 min/application
- Recommended for 国内招聘 (Boss / 拉勾 / 牛客 / 阿里招聘 / 字节招聘) where ATS bot detection is light but behavioral consistency matters.

### Channel B — Browser agent (OpenClaw / Hermes / Anthropic Computer Use)

Agent in own browser instance simulates click + type.
- Solves: ATS bot fingerprint detection (real browser + real input cadence)
- Does NOT solve: cross-company de-dup, 招聘方端 reading detection, email pattern detection
- Risk: medium (rate-based outlier signals more visible at agent speed)
- Time: 1-2 min/application
- Recommended only for 海外 ATS-heavy forms (Workday, Greenhouse, Lever) where form filling time dominates.

### Channel C — Email direct

Send .pdf + cover letter to 招聘邮箱 directly. Bypasses ATS entirely.
- Risk: minimal
- Time: 2-3 min/application
- Recommended when 招聘邮箱已知 or 内推 channel exists. Highest signal-to-noise ratio.

Channel selection is recorded in lifecycle state alongside `applied`:
`submitted_via_manual` | `submitted_via_agent` | `submitted_via_email`.

## 15. Metrics taxonomy (per HARNESS_DESIGN.md §7)

Four metric categories captured per pipeline run:

### Task Effectiveness

- `task_success_rate` — drafted → submitted without manual override (target ≥80% Tier 1)
- `pass3_pass_rate` — Pass 3 verdict = complete on first try (target ≥90% Tier 1 / ≥75% Tier 2/3)
- `tier_assignment_accuracy` — post-hoc compared to user override (target ≥85%)
- `master_selection_correctness` — post-hoc compared to user override (target ≥90%)

### Quality of Service

- `end_to_end_latency_p50` / `p95` (JD ingestion → drafted in Inbox; target p50 < 30s Tier 1)
- `time_to_first_action_p50` / `p95` (target p50 < 5s)
- `error_rate` per stage (perception / planning / action / feedback; target <2% per stage)

### Resource Efficiency

- `avg_token_consumption` per Tier (Tier 1 < 8K, Tier 2 < 20K, Tier 3 < 50K)
- `avg_claude_api_calls` per JD (Tier 1 ≤3, Tier 2 ≤8, Tier 3 ≤15)
- `avg_cost_usd` per JD (Tier 1 < $0.05, Tier 2 < $0.15, Tier 3 < $0.30)
- `avg_tool_calls` (Pass 3 verifier internal; ≤5 per bullet)

### Security & Compliance

- `policy_gateway_denial_rate` (R-1 to R-8 enforcement; target <5%)
- `pii_leak_incidents` (resume content leaving sandbox; target 0)
- `truthfulness_violations` (Pass 3 caught vs missed, post-user-feedback; target <1/100 JD)

Storage: SQLite traces table (per `HARNESS_DESIGN.md` §6 Data Plane).
Schema: `contracts/schemas/metrics-event.schema.json`.

## 16. Diagrams

Visual representations of the system architecture:

- [Handshake Layers](diagrams/handshake-layers.svg) — The 5-layer model and status of component boundaries.
- [PPAF Orchestration Cycle](diagrams/ppaf-cycle.svg) — The 5-stage variant of the Perception-Planning-Action-Feedback loop.
- [Strategy Module Map](diagrams/module-map.svg) — Mapping of strategy modules to their harness implementation.
