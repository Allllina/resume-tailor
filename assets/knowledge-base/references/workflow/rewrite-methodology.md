# Rewrite Methodology — 候选人审计、叙事、优先级、ATS 注入

供 `packages/strategy-modules/resume-rewrite-engine/` 与根 `SKILL.md` Step 4–7 调用。本文件定义重写决策的方法论；产物结构见 `packages/strategy-modules/resume-rewrite-engine/output-schema.md`，bullet 写作标准见 `general-rules.md`。

---

## 1. Candidate Audit（候选人六维审计）

不要"读简历" — 拿 competency model 逐条质询经历。

### 1.1 Direct Fit（直接命中）
经历直接对应 must-have 资质。
- 候选人有这种类型的经历吗？
- 能用具体可信的证据展示吗？
- 时效 / 深度 / 语境是否足够强？

> 自检："如果招聘人看到这条 bullet，会不会立刻想'这人干过这个'？"

### 1.2 Transferable Fit（可迁移）
不完全对应但展示底层能力。
- 用什么 transferable skill 桥接？
- 让连接可见需要多少 narrative 工作？
- 招聘人会买账吗，还是太牵强？

> 自检："我能在不夸大匹配度的情况下重新框架这段经历，让相关能力显眼吗？"

### 1.3 Low-Signal（低信号）
不加分也不扣分，仅占位。
- 通用实习描述无具体内容
- 仅展示参与但无成就 / 能力信号
- 课程罗列无应用语境

**处理：** 压成一行或删除，除非雇主品牌带可信度。

### 1.4 Distracting（干扰性）
积极指向另一条职业方向。
- 数据分析师简历上的创意写作作品集
- 咨询简历上的零售管理（除非重新框架）
- 战略简历上的技术 deep-dive

**处理：** 删除或大幅压缩。雇主品牌有价值就保公司名 + title，bullet 重写只抽取角色相关信号。

### 1.5 Proof Strength（证据强度）
每段经历能用多具体的证据证明。
- 有数字 / 结果 / 具体 deliverable 吗？
- 贡献是否具体到 credible？
- 证据能扛住 "so what?" 测试吗？

| 强度 | 标准 |
|---|---|
| Strong | 具名 metrics / 具名 deliverables / 清晰结果 |
| Moderate | 清晰活动与语境，无量化 |
| Weak | 通用描述，谁干都能这么写 |

### 1.6 Gaps（差距）
competency model 要求但候选材料没覆盖的。
- 哪些 must-have 完全无证据？
- 哪些 strongly-preferred 缺失？
- 能否通过创造性 reframe 既有经历部分弥补？
- 哪些 gap 必须诚实在 Risk Flags 标注？

> 与 `workflow/gap-bridging.md` 的 5a/5b/5c 联动：bridge → add → skill gap。

---

## 2. Narrative Construction（叙事构建）

### 2.1 单一叙事原则
每份有效简历讲一个故事。这个故事回答："这个人是哪种专业人士？为什么对这个具体角色 credible？"

### 2.2 找叙事的方法
1. 看候选人 2-3 个最强经历（按 proof strength + 角色相关性）
2. 找共同线索 —— 它们集体展示了什么 capability / profile type？
3. 把这条线索对照 competency model 的核心招聘逻辑（Section B）
4. **叙事 = 候选人最强证据 ∩ 角色最高优筛选标准**

### 2.3 叙事示例（按 5 lens）

| Lens | Strong narrative | Weak narrative |
|---|---|---|
| A 战略研究 | "结构化问题解决者，把研究综合成可执行 recommendation" | "Well-rounded business student with diverse experience" |
| B 数据分析 | "Metrics-driven 分析师，搭建 pipeline 并把数据翻译成业务决策" | "Data enthusiast with Python and SQL skills" |
| C 产品运营 | "用户痴迷型 operator，协调跨职能团队 ship & iterate" | "Organized project manager with product interest" |
| D 金融市场 | "Sector-focused analyst，搭建模型并形成独立投资观点" | "Finance student interested in markets" |
| HC 人力资本 | "组织诊断者，用数据让人才与组织决策更可证据化" | "HR enthusiast who likes working with people" |

### 2.4 Anti-Narrative（反向叙事）
也要定义简历**不应该**意外读起来像什么：
- "缺方向感的 generalist"（最常见）
- "技术的人装作业务的人"（或反过来）
- "junior 在膨胀 seniority"
- "用一份简历投所有岗位"

每个 section 都要 reinforce chosen narrative，避免 anti-narrative。

---

## 3. Prioritization Logic（优先级四档）

### Category 1: Must Lead and Expand
- 直接对应 must-have qualifications
- 候选人有强证据（metrics / specifics / outcomes）
- 是简历叙事核心
- **位置：** 顶部经历，最大 bullet 数（4-6）

### Category 2: Keep but Compress
- 对应 strongly-preferred qualifications
- 加 credibility 但不是核心故事
- 雇主品牌 / 经历类型增值
- **位置：** 保留，2-3 个压缩 bullets

### Category 3: Retain as Supporting Signal
- 提供广度 / 展示 nice-to-have
- 有价值的雇主品牌或 credential
- **位置：** 一行提及 / skills section

### Category 4: Downgrade or Remove
- 干扰、偏离叙事、低信号
- 占用更高价值内容空间
- 可能意外触发 anti-narrative
- **处理：** 整段删除，或仅保公司名 + title 如品牌价值值得

### 优先级铁律
- 不同价值的经历**绝不**给同等空间
- 第一页前 1/3 real estate **专属** Category 1
- Category 2 vs 3 不确定时自问："招聘人非读这段不可才能理解候选人 fit 吗？" 不是 → 再压
- Category 4 决定要在 output Section C 解释，让用户理解为什么

---

## 4. ATS Optimization（ATS 注入策略）

### 4.1 原则
1. ATS 优化和人类可读性**不冲突**，做对了就同时满足
2. 关键词应放在真实经历自然支持的位置
3. 密度重要，但 credibility 更重要
4. 现代 ATS / AI 用语义相似度，不只是 exact match

### 4.2 关键词集成（详见 `keyword-extraction.md`）

**Resume headline / title line：**
插 1-2 个 Tier 1 核心词。最高 impact 位置。
> "Data Analyst | Business Intelligence & Analytics" 强于 "Recent Graduate Seeking Opportunities"

**Professional summary（3-4 行）：**
weave 4-6 个 Tier 1+2 高价值词。读起来像自然段落，不是关键词清单。

**Experience bullets：**
verb-capability-tool 模式：[Tier 4 动词] + [Tier 2 capability] + [Tier 3 tool/method] + [outcome]。每条自然含 2-3 个词，不强塞。

**Skills section：**
Tier 3 综合罗列。这是唯一适合 clean list 的位置。按类别分组（"Analytics: SQL, Python, Tableau, Power BI"）。

### 4.3 不要做
- 不创建 invisible keyword block（白字 / 隐藏区块）
- 不列经历未支撑的工具
- 不强塞关键词到不属于的 bullet
- 同一关键词不重复 >3 次（全简历范围）
- 不照抄 JD 原句如果用候选人口吻不自然

### 4.4 Credibility Test
每插一个关键词都自问：
> "面试官就这个关键词追问 2 分钟，候选人能 credibly 答出吗？"

不能 → 移除或弱化（如降级到 skills section 的 "Exposure to Tableau" 而不是 bullet 的 "Built Tableau dashboards"）。

---

## 5. 与 gap-bridging.md / quality-pass.md / general-rules.md 的边界

| 文件 | 负责 |
|---|---|
| 本文件 (rewrite-methodology) | audit / narrative / prioritization / ATS 集成的方法论 |
| `jd-analysis.md` | JD 五层结构拆解（核心定位 → 硬性要求 → 核心能力 → 加分项 → 关键词） |
| `gap-bridging.md` | 5a 经历桥接 / 5b 经历补充 / 5c 技能调整 三档具体策略 |
| `quality-pass.md` | 三步质量 pass（关键词注入 → AI 味清洗 → 真实性验证） |
| `keyword-extraction.md` | 关键词提取与分级架构（被 quality-pass Pass 1 引用） |
| `general-rules.md` | bullet 级写作标准（公式 / 量化 / 动词 / 长度） |

本文件输出**决策**（哪段 lead / 哪段删 / 叙事是什么），`general-rules.md` 输出**句子**（每个 bullet 怎么写）。

---

## 6. 与 target_market 的耦合

不同市场的 audit / narrative / prioritization 都会变化。

| 维度 | NA | HK | 内地 |
|---|---|---|---|
| Proof 优先级 | Impact → Method → Scope | Scope → Credentials → Impact | Pedigree → Scope → Relevance → Impact |
| Front door 内容 | Summary + 第一段经历 | Summary + 证书 / 语言 + 第一段经历 | 学校 + 雇主品牌 + summary 关键词 |
| Bullet 密度 | Fewer / punchier | Moderate / 更多语境 | Moderate / scope-heavy |

详见 `market-contexts/{north-america, hong-kong, mainland-china}.md`。
