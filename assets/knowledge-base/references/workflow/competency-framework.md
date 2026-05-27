# Competency Framework — JD 拆解与能力提取方法论

供 `packages/strategy-modules/role-competency-extractor/` 模块调用。配套使用：`workflow/jd-analysis.md`（JD 五层拆解结构）、`workflow/keyword-extraction.md`（关键词架构）、`role-lenses/`（5 个上位族判定）。

---

## 1. Role Family Validation（角色族验证）

在分析多 JD 之前，先判定它们是否属于同一角色族。相似 title 不等于同一族。

**验证维度：**

1. **核心业务功能** — 服务的业务功能是否一致（都是 revenue ops / product analytics / strategic planning 等）。client-facing 咨询和 internal ops 即使 title 相似也是不同族。
2. **决策权与 scope** — 50 人创业公司向 CEO 汇报的 "Strategy Analyst" ≠ Big 4 advisory 的 "Strategy Analyst"。
3. **主要交付物类型** — 客户 deck vs SQL dashboard，title 同名也属不同族。
4. **团队归属** — Marketing analytics / finance analytics / product analytics 工具栈重合，但服务对象与判断框架完全不同。

**Seniority detection：**
JDs 跨多个层级时（Analyst / Senior / Lead），记录差距，分层观察：
- ownership scope（task-level → workstream-level → function-level）
- stakeholder seniority（peers → managers → executives）
- decision authority（execute → recommend → decide）
- mentorship 期望（none → informal → formal）
- strategic vs executional 比例

**输出：** 2-3 句结论，是否同族 + seniority 跨度。不同族就 stop 并解释。

---

## 2. Lens 判定（5 上位族归位）

完成 role family validation 后，判定该 JD 应路由到哪个 lens：

| Lens | 文件 | 触发信号 |
|---|---|---|
| A 战略研究 | `role-lenses/A-strategy-research.md` | consulting / strategy / advisory / 战略 / 研究 / 政策 |
| B 数据分析 | `role-lenses/B-data-analytics.md` | data analyst / business analyst / 数据分析 / 用户洞察 / 舆情 |
| C 产品运营 | `role-lenses/C-product-ops.md` | product ops / growth / customer success / 产品运营 / 数据运营 / AI 产品 |
| D 金融市场 | `role-lenses/D-finance-markets.md` | equity research / IBD / 二级 / 投研 / 市场分析 |
| HC 人力资本 | `role-lenses/HC-human-capital.md` | people analytics / HR analytics / org effectiveness / 人力资本 |

### 2.1 Scenario 单归属规则（MECE 铁律）

每个 scenario 文件**只属于一个 lens**。混合 / 边界岗位的分流逻辑**不写在 lens 或 scenario 文件里**，而是写到运行时 `scoring_notes` 输出字段。

例如：JD 是"data-driven growth strategy" → 加载 Lens A 的 `growth-strategy.md`（A 是单一 owner），但在 `scoring_notes` 里记录 "secondary lens: B（30%）" 让 scoring/rewrite 阶段叠加 B 的语言信号。

最终归属（共 15 个 scenario：v0.3.0 的 14 = 现有 12 + HC 新建 2，外加 v0.6.x 新增 `ai-engineering`，归 Lens C）：

| Lens | 单归属 scenarios |
|---|---|
| A 战略研究 | `consulting` / `business-analysis` / `growth-strategy` / `product-strategy` |
| B 数据分析 | `data-analysis` / `user-insights` / `public-opinion` |
| C 产品运营 | `product-ops` / `data-ops` / `customer-success` / `ai-innovation` / `ai-engineering` |
| D 金融市场 | `financial-markets` |
| HC 人力资本 | `human-capital` / `people-analytics` |

### 2.2 Blended Lens（≥60% / <40%）

混合岗位识别 primary 与 secondary 后：

1. 识别 primary lens（≥60% 需求映射）
2. 识别 secondary lens（剩余）
3. **整体叙事 / 结构 / 前半段强调用 primary lens**
4. **secondary lens 信号 weave 进 supporting bullets 和 skills section**
5. 在 `scoring_notes` 与 output Section E 标注 blend 比例

---

## 3. Responsibility Clustering（职责聚类）

跨所有 JDs 提取重复职责，聚成 4-7 个 workstream。

**方法：**
1. 列出所有 distinct 职责
2. 归一化语言（"drive cross-functional alignment" 与 "coordinate across teams" 是同一个）
3. 按业务结果（不是动作描述）聚类成 workstream
4. 按出现频率与位置（前 3 条权重高）排序

**职责重要性信号：**

| 信号 | 权重 | 原因 |
|---|---|---|
| 出现在 80%+ JDs | 极高 | 跨公司共识 |
| 列在前 3 条 | 高 | 雇主前置优先级 |
| 绑定可量化结果 | 高 | 责任明确 |
| 强动词（own / lead / drive） | 中高 | primary ownership |
| 仅 1 个 JD 出现 | 低 | 公司特异，非族级 |
| 被动框架（support / assist / contribute） | 低 | secondary |
| 在 "nice to have" / "bonus" 之后 | 极低 | 显性降权 |

**Workstream vs Task：** workstream 是 "stakeholder management & cross-functional alignment"，task 是 "schedule weekly syncs with the product team"。聚到 workstream 层。

---

## 4. Capability Extraction（能力五维提取）

把每个 workstream 翻译成执行所需能力，分五维。

### 4.1 Cognitive / Problem-Solving
- 结构化问题拆解
- ambiguity 容忍 + 假设构建
- 跨数据 / 定性输入的 pattern recognition
- first-principles vs framework application
- 多源信息综合成 coherent view

### 4.2 Business / Functional
- 行业 / 板块知识
- business model / revenue driver / cost structure 的理解
- 职能专业（marketing / finance / operations / etc.）
- 市场 awareness 与竞争语境
- 监管 / 合规知识（如适用）

### 4.3 Execution
- 项目管理与优先级
- 流程设计与改进
- 时间压力下的速度与质量
- 自主执行（最少监督）
- attention to detail 与产出 polish

### 4.4 Stakeholder / Collaboration
- upward communication（向高层汇报）
- lateral coordination（跨团队）
- 客户 / 用户互动
- influence without authority
- 书面 vs 口头侧重

### 4.5 Technical / Tool
- 软件平台（具名工具）
- 方法论与框架
- 编程 / 分析语言
- 数据素养（consumer → analyst → builder）
- 技术深度 vs 广度

**每条能力标注：**
- 映射到哪个 workstream
- 显性要求 or 由职责隐含
- 出现在多少个 JDs（recurrence score）

---

## 5. Priority Ranking（优先级三档）

### Tier 1: Must-Have
- 出现在 70%+ JDs
- 列在 "required" / "minimum qualifications"
- 非协商语言（"must have" / "required" / "X+ years"）
- 直接对应核心 workstream
- 缺这一条 → 无法执行 primary function

### Tier 2: Strongly Preferred
- 出现在 40-70% JDs
- 列在 "preferred" 或职责中提及但不在 requirements
- preference 语言（"preferred" / "ideally" / "experience with X is a plus"）
- 对应 secondary workstream，或在 primary workstream 上提升表现
- 没这一条仍能干，但竞争力下降

### Tier 3: Nice-to-Have
- 出现在 <40% JDs
- 列在 "bonus"，或一笔带过
- 弱语言（"familiarity with" / "exposure to" / "interest in"）
- 对应 aspirational 成长方向 / 团队特定加分项
- 不影响核心职责

**警惕装饰性要求：**
- "Passion for [industry/mission]" — 几乎不筛
- "Thrives in a fast-paced environment" — 套话
- "Strong attention to detail" — 太通用，除非绑定具体 deliverable（如 financial modeling 准确性）
- 长串 "nice to have" 工具 — 没有候选人能全部具备

---

## 6. Hidden Screening Logic（隐性筛选逻辑）

雇主很少写出全部筛选标准。从信号反推未明说的过滤器。

**推断方法：**

1. **职责 scope 推 experience 下限** — 角色 own P&L / budgets / executive presentations，则真实 experience 下限高于 stated。
2. **团队功能推 culture fit** — 咨询公司的 strategy team 筛 structured thinking + polish；初创的 growth team 筛 speed + scrappiness。
3. **汇报线推 communication 期望** — 直接向 C-suite 汇报 → 信息综合与高密度产出能力。
4. **行业语境推 domain depth** — 银行 internal strategy team 的 "financial services experience" 是 deep 的，不是 surface。
5. **未明说的 credential 偏好** — 学校 / 雇主 / 证书偏好往往不写在 JD 但实际在筛。
6. **协作 pattern 推 personality** — 大量 cross-functional 语言 → 筛 proactive / diplomatic / organized 的人。
7. **conspicuously absent** — data 角色完全不提 statistical rigor / experimentation → 团队偏 descriptive analytics 而非 causal inference。

**每个推断标注：**
- 哪个信号支持
- 为什么影响筛选
- 简历中什么证据能满足

---

## 7. Visa / Work Authorization（与 ARCHITECTURE.md §8 + `contracts/schemas/job-score.schema.json` 一致）

输出字段 `visa_risk` 取值（5 值，与 schema 一致）：

| 值 | 触发条件 |
|---|---|
| `clear` | JD 显性说明对该候选人无 visa 限制（含已确认本人 status 满足） |
| `generic_authorized_neutral` | "authorized to work in the U.S." / "eligible to work in the U.S." 等 generic 语言（F-1 OPT 满足） |
| `sponsor_positive` | 显性 sponsorship available / "we sponsor work visas" |
| `blocked` | 显性 no-sponsorship / U.S. citizen only / permanent resident only / security clearance |
| `unknown` | JD 完全未提及 work authorization |

`blocked` → hard skip（除非手动覆盖）。`generic_authorized_neutral` 与 `unknown` 都允许进入打分流程。

---

## 8. 与目标市场（target_market）的耦合

每次提取必须接收 `target_market` 输入（默认 `north-america`）。下列维度受市场影响：

- **Tier 1/2/3 边界** — 内地市场学校/雇主 brand 是硬筛信号，NA 偏向能力证据
- **隐性筛选** — 内地："985/211 优先"几乎不会写但常见；HK：双语+证书；NA：clearance/citizen
- **关键词形态** — 同一能力在不同市场用不同词

详见 `market-contexts/{north-america, hong-kong, mainland-china}.md`。

---

## 9. 输出契约

提取结果按 `packages/strategy-modules/role-competency-extractor/output-schema.md` 的 9 段结构输出，再由 JobOps scoring layer 与 resume-rewrite-engine 消费。

关键输出字段（与 ARCHITECTURE.md §6 / `contracts/schemas/job-score.schema.json` 对齐）：

- `role_family`: `A_strategy_research` | `B_data_analytics` | `C_product_ops` | `D_finance_markets` | `HC_human_capital` | `other`
- `competency_tags`
- `evidence_requirements`
- `visa_risk`: `clear` | `generic_authorized_neutral` | `sponsor_positive` | `blocked` | `unknown`
- `resume_version_hints`: 从 `{A, B, C, D, HC}` 中选择（与 `assets/resume-bank/versions/*/metadata.json` id 一致）
- `scoring_notes`: 包含 secondary lens 标注（如适用）、blend 比例、边界 scenario 路由解释
- `confidence`: `high` | `moderate` | `low`
