---
name: resume-rewrite-engine
description: |
  Consume the role-competency-extractor output and the candidate's experience
  bank, select the best canonical resume version, and produce a structured
  10-section rewrite plan (sections A-J per `output-schema.md`) that JobOps
  review queue persists. The LaTeX renderer is downstream of this product, not
  this module's responsibility. Truthfulness rules from root `SKILL.md` apply.
---

# Resume Rewrite Engine

Strategy module for the v0.3.x scoring + v0.4.x tailoring MVPs. Consumes the
competency model, audits the candidate against it, decides experience priority,
defines narrative, drafts rewrite content, and emits a structured product the
JobOps review queue can hold for human approval before LaTeX rendering.

This module **does not** rerun JD analysis. It assumes the
`role-competency-extractor` has already emitted its 9-section output (per
`packages/strategy-modules/role-competency-extractor/output-schema.md`).

## Inputs (canonical)

- Role competency profile from `role-competency-extractor` (9 sections + flat-field summary)
- Job score (when available) conforming to `contracts/schemas/job-score.schema.json`
- `target_market` (passes through from upstream; default `north-america`)
- Candidate strategy assets (read-only, ground truth):
  - `assets/profile/user-profile.md`
  - `assets/experience-bank/index.json`
  - `assets/experience-bank/raw/*.md`
  - `assets/resume-bank/versions/*/metadata.json`
  - canonical resume source files under `assets/resume-bank/versions/`
  - `assets/knowledge-base/references/general-rules.md`
  - `assets/knowledge-base/references/workflow/rewrite-methodology.md`
  - `assets/knowledge-base/references/workflow/keyword-extraction.md`
  - `assets/knowledge-base/references/workflow/quality-pass.md`
  - `assets/knowledge-base/references/workflow/gap-bridging.md`
  - `assets/knowledge-base/references/role-lenses/<X>-*.md` (matching primary lens)
  - `assets/knowledge-base/references/scenarios/<single-owner>.md`
  - `assets/knowledge-base/references/market-contexts/<target_market>.md`
  - `assets/knowledge-base/references/company-contexts/<context>.md` (if applicable)

## Output

Structured 10-section product per `output-schema.md` (Sections A-J). Persisted
by JobOps to the review queue. **The LaTeX renderer reads this product as input
and is not part of this module.** Section I (Final Resume Draft) is the
text-form rewrite that the renderer transforms.

## Workflow

### Step 1 — Load upstream + lens

1. Confirm the role-competency-extractor 9-section output is present. If
   missing → request the user run that module first, OR infer a lightweight
   competency model with a confidence caveat.
2. Resolve `primary_lens` from the upstream flat-field summary; load matching
   `role-lenses/<X>-*.md` and the single-owner `scenarios/<name>.md`.
3. If `secondary_lens` is set: load secondary lens file; apply blended-lens
   directive per `workflow/competency-framework.md §2.2` (primary drives
   narrative + structure + front-half; secondary woven into supporting bullets
   + skills section).

### Step 2 — Candidate audit (6-dimension)

Apply `workflow/rewrite-methodology.md §1`:
1. Direct Fit
2. Transferable Fit
3. Low-Signal Content
4. Distracting Content
5. Proof Strength (Strong / Moderate / Weak)
6. Gaps

Audit each entry in `assets/experience-bank/index.json` against the upstream
competency model's Section B (Core Hiring Logic) and Section C (Tier 1/2/3
qualifications).

### Step 3 — Narrative construction

Apply `workflow/rewrite-methodology.md §2`:
- Determine the single narrative
- Connect narrative to upstream Section B core hiring logic
- Define the anti-narrative (what the resume must NOT accidentally read like)
- Match narrative to lens-specific exemplar (lens file §2 + bullet pattern)

### Step 4 — Prioritization (3-pass selection + 4×3 decision matrix)

Apply `workflow/rewrite-methodology.md §3` + `assets/experience-bank/index.json` v0.2.0+ double-axis scoring. Score判准 references:
- `assets/knowledge-base/references/recognition-rubric.md` — recognition_per_industry score 定义 + disambiguator 来源
- `assets/knowledge-base/references/vertical-fit-rubric.md` — vertical_fit_per_lens + ai_digital_fluency score 定义

**Required fields per experience (read from index.json):**
- `recognition_per_industry[target_industry].score` ∈ {high, medium, low, null}
- `vertical_fit_per_lens[target_lens].score` ∈ {core, adjacent, weak, missing}
- `ai_digital_fluency.score` ∈ {strong, moderate, weak, none}
- `disambiguator_per_industry[target_industry]` (may be null; see Hard rule R-7)
- `evidence_strength` on any of the above (`direct_bullet | direct_capability_tag | inferred`)

**3-pass selection algorithm:**

**Pass A — Base 筛选**
Use `base_recognition = recognition_per_industry[target_industry].score`.
Look up 4×3 decision matrix to assign initial tier:

|                       | fit=core    | fit=adjacent | fit=weak    |
|---                    |---          |---           |---          |
| **rec=high**          | 必上展开    | 上展开       | 单 bullet   |
| **rec=medium**        | 上展开      | 单 bullet    | backup 行   |
| **rec=medium-low**    | 单 bullet   | backup 行    | 砍          |
| **rec=low / null**    | backup 行   | 砍           | 砍          |

`fit=missing` → 砍 (regardless of recognition).

**Pass B — Disambiguator booster**
For experiences landed in `砍` or `backup 行` tier with non-null `disambiguator_per_industry[target_industry]`, recompute `effective_recognition`:

| Disambiguator type      | Lift on base_recognition           | Ceiling      |
|---                      |---                                  |---           |
| `mis_classification`    | low → medium, medium → high        | high         |
| `pure_recognition`      | low → medium-low (or medium if 信号强) | medium     |
| null                    | 0                                   | —            |

Re-look up matrix with `effective_recognition`. If new tier is higher, **promote**. Pass A 已上车的 (必上 / 上展开 / 单 bullet) 不动 — booster 只解救底部经历。

**Disambiguator may NOT promote any experience to "必上展开"** — that tier requires `base_recognition ≥ medium`.

**Pass C — JD-specific hard 筛 (subtraction only, never adds)**

Trigger AI hard 筛 if JD contains any of:
`AIGC | 生成式 AI | Agent | LangGraph | Prompt Engineering | RAG | NLP | 标签体系 | LLM | Generative AI | AI 创新`.

When triggered, apply per-experience downgrade:
- `ai_digital_fluency = strong` → no change
- `ai_digital_fluency = moderate` → no change
- `ai_digital_fluency = weak` → 下压 1 档 (必上展开→上展开 / 上展开→单 bullet / 单 bullet→backup 行 / backup 行→砍)
- `ai_digital_fluency = none` → 下压 2 档

Other hard 筛 (industry-specific blacklist / lens missing override) per `workflow/jd-analysis.md`.

**Final 4-category mapping:**
- Tier `必上展开` → Cat 1 (Must Lead and Expand, 4-6 bullets)
- Tier `上展开` → Cat 1 or Cat 2 (4 bullets if budget allows, else 2-3)
- Tier `单 bullet` → Cat 2 (Keep but Compress, 2-3 bullets)
- Tier `backup 行` → Cat 3 (Retain as Supporting Signal, 1 line / skills section)
- Tier `砍` → Cat 4 (Downgrade or Remove)

**`evidence_strength` low-confidence flag:** For any cell where `evidence_strength = inferred AND unverified = true`, append `[低置信度]` flag in Section C reasoning. Do NOT auto-promote experiences whose tier-affecting score is unverified inference; require user confirmation before promotion above `单 bullet`.

**Reasoning trace (mandatory)**: every Pass A → Pass B → Pass C transition + final tier per experience recorded in output Section C with format:
`<exp_id>: PassA=<tier>(rec=<X>, fit=<Y>) → PassB=<tier>(disambig:<type>) → PassC=<tier>(AI:<level>) → final=<Cat>`

### Step 5 — Resume version selection

From upstream `resume_version_hints`, select `matched_resume_version`:
- Primary lens drives the choice
- If candidate strongest evidence does not match primary lens (rare), document
  the rationale for the override in `scoring_notes` and downgrade overall fit
- Read `assets/resume-bank/versions/<version>/metadata.json` for protected
  sections and version-specific rules

### Step 6 — Bullet rewrite

Apply `general-rules.md` §"Bullet 六元素解构" (Action / Context / Method /
Contribution / Outcome / Scale). Per category:
- Cat 1: 4-6 bullets, 1.5-2.5 lines, 4-5 elements per bullet
- Cat 2: 2-3 bullets, 1-2 lines, 3-4 elements per bullet
- Cat 3: 1 bullet / 1 line / minimum elements

Lens-specific verb patterns from `role-lenses/<X>-*.md` §4 Language Signals.
Market-specific tone / quantification from `market-contexts/<target_market>.md`.

### Step 7 — ATS keyword integration

Apply `workflow/rewrite-methodology.md §4` + `workflow/keyword-extraction.md §4`
placement strategy. Insert Tier 1 / 2 / 3 keywords per the placement table.
Apply Credibility Test (`keyword-extraction.md §7`) to every inserted keyword.

### Step 8 — Quality Pass

Apply `workflow/quality-pass.md` Pass 1 → Pass 1.5 (中文 only) → Pass 2 → Pass 3.
**Truthfulness rules from root `SKILL.md` are enforced here.** Pass 3 outputs
must explicitly cite source for every new claim, or mark `[请确认]`.

### Step 9 — Market localization

Apply `market-contexts/<target_market>.md` resume-side rules:
- Length budget
- Section ordering
- Photo / personal info handling
- Bullet density
- Proof hierarchy (NA: Impact → Method → Scope; HK: Scope → Credentials → Impact;
  内地: Pedigree → Scope → Relevance → Impact)
- Bilingual handling if applicable

### Step 10 — Emit structured output

Format per `output-schema.md` (Sections A-J). Section I is the text-form
final draft; the LaTeX renderer is downstream and consumes Section I.

## Hard rules

**Truthfulness 护栏**: inherits root `SKILL.md` §细则 真实性细则 (R-1..R-6, 红线 1, highest priority). Do not restate; read root SKILL.md for the canonical list. Pass 3 of `workflow/quality-pass.md` is the enforcement point.

**Module-specific:**
1. **Single resume version selected** — no multi-version output
2. **Section J (Risk Flags) is mandatory** — at least the unsolvable-by-rewrite gaps
3. **Lens / scenario / market contexts read-only** — do not mutate ground-truth files
4. **LaTeX rendering is downstream** — Section I is text; do not embed LaTeX commands except where the user's resume template requires them in Section I
5. **For HC lens hard-sell (Mercer / Desay SV)** — apply `packages/strategy-modules/resume-rewrite-engine/README.md` strategic positioning rules
6. **Tier-1 light tailoring** (per `docs/architecture/ARCHITECTURE.md §9`): only headline / summary / skills section may change; no work-experience bullet edits in Section I. Tier-2 deep tailoring permits bullet edits but every claim grounded.

7. **Brand-Recognition Disambiguator (R-7)** — When `recognition_per_industry[target_industry].score ∈ {low, medium}` AND the experience is retained on resume **as Cat 1 / Cat 2 (展开 with bullets)**, prepend a parenthetical disambiguator to the company name. Two types:
   - **Mis-classification 校正** (公司有多业务线 / 招聘方可能误判): e.g., `Ipsos` → `Ipsos Strategy3（益普索旗下战略咨询）`
   - **Recognition 锚定** (招聘方不识别公司): e.g., `Desay SV` → `德赛西威（头部汽车电子上市公司）`

   **Application scope (重要)**:
   - **Cat 1 / Cat 2 (展开 with bullets)** → 加 disambiguator (招聘方 5-10 秒精读 header，括号信息会被读到)
   - **Cat 3 (其他实习经历 backup line)** → **不加** (招聘方 1-2 秒扫过 backup line 时括号通常被略过；多公司一行加括号反而视觉拥挤 + 字符预算紧 + 读者无暇消化)
   - **Cat 4 (砍)** → 不适用

   **Truthfulness constraints (inherits root SKILL.md R-1)**:
   - 等级形容词 (头部 / 顶级 / 龙头) require factual support (上市状态 / 行业排名 / revenue scale) — no self-anointment
   - Business-line classification must match candidate's actual team / role per `experience-bank/raw/*.md`
   - 历史 anchor (前 X 合资 / 原 X 子公司) require fact-grounded (公开公司史可验证) AND temporal proximity to candidate's tenure (合资退出 > 10 年的前合资关系 anchor 力减弱，谨慎使用)

   **Space economy**: When disambiguator > 12 字 in Cat 1/2 header line, weigh against keyword density displacement.

   **Lens-specific**: Same company may need different disambiguator across industries. Read `disambiguator_per_industry[target_industry]` field; do not propagate one disambiguator across lenses. `null` value = no disambiguator needed for this industry.

8. **Disambiguator-aware Selection (R-8)** — Step 4 selection MUST run the 3-pass algorithm (Pass A base → Pass B disambiguator booster → Pass C hard 筛). Disambiguator lift is capped: `mis_classification` grants +1 level (low→medium, medium→high), `pure_recognition` grants +0.5~1 level (low→medium-low, ceiling = medium). Disambiguator may not promote any experience to the `必上展开` tier — that tier requires `base_recognition ≥ medium`.
