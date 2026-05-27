# Keyword Extraction — ATS / AI 关键词架构

供 `quality-pass.md` Pass 1 与 `packages/strategy-modules/role-competency-extractor/` 模块调用。本文件定义关键词的提取、分级与放置策略。

---

## 1. 什么算关键词

关键词 = ATS / AI 筛选工具 / 招聘人员可能用作匹配标准的任何 term / phrase / 公式化表达。包括名词、动词、短语、复合词。

**不算关键词：**
- 通用企业语言（team player / self-starter / passionate）
- 填充形容词（strong / excellent / proven），除非与具体技能搭配
- 公司特异 jargon（候选人简历不会出现的）
- 福利 / perks / 公司介绍语言

---

## 2. 提取四步法

### Pass 1: Explicit
直接从 JD 文本中拉出所有具名 skill / tool / methodology / qualification / capability。

### Pass 2: Implicit
识别由职责隐含但未具名的能力。例如 "present findings to senior leadership" 隐含：executive communication / stakeholder presentation / data storytelling / insight synthesis。

### Pass 3: Semantic Expansion
为每个关键词生成 2-3 个语义等价词，覆盖 ATS / AI 的语义匹配。
- "Cross-functional collaboration" → cross-team coordination / interdepartmental partnership / matrixed environment
- "Data-driven decision making" → evidence-based strategy / analytical decision support / metrics-informed recommendations

### Pass 4: Frequency × Placement Scoring

**频率分**（出现在多少 JDs）：
- 80%+ → Critical（必须出现在简历）
- 50-79% → Important（应该出现）
- 25-49% → Useful（有空间就放）
- <25% → Optional（公司特异，仅针对该雇主时放）

**位置权重**（在 JD 中的位置）：
- Job title → 最高
- 前 3 条职责 → 高
- Required qualifications → 高
- 中段职责 → 中
- Preferred qualifications → 中
- Nice-to-have / bonus → 低

**综合优先级 = 频率 × 位置权重**

---

## 3. 关键词分级（5 Tier）

### Tier 1: Core Role Keywords
定义角色本身。应出现在 headline / summary / job title。

**识别：** 出现在 JD title / 第一句 / 重复 3+ 次。通常是 role name 与 functional descriptor。

按 5 lens 举例：
- A 战略研究: strategy / management consulting / strategic advisory / 战略研究 / 政策研究
- B 数据分析: data analysis / business intelligence / analytics / reporting / 数据分析 / 用户洞察
- C 产品运营: product management / product operations / growth / 产品运营 / 增长策略
- D 金融市场: equity research / securities analysis / investment research / 投研 / 金融分析
- HC 人力资本: people analytics / HR analytics / org effectiveness / 人力资本

### Tier 2: Capability Keywords
描述这个人做什么。属于经历 bullet。

**识别：** 绑定具体职责或要求的 term，多为名词短语 / 动名词短语。

举例：stakeholder management / financial modeling / market research / process optimization / competitive analysis / user research / A/B testing / forecasting

### Tier 3: Tools / Methods / Frameworks
具名技术与方法论。属于 skills section + 自然 woven 进经历描述。

**识别：** 专有名词 / 缩写 / 具名方法论。

举例：SQL / Python / Tableau / Power BI / Salesforce / Agile / Six Sigma / DCF / SWOT / OKRs / Google Analytics / Snowflake / dbt

### Tier 4: Action Verbs
高信号动词，传达 ownership / leadership / impact。开 bullet 用。

| Ownership 等级 | 动词 |
|---|---|
| Full ownership | Led / owned / built / designed / launched / established / created |
| Strategic influence | Drove / shaped / defined / developed / spearheaded / championed |
| Analytical contribution | Analyzed / identified / evaluated / assessed / synthesized / modeled |
| Execution | Implemented / executed / delivered / managed / coordinated / optimized |
| Collaboration | Partnered / collaborated / aligned / facilitated / influenced |

**避免弱动词：** assisted / helped / supported / participated / contributed（除非搭配 strong context）。

> 中文等价见 `general-rules.md` 动词表（领导力 / 分析力 / 执行力 / 创新力 / 沟通力）。

### Tier 5: Semantic Equivalents
扩大 ATS 语义匹配覆盖，不引起冗余。

**为什么重要：** 现代 ATS / AI 用语义匹配，不只是 exact match。自然变体提高命中。但 keyword stuffing / 不自然重复会伤可读性，可能触发 spam filter。

**规则：**
- 每个变体能在自然句子中使用
- 把变体分散到不同 bullets，不要堆在一起
- 最常用形态作 primary，变体作 secondary

---

## 4. 简历放置策略

| 简历区块 | 优先放置 Tier | 密度建议 |
|---|---|---|
| Headline / Title | Tier 1 only | 1-2 个核心词 |
| Summary（3-4 行） | Tier 1 + 高优 Tier 2 | 4-6 词，自然 woven |
| Experience bullets | Tier 2 + 3 + 4 | 每条 2-3 词，verb + capability + tool 模式 |
| Skills section | Tier 3 为主 | 完整但诚实清单 |
| Education / Certs | Tier 3 如适用 | 仅核实过的 credentials |

### Verb-Capability-Tool 模式
最强的 bullets 遵循：

**[Action verb]** + **[capability / what you did]** + **[tool / method]** + **[measurable result]**

示例：
> **Led** competitive market analysis **using** SQL-based data extraction and Tableau dashboards, identifying 3 underserved segments that informed a $2M product expansion strategy.

这一条自然包含：led（Tier 4）/ competitive market analysis（Tier 2）/ SQL（Tier 3）/ Tableau（Tier 3）/ product expansion（Tier 2）。

---

## 5. 与 quality-pass.md 的耦合

`quality-pass.md` 的 Pass 1（关键词 Gap 注入）流程：

1. 由本文件方法论从 JD 拆解输出**关键词清单**（按 Tier 分组，标注高优）
2. 用 word-boundary 精确匹配扫描简历全文
3. 输出命中表（关键词 / 是否命中 / 出现位置）
4. 未命中但用户具备 → 在最相关 bullet 或 Skills 栏注入
5. 未命中且用户不具备 → 标记为不可弥补 gap，**不注入**

---

## 6. Red Flags（红线）

- **Keyword stuffing：** 列了技能但经历 bullet 没体现
- **Invisible keyword block：** 白字或隐藏区块（可能触发 ATS 拒收）
- **Seniority 错配：** 角色期望 led / owned，简历写 assisted / supported
- **工具罗列无 context：** "Proficient in SQL" 弱于 "Built automated SQL reporting pipelines serving 5 business units"
- **Generic verb 综合症：** 每条以 "Responsible for" / "Managed" 开头
- **同一关键词重复 >3 次** — 全简历范围控制

---

## 7. Credibility Test（可信度测试）

每个插入的关键词都要过这一关：
> "如果面试官就这个关键词追问 2 分钟，候选人能否答得 credibly？"

不能 → 移除或弱化（如把 bullet 中的 "Built Tableau dashboards" 降级为 skills section 的 "Exposure to Tableau"）。

与 `quality-pass.md` Pass 3（真实性验证）联动：所有新增关键词必须可溯源到 `assets/experience-bank/raw/*.md`，否则标 `[请确认]`。
