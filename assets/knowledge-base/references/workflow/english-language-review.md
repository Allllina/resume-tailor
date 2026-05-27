# Pass 1.6 — English Language Review（英文简历专项审查）

> 与 `quality-pass.md` Pass 1.5（中文可读性检查）对称的 Pass，**仅英文简历执行**。
> 目的：让简历在 native English / 国际化招聘语境下读起来自然、专业、不像直译。
> 触发：当 resume 输出语言 = `en` 或 `bilingual` 时，对所有 EN bullet 执行此 Pass。

---

## 0. 执行时机

`quality-pass-runner` 调用顺序：

```
Pass 1（关键词注入）
  → Pass 1.5（中文可读性，仅中文简历）
  → Pass 1.6（英文语言审查，仅英文 / 双语简历）
  → Pass 2（AI 味清洗）
  → Pass 3（真实性 source-grounding）
```

Pass 1.6 与 Pass 1.5 互斥：单语简历只跑对应一边；双语简历两边都跑（英文页跑 1.6，中文页跑 1.5）。

---

## 1. 检查维度（5 类）

每条 EN bullet 对照以下 5 类规则逐项 sweep：

### 1.1 Brand-name → generic noun（叙述里换成通用词）

**规则：** Skills / Tools section 保留品牌名（ATS 关键词）；**bullet 叙述里换成 generic**（更显国际化、更专业）。

| 中文/品牌（出现在叙述时）| Skills 行（保留）| Bullet 叙述（改 generic） |
|---|---|---|
| Excel | Excel | spreadsheet / model |
| PowerPoint | PowerPoint | deck / slides / presentation |
| Word | Word | document |
| Photoshop | Photoshop | image-editing software |
| Slack / 飞书 / 钉钉 | Slack | messaging tool / chat |
| Zoom / 腾讯会议 | Zoom | video call / video conference |
| Tableau / Power BI | Tableau / Power BI | dashboard / BI tool |
| Google Docs | Google Docs | document |
| WeChat | WeChat | messaging tool（如非品牌强调）|

**典型违规：** `maintained the master Excel model` → 修复为 `maintained the master spreadsheet model` 或 `maintained the consolidated master model`（直接 drop brand）。

### 1.2 直译腔（literal-translation smell）

中文短语直译进英文，读起来不顺。常见 pattern：

| 中文直译（错）| 英文 native（对）|
|---|---|
| make use of X | use X |
| in order to X | to X |
| based on the analysis of X | analyzing X / based on X |
| have the ability to X | can X / am able to X |
| play an important role in X | shaped X / drove X |
| put forward suggestions | proposed / recommended |
| do research on X | researched X |
| make a decision | decided |
| provide help / give support | helped / supported |
| achieve the goal of X | reached X / hit X |
| with the help of X | using X / with X |
| to a large extent | largely |
| at the same time | concurrently / in parallel |
| it is worth mentioning that | notably / of note, |
| has a positive impact on X | improved X / lifted X |

**Sweep 规则：** 全文 grep 这些短语，命中即标黄；判断是不是真的需要重写。

### 1.3 AI-flavor English（与 quality-pass.md Pass 2 对齐 + 扩充）

LLM 高频英文词在 native 商业写作里属于 cliché：

| AI 高频词 | Native 替换 | 何时可保留 |
|---|---|---|
| Spearheaded | Led / Drove / Owned | 创立角色才用 |
| Leveraged | Used / Applied / Drew on | 简历不是商业计划书 |
| Synergized | Collaborated / Coordinated | 永不保留 |
| Orchestrated | Managed / Coordinated | 真管多团队才用 |
| Pioneered | Introduced / Launched | 第一个做才用 |
| Cutting-edge | Advanced / Modern / Latest | — |
| Streamlined | Simplified / Improved / Reduced | JD 用了可保留 |
| Revolutionized | Improved / Transformed | 永不保留 |
| Robust | Strong / Reliable / Stable | — |
| Comprehensive | Full / Complete / End-to-end | — |
| Actionable insights | Findings / Recommendations | — |
| Drive impact | Improved / Lifted / Contributed to | — |
| Cross-functional synergies | Cross-team collaboration | — |
| Strategic initiatives | Projects / Programs | 战略级才用 |
| Stakeholder alignment | Coordination with [具体角色] | — |
| Holistic | End-to-end / Full-scope | 哲学课才用 |
| Empowered / Enable | Helped / Allowed | — |
| Facilitated | Helped / Enabled / Hosted | — |
| Optimized（无具体指标）| Improved by N% / Reduced by N% | 必须有数字才保留 |
| Architected（非软件）| Designed / Structured | 软件架构师才用 |
| Curated | Selected / Compiled | 博物馆 / 编辑才用 |
| Bespoke | Custom / Tailored | 永不在简历用 |

**关键判断规则：** AI 高频词 **出现在 JD 原文中** → 保留不替换（命中关键词比避 AI 味更重要）。

### 1.4 Verb diversity（动词重复检查）

**规则：** 同一动词在整份简历最多出现 2 次。常被滥用的开头动词：

`Owned / Led / Designed / Built / Developed / Engineered / Drove / Synthesized / Contributed / Supported / Created / Implemented / Managed`

**检查方式：** 自动 count 每个 bullet 开头动词的出现频次，超过 2 次报警。

**替换库**（按 ownership 强度排序）：

| Ownership 强度 | EN 动词候选 |
|---|---|
| 主导 / sole owner | Owned / Led / Drove / Spearheaded* / Headed |
| 重点负责 / co-owner | Co-led / Drove / Anchored / Headed |
| 独立交付一段 | Independently led / Single-handedly delivered / Authored |
| 显著贡献 | Shaped / Informed / Co-developed / Co-built |
| 参与 | Contributed to / Supported / Worked with / Joined |
| 数据/分析动作 | Analyzed / Synthesized / Triangulated / Modeled / Quantified / Diagnosed / Assessed |
| 设计/构建 | Designed / Built / Engineered / Architected* / Structured / Crafted |
| 推动/落地 | Drove / Pushed / Implemented / Rolled out / Operationalized |
| 沟通/协作 | Aligned / Coordinated / Briefed / Presented / Negotiated |

*带星号的（Spearheaded / Architected）有 AI 味嫌疑，谨慎使用。

### 1.5 翻译精度（CN→EN 术语 grounded 在 translation-glossary.md）

**规则：** 凡涉及中文经历的英文翻译，必须 cite `translation-glossary.md` 中的 canonical 翻译；如术语不在表中，先入表再用。

**典型错配（如出现自动 flag）：**

| 中文 | 错译（常见 LLM 直觉） | Canonical |
|---|---|---|
| 组织架构 | talent framework / organizational chart | **organizational structure / org architecture** |
| 任职资格体系 | rank system / job grade system | **qualification framework / competency-and-qualification framework** |
| 编制配置 | headcount only / staffing only | **headcount-and-allocation analysis / staffing structure** |
| 指标体系 | indicator system / KPI list | **metric system / performance metric architecture** |
| 数字化转型 | digitalization transformation（重复）| **digital transformation** |
| 战略复盘 | strategy retrospective（弱）| **strategy review / post-mortem strategic review** |
| 即时零售 | real-time retail（错误）| **instant retail / quick commerce / q-commerce** |
| 钱效模型 | money-efficiency model（直译丑）| **unit economics / contribution-margin model** |
| 抓手 | grip handle / lever（字面）| **lever / entry point / starting point** |
| 落地 | land on the ground（字面）| **implemented / executed / rolled out** |
| 闭环 | closed loop（字面）| **end-to-end / fully integrated** |
| 业务方 | business side（字面）| **business stakeholders / business team** |
| 主导 | spearheaded（默认）| **led / owned / drove**（依 ownership 程度）|

完整表见 `translation-glossary.md`。

---

## 2. 执行流程（每条 EN bullet 跑一遍）

```
For each bullet B in resume.en:
    Step 1: brand_name_audit(B)  → flag any brand name in narrative not in Skills line
    Step 2: literal_translation_audit(B)  → grep §1.2 patterns
    Step 3: ai_flavor_audit(B)  → grep §1.3 patterns × not in JD
    Step 4: verb_diversity_audit(B)  → count opening verbs against §1.4 limit
    Step 5: translation_glossary_audit(B)  → if bullet sources from CN experience-bank,
                                              verify each EN term against glossary
Output:
    flagged_bullets[]: list of (bullet, issue_type, suggested_fix)
    if any: chat-style review with user before applying
```

---

## 3. 输出格式

```
[Pass 1.6 EN Review Report]

Total EN bullets: 11
Flagged: 2

#1 Ipsos bullet 1
  Issue: §1.1 brand-name in narrative
  Original: "...maintained the master Excel model."
  Suggested: "...maintained the consolidated master model."
  Severity: Low

#2 Mercer bullet 1 (label)
  Issue: §1.5 translation precision
  Original label: "Talent Framework Design" (for 任职资格体系)
  Note: per glossary, 任职资格 → "Qualification Framework" or "Competency-and-Qualification Framework"
        "Talent Framework" is broader (= 人才框架). Either works for 任职资格 if
        framing as HR talent-development; flag for user choice.
  Severity: Medium

Total Pass 1.6 status: 2 issues require user review.
```

---

## 4. 与其他 Pass 的耦合

- **Pass 1（关键词注入）后** → Pass 1.6 检查注入的关键词不引入直译腔
- **Pass 2（AI 味清洗）前** → Pass 1.6 已先做一轮 AI flavor sweep；Pass 2 是 backup + 中文 AI 味
- **Pass 3（真实性）独立** → Pass 1.6 不验证事实，只验证语言

---

## 5. Failure modes（典型违规，源自 2026-05-10 IBM 试跑）

| 违规类型 | 例子 | 修复 |
|---|---|---|
| Brand 漏过 | `maintained the master Excel model` | drop Excel → `consolidated master model` |
| 任职资格直译 → talent | `Talent Framework` 用作"组织架构"标签 | 拆开：组织架构 = Org Restructuring；任职资格 = Qualification Framework |
| 编制配置半翻 | `synthesized headcount and responsibility-overlap` | 完整化：`headcount-and-allocation and responsibility-overlap` |
| 动词超限 | `Owned` 出现 3 次 | 一处改 `Led` 或 `Drove` |
| 直译"contribute to"过用 | `contributed to consolidation plan / framework / module` | 改 `informed` / `shaped` / `co-developed` |

---

## 6. 当 EN review 与中文原意冲突时

**规则：原意优先于流畅度**。如果 EN native 表达会损失中文原文的精度（量化范围、所有权强度、行业术语），保留略生硬的精确表达。例：

- `synthesized 200+ employee and 10 executive interviews` —— 不要为流畅改成 `synthesized stakeholder interviews`，会丢"200+/10"分层信息
- `9 clinical subtypes` —— 不要为流畅改成 `multiple clinical subtypes`，会丢具体性

精确度排在 native 流畅度之上。

---

## 7. 维护

- 每跑完一份英文简历，将新发现的违规模式 append 到 §1 对应分类
- 每跑完一份英文简历，将新出现的 CN→EN 术语 append 到 `translation-glossary.md`
- 每季度归档一次违规高频统计，反向修订 `translation-glossary.md` 的优先级
