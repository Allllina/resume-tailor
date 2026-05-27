---
title: 经历内容契合度（Vertical Fit）评分判准
status: v0.1 draft（待用户审阅 / 修改）
last_updated: 2026-05-04
owner: Resume_Optimizer
related:
  - assets/experience-bank/index.json (vertical_fit_per_lens 字段)
  - assets/knowledge-base/references/recognition-rubric.md (姊妹文档：品牌信号轴)
  - packages/strategy-modules/resume-rewrite-engine/SKILL.md (实习筛选优先级硬规则)
  - assets/knowledge-base/references/role-lenses/{A,B,C,D,HC}-*.md (lens 能力定义)
---

# Vertical Fit Rubric — 经历内容契合度评分判准

## 1. 用途

为 `experience-bank/index.json` 的 `vertical_fit_per_lens` 字段提供打分依据。每条经历 × 5 个 lens 打 core / adjacent / weak / missing。

**与 `recognition-rubric.md` 的分工：**

| 字段 | 回答的问题 | 看什么 |
|---|---|---|
| `recognition_per_industry` | 招聘方看到这家公司**眼前一亮**吗？ | 公司品牌 × 行业圈子 |
| `vertical_fit_per_lens` | 经历的**实际内容**能不能映射到该 lens 的能力要求？ | bullet 内能力 × lens 能力定义 |

两者都是简历筛选 / tailoring 决策依据，但是**不同的轴**，不能合并打分。

## 2. 评分轴定义

**Vertical fit = 经历的内容（动作 / 方法 / 产出）与目标 lens 能力要求的对位程度。**

只看内容，不看公司品牌。同一家公司不同项目可以得不同分（Mercer 组织咨询 vs Mercer 福利精算）。

| 等级 | 判准 | bullet 重写工作量 |
|---|---|---|
| **core** | 经历中有 ≥1 个项目 / 任务**直接命中** lens 5 维能力之一；bullet 几乎不用 reframe，原始措辞已落在 lens 语境里 | 0–10%（轻微 polish） |
| **adjacent** | 经历有相关能力但视角 / 落点不同，需要换叙述角度（如把"战略复盘"换成"业务诊断"角度）；bullet 必须 reframe 但 underlying fact 不变 | 30–50%（中度重写） |
| **weak** | 经历跨界大；bullet 内主要价值不在该 lens 的能力维度上，必须依赖**可迁移技能论证**（structured thinking / data sense / project mgmt 这类通用层）才能上 | 60–80%（重度改写） |
| **missing** | 该经历对该 lens **完全没有可用素材**——没动作、没产出、没相关背景 | N/A（直接不上） |

## 3. 证据等级（由强到弱）

> 评分必须能在 raw 文件里指到具体段落 / bullet 作为证据。仅 `inferred` 级别的评分要标 `evidence_strength: "inferred"`。

1. **direct_bullet** — raw 文件中明确写有该 lens 关键能力的 bullet
   - 例：`03-desaysv.md § 项目 4 第二层 "组织绩效诊断 5 横×6 纵框架"` → HC core 的直接证据
2. **direct_capability_tag** — raw 文件 capability_tags 明确包含该 lens 关键能力词，但具体 bullet 散在多个项目
   - 例：`02-ipsos` 标 "data modeling" → B adjacent
3. **inferred** — raw 文件没明示，但能力可迁移；必须标 `evidence_strength: "inferred"`，并写明可迁移的具体逻辑（"structured thinking 可迁移 / market sizing 跨行业通用"）
4. **none** — 没任何线索；直接打 `missing`，**不要硬扯迁移**

## 4. Lens 列（与 `role_family` 1:1 对齐，5 项）+ 横切层（1 项）

### 4.1 五个 Lens（vertical 主轴）

| Lens | 关键能力锚点（极简版） |
|---|---|
| **A_strategy_research** | 行业研究 / 竞争格局 / 市场容量 / 战略选择 / 方法论框架（PEST / Porter / 价值链）|
| **B_data_analytics** | 数据建模 / 统计推断 / SQL+Python / 业务指标体系 / 异动归因 |
| **C_product_ops** | 用户运营 / 增长漏斗 / A/B test / 标签体系 / 产品迭代闭环 |
| **D_finance_markets** | 估值建模 / 财务分析 / 资本市场 / 行业研报 / 投融资逻辑 |
| **HC_human_capital** | 组织诊断 / 任职资格 / 薪酬体系 / 绩效管理 / HR 数字化 |

详细 5 维能力定义见 `role-lenses/{A,B,C,D,HC}-*.md`，本表只为打分时快速 anchor。

### 4.2 AI / Digital Fluency（横切层，独立打分）

**定义：** 经历中体现出的 AI 工具实操深度 + 数字化方法论熟练度。**不是第 6 个 lens**，而是一条与 5 个 lens 正交的横切轴——任何 lens 的招聘方都会单独评估这一层。

**为什么独立打分：** 2025-2026 招聘方对"会用 AI"的判断与对"对口能力"的判断**走两套筛选**——AI fluency 强可让 fit 中的经历多一个加分维度，反之 AI fluency 弱不会拖累 lens core 评分。两者要分开看，不能混在 vertical_fit 里。

**等级：**

| 等级 | 判准 |
|---|---|
| **strong** | 经历中有 ≥1 处**直接动手**实操：自建 agent / 训练或微调模型 / 写过 RAG / Text-to-SQL pipeline / Prompt Engineering 落地业务 / MCP 工具集成；可在 bullet 里点名工具栈 |
| **moderate** | 用过 LLM 提效（Cursor / Copilot / ChatGPT 辅助分析），但无独立实现；**需在 bullet 里诚实标注层级，不能伪装成 strong** |
| **weak** | 仅"了解概念" / 课程学过 / 浅尝试但无产出 |
| **none** | 经历完全无 AI / digital 元素；或经历完成于 AI 工具普及之前且无后续补充 |

**能力锚点（用于打分时快速 match）：** Prompt Engineering · Agent / LangGraph · RAG · Fine-tuning · Text-to-SQL · MCP / Tool Use · Embedding / Vector Search · BERT / NLP modeling · AIGC 工作流 · A/B test 自动化 · Claude Code / Cursor 工程化使用

**与 lens 评分的关系：**
- AI fluency = strong **不能**自动把 lens 从 weak 升到 adjacent；该 lens 内容仍要单独评估。
- 但当 lens score = adjacent 或 core 时，AI fluency = strong 可让该经历在 routing 中获得 **+1 偏好权重**（同等条件下优先选 AI fluency 高的经历上简历）。
- 当目标 JD 明确提 AI 关键词（Prompt Engineering / Agent / RAG / 标签体系等）时，AI fluency = strong 升级为**硬性筛选条件**，弱于 strong 的经历不上。具体规则在 `resume-rewrite-engine/SKILL.md`。

## 5. 边界与陷阱

- **同一经历不同项目要分别打分**。Desay SV 有 5 个项目（Europe strategy / 低空经济 / 质量转型 / 供应链数字化 / 组织绩效诊断），其中"组织绩效诊断"对 HC 是 core，对 A 是 adjacent；其余 4 个项目对 A 是 core，对 HC 是 weak。打分时要锚到**最强项目的最高分**，但 rationale 要写明是哪个项目支撑（agent 后续 bullet 选取要走这个锚点）。
- **不要为了"多上简历"放水**。adjacent 与 weak 之间的界线：*能否在不重写事实、只换叙述视角的情况下命中 lens 能力*。如果必须**新增动作 / 新增产出**才能命中——这已经是 weak 了，甚至可能是 missing 套着可迁移叙述的伪装。
- **可迁移技能 ≠ vertical fit**。"结构化思考" / "项目管理" / "跨部门沟通"是所有 lens 都需要的通用层，单独依赖这些只能撑 weak，不能升级到 adjacent。adjacent 必须有 lens-specific 内容线索。
- **fit 的"高"不补 recognition 的"低"**（这是与 recognition rubric §9 联动的硬规则）。这条文档化在 `resume-rewrite-engine/SKILL.md` 的 4 象限决策表里。

## 6. 时效性

- direct_bullet 评分稳定（除非 raw 文件被改）
- inferred 评分需在每次新 lens 定义更新（`role-lenses/*.md` 变动）后复核
- 添加新 lens（目前只有 5 个；如未来出现新 family）时，所有 6 条经历都要补一列

## 7. JSON 字段格式（在 index.json 中）

```jsonc
{
  "experience_id": "03-desaysv",
  "vertical_fit_per_lens": {
    "A_strategy_research": {
      "score": "core",
      "evidence_strength": "direct_bullet",
      "anchor_projects": ["项目 1 Europe strategy review", "项目 2 低空经济研究"],
      "rationale": "战略选择 + 行业研究 + 价值链分析三维都直接命中"
    },
    "B_data_analytics": {
      "score": "adjacent",
      "evidence_strength": "direct_capability_tag",
      "anchor_projects": ["项目 4 组织绩效诊断（5 横 6 纵框架）"],
      "rationale": "有数据诊断动作但建模深度不足；reframe 为指标体系视角可上"
    },
    "C_product_ops": {
      "score": "weak",
      "evidence_strength": "inferred",
      "rationale": "供应链数字化项目可迁移 ops 闭环逻辑，但缺直接 product / 用户运营素材"
    },
    "D_finance_markets": {
      "score": "missing",
      "evidence_strength": "none",
      "rationale": "无估值 / 资本市场 / 财务模型素材"
    },
    "HC_human_capital": {
      "score": "core",
      "evidence_strength": "direct_bullet",
      "anchor_projects": ["项目 4 组织绩效诊断", "项目 5 海外子公司治理"],
      "rationale": "组织诊断 + 海外子公司治理 + 绩效体系三处直接命中 HC 5 维"
    }
  }
}
```

> **null 约定**：与 recognition 一致——若该 lens 完全没评估、缺方法论锚点（如新加 lens 但还没回填），写 `null`，agent 走 fallback。

## 8. 已 verified 的 entries（首批 anchor，待用户校验）

> 以下评分基于 `index.json` 现有 `capability_tags` + `role_family_relevance` 字段反推。每条都标 `tentative=true`，等候用户逐条确认或修改。打 `core` 的尤其需校验，避免推高过头。

| Experience | A 战略 | B 数据 | C 产品运营 | D 金融 | HC 人力 | 主要证据出处 |
|---|---|---|---|---|---|---|
| 01-kearney | core | adjacent | adjacent | weak | weak | role_family_relevance: strategy/consulting/BA/market research |
| 02-ipsos | adjacent | core (data modeling) | adjacent | adjacent (CTX bottom-up sizing 与金融分析方法论相通) | weak | capability_tags: data modeling/market sizing |
| 03-desaysv | core | adjacent | core (供应链数字化 + 质量管理可视为 ops 闭环) | missing | core (组织绩效诊断 + 海外子公司治理) | role_family_relevance: 5 lens 都涉及；项目 1+2 → A，项目 4+5 → HC |
| 04-mercer | adjacent | adjacent | weak | weak | core (主线就是组织咨询) | 待 raw 文件校验 |
| 05-sdic | adjacent | adjacent | weak | core (主线就是金融市场 / 国投证券) | weak | 待 raw 文件校验 |
| 06-projects | adjacent | core (NYC ETL + Reddit BERT) | core (LangGraph Agent + 标签体系) | weak | adjacent (Resume Optimizer Skill 系统涉及组织 / 招聘逻辑) | 待逐项目拆分 |

> **重要**：上表 04-mercer / 05-sdic / 06-projects 是基于 user-profile 信息和投递记录的 inference 评分，未读 raw 文件细节。回填 index.json 前必须先打开这 3 个 raw 文件逐项目校验，将 `evidence_strength` 升级为 `direct_bullet` 或调整分数。

## 9. 与 `recognition_per_industry` 的联动决策表

（与 recognition-rubric §9 同步；正式硬规则放 `resume-rewrite-engine/SKILL.md`）

| recognition × fit | 决策 | 理由 |
|---|---|---|
| 都高 | **必上** | 招牌+内容双信号 |
| recognition 高 / fit 低 | 上，bullet 努力靠拢 lens 能力（rewrite 重活） | 招牌不能浪费，但要避免内容拖后腿 |
| recognition 低 / fit 高 | **不优先** | 招牌不识别会增加阅读成本，即使内容硬也不优先；除非空位且无替代 |
| 都低 | **删** | 双低=减分项，宁缺毋滥 |

> 注：recognition 低 / fit 高 = "不优先"——这是 v0.1 的保守取向，源自京东 BA 面试官反馈"宁可少放也要保证认可度"的经验。后续若投递规模 ↑、招聘方多样性 ↑，可重审本格。

## 10. 待修订（请用户审阅）

- [ ] §4 的 5 lens 关键能力锚点是否覆盖到位？是否要加第 6 个能力锚点（如 AI / digital fluency 横切层）？
- [ ] §8 anchor 表中 02-ipsos × D 打 adjacent（理由：CTX bottom-up sizing 与金融行研方法论相通），是否过高？还是确实可作为投资分析师 / 行研 lens 的 transferable claim？
- [ ] §8 anchor 表中 06-projects 是否应该按项目（LangGraph / Reddit / NYC ETL / Resume Optimizer Skill）逐条拆开评分，而不是合并打分？
- [ ] §5 是否需要加一条规则关于"项目段（个人项目）与实习经历的 fit 是否同等权重"？候选人感觉如何？
- [ ] §9 联动决策表是否需要加第 5 行处理"recognition unknown / fit any"的情形？（建议默认按 recognition=low 处理，但等用户确认）
