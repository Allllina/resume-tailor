> 本文件仅包含差异化内容。通用框架见 scenario-template.md，写法规则见 general-rules.md
> Lens: C 产品运营 · 简历版本 C · 详见 `role-lenses/C-product-ops.md` · 单归属规则见 `workflow/competency-framework.md §2.1`

# AI 创新产品方向简历优化标准

## 0. 核心理念：判断力 > 动手能力

**产品岗的核心是判断力 + 动手能力，但动手能力作为 AI 产品的加分项，前提是简历先体现了产品判断力。**

为什么这个顺序重要：
- 产品 HM 扫简历时问的第一个问题是"这个人想清楚再做，还是别人 ask 什么就做什么"
- 一条 bullet 如果开头是 "Built X using Y" → 答案是后者 → 被归类为"工程师候选，可被 assign 产品任务"
- 一条 bullet 如果开头是 "Identified that X was causing Y in user segment Z, hypothesized A would solve it, validated through B" → 答案是前者 → 被归类为"产品思考者，能 ship"
- 动手能力（建系统、写代码、上线产品）单独看是中性甚至偏 engineer-leaning 信号；只有当判断力先 established 之后，动手能力才能 reframe 为"会写 prompt / 会评估模型 / 能快速验证假设"的 AI 产品加分项

**简明规则**：

> 一条产品 bullet 的前 60-70% 文字 = 判断力信号（问题判断 + 假设 + 设计 trade-off）；后 30-40% = 执行（model / prompt / eval / tech stack）。如果一条 bullet 写不出判断力部分，就不要写这条 bullet，**即使执行很 impressive**。

---

## 1. AI 产品 bullet 的 6 要素（judgment-first 结构）

替代 `general-rules.md` 第 §"Bullet 六元素解构"中的 engineering-flavored 顺序。AI 产品 bullet 的 6 要素**按顺序**：

| # | 要素 | 类别 | 例 |
|---|---|---|---|
| 1 | **Problem identification** | 判断力 | "Identified that LLM chat tools' AI-flavor over-claim erodes candidates' interview trust" |
| 2 | **Product hypothesis** | 判断力 | "Hypothesized that 'trust as enforced contract' (not as guideline) would differentiate from Simplify / Teal-style template tools" |
| 3 | **Design decision / trade-off** | 判断力 | "Chose source-grounding verification at the bullet-level rather than disclaimer-level — accepting a small false-positive rate to gain full verifiability" |
| 4 | **AI-specific execution** | 动手力（加分）| 见 §2 — model selection / prompt iteration / eval design |
| 5 | **Outcome / validation** | 共同 | "Cut per-JD rewriting time substantially; validated across multiple real applications" |
| 6 | **Tech stack** | 动手力（可选）| "LangGraph + FastAPI + React" — **置于句末，不加粗，不要做 bullet 开头** |

**最低要求**：6 要素中含 **要素 1 或 2** + 要素 5（即至少 1 个判断力 + 结果）；否则该 bullet 退化为流水账，应被剪掉或重写。

**高密度目标**：4-5 个要素 weave 进单句 1.5-2.5 行 bullet。

---

## 2. AI 产品的 3 个"加分项"维度（动手力）

这三个维度是 AI 产品岗位的**专属**信号，engineering 简历不一定有，所以体现出这些 = 把动手能力 reframe 为产品角度的能力。

### 2.1 模型选择 rationale（model selection）

不是写 "used GPT-4"，而是写 **why this model, not others**：

| 维度 | 写什么 |
|---|---|
| **任务 fit** | 该任务是 multi-step reasoning / long-context / 高并发 / 低延迟，哪个模型在这个 axis 上更稳 |
| **Cost / latency trade-off** | 用 mini 版牺牲多少 accuracy 换多少 cost / speed |
| **闭源 vs 开源选择** | 数据敏感 → 选自部署；scale 不大 → 选 API |
| **Eval-driven 选型** | 在 N-query eval set 上对比 X 个候选模型，最终选 Y |

**例**：
- ✅ "在内容审核场景对比 GPT-4o-mini / Claude Haiku / Qwen-Max 三个 mini-tier 模型，基于 200-query 内部 eval set（含 5 个边界 case），选用 Claude Haiku — accuracy 92% vs GPT-4o-mini 88%，且 cost 低 30%"
- ❌ "Used Claude API to build content moderation"（无 rationale）

### 2.2 Prompt 迭代史（prompt iteration）

不是写 "wrote prompts"，而是写 **V1 → V2 → V3 的迭代过程**：

| 维度 | 写什么 |
|---|---|
| **V1 失败模式** | 第一版 prompt 在什么场景失败（hallucination / format drift / refusal）；具体百分比 |
| **诊断 root cause** | 是 context 不足 / instruction 模糊 / few-shot 缺失 / structure 不对 |
| **V2/V3 改进** | 加了什么（chain-of-thought / few-shot / output schema / negative example）；效果 |
| **最终稳定版的判断** | 为什么这一版可以 ship；剩余失败模式怎么 handle |

**例**：
- ✅ "Initial prompt 把 constraint 放 system message，hallucination 偏高 / format compliance 不稳；诊断为 constraint 隐性 + 缺 few-shot 锚定。V3 把 constraint 改成 3-shot positive example + chain-of-thought structure + explicit output schema —— hallucination 显著下降，format compliance 显著提升"
- ❌ "Iterated on prompts to improve accuracy"（无迭代细节）

### 2.3 Eval 设计（evaluation methodology）

不是写 "tested accuracy"，而是写 **eval set 怎么设计 + 怎么测**：

| 维度 | 写什么 |
|---|---|
| **Eval set 设计** | 多少 query / 哪些 distribution（typical vs edge case）/ 谁标的 ground truth |
| **Metric 选择 rationale** | 为什么用 F1 / accuracy / human preference / specific business metric |
| **回归测试** | 怎么 catch prompt 改动引入的 regression |
| **业务 metric 桥接** | 模型 metric（F1）怎么 map 到业务 metric（用户满意度 / 节省时间）|

**例**：
- ✅ "设计 100-query eval set 覆盖 12 个边界 case（长 context / multi-turn / refusal / ambiguous intent），每 query 有 ground truth + 2-3 acceptable variations；benchmark V1-V5 prompt 版本，建立 prompt 更新前的自动回归门，3 个月内 catch 5 次回归"
- ❌ "Achieved 78% accuracy on test set"（无 eval 设计细节）

---

## 3. Before / After 改写示例

体现 judgment-first 改写的对照。每个例子都用真实候选人 source（不编造）。

### 例 1：AI agent 系统项目

❌ **Engineering-style（现在简历常见）**：
> "Built multi-agent resume optimization system on Claude Code Skill + LangGraph + FastAPI + React. Implemented 5 sub-skill orchestration, 5-pass quality pipeline with regex sanitizer and source-grounding verifier. Hundreds of commits and automated tests."

问题：tech stack 在前，全是 "Built / Implemented" 的执行动词。判断力 zero visible。HM 读完只知道你能 ship，不知道你能想。

✅ **Product-style（judgment-first）**：
> "**Identified** that existing LLM chat tools (GPT/Claude direct prompts) produce AI-flavor over-claim that fails interview deep-dives, while template tools (Simplify / Teal) only do surface form-filling — neither serves candidates applying across 3+ industries per season. **Hypothesized** that 'trust-as-enforced-contract' (not as guideline) would differentiate. **Designed** 2-phase architecture: methodology MVP on Claude Code Skill (validate before infra), then productionized to FastAPI + LangGraph backend + React frontend. **Iterated** Pass 3 verifier prompt 4 times — V1 over-flagged benign client names → V4 with custom NDA-whitelist + few-shot cut false positives sharply. **Validated** through multiple real applications across consulting / AdTech / AI roles."

判断力 → 假设 → 设计 trade-off → 动手力（prompt 迭代具体）→ 结果。Tech stack 出现在 "Designed" 句中 in service of 设计判断，不是开场。

### 例 2：AI 客服 / 知识库产品

❌ **Engineering-style**：
> "从 0 到 1 设计并落地 AI 智能客服产品，基于 LLM+RAG 架构实现知识库自动问答，上线 3 个月覆盖日均 5000+ 咨询，人工客服工作量降低 60%。"

问题：纯执行 + 结果。没说为什么是这个客户 / 这个场景 / 这个架构。HM 会问"你怎么决定从哪个客服场景切入？为什么选 RAG 不是 fine-tuning？"

✅ **Product-style**：
> "**诊断**售后客服每日 5000+ 咨询中 70% 集中在 20 个高频问题、且响应时长 vs 满意度强负相关——传统客服扩容 ROI 低于自动化方案。**评估** Fine-tuning 与 RAG 两条路径：FT 维护成本高且新增 SKU 时需重训，RAG 可热更新且对长尾问题更稳——**选用 RAG**。**迭代** retrieval prompt 3 版（V1 top-3 召回 chunks → V3 加入 query rewrite + relevance re-ranking），accuracy 从 71% 提升至 89%。上线 3 个月覆盖日均 5000+ 咨询，人工客服工作量降低 60%，满意度保持 92%。"

诊断（问题判断）→ 评估（两条路径对比）→ 选型决策 → prompt 迭代 → 结果。同样的项目，但 HM 看到的是产品思考过程，不只是执行结果。

### 例 3：内容审核场景

❌ **Engineering-style**：
> "主导大模型在内容审核场景的应用探索，设计 Prompt Engineering 方案，将审核效率提升 3 倍。"

问题：动作 + 结果，但"内容审核"为什么是 AI 适用场景？模型怎么选？怎么验证不误判？

✅ **Product-style**：
> "**识别**内容审核中 80% 案例是规则可枚举的（敏感词 / 模板诈骗 / 已知 spam pattern），剩 20% 需要语义判断——后者人工审核成本占比 60%，是 AI 介入的高 ROI 切入点。**设计**人机协同方案：规则引擎过 80% + LLM 判 20%，且 LLM 输出附 confidence；confidence < 0.7 自动转人工。**评估** 4 个候选模型在 500-case eval set（含 50 边界 case），最终选 Qwen-Max — 误判率 1.8% vs 人工 baseline 2.5%。审核效率提升 3 倍，外包成本节省 200 万/年。"

问题分层（80/20）→ 设计判断（人机协同 + confidence threshold）→ 模型选型（4 候选对比 + eval set）→ 结果。

---

## 4. 岗位画像

AI 创新产品岗位处于技术与商业的交叉点，负责将 AI/LLM 能力转化为实际产品功能或业务形态。可能的岗位包括：AI 产品经理、创新产品经理、AI 应用研究员、智能化产品负责人等。常见于互联网大厂 AI 部门、AI 创业公司、传统企业的数字化转型团队。

---

## 5. 核心能力评估维度

### 5.1 产品判断力（最高优先级）
- 关键词信号：用户痛点诊断、场景拆分、AI 适用边界识别、产品假设、设计 trade-off、ROI 判断
- 这是**所有 bullet 必须显化**的维度

### 5.2 AI 技术理解力
- 关键词信号：LLM 应用、Prompt Engineering、RAG、Agent、多模态、Fine-tuning、Eval 体系、模型选型 rationale
- 不是堆术语，是体现"懂 AI 能力边界 + 会做技术取舍"

### 5.3 动手能力（AI 产品加分项）
- 关键词信号：从 0 到 1 落地、Prompt 迭代细节、eval set 设计、POC、原型测试
- **仅当 5.1 已 established 时该维度才加分**；否则反而把候选人推向 engineer-leaning

### 5.4 商业敏感度
- 关键词信号：商业化方案、Token 成本 / 推理成本优化、付费转化、B 端客户需求
- AI 产品比 SaaS 产品多一层 cost-per-query 思维

### 5.5 快速验证能力
- 关键词信号：POC、原型测试、A/B 测试、人工评测 set 设计、迭代速度

---

## 6. 术语表

### 技术相关（不要堆，按需用）
LLM（大语言模型）、GPT、Claude、Qwen、多模态、RAG（检索增强生成）、Prompt Engineering、Fine-tuning、Embedding、向量数据库、Agent / Multi-Agent、Function Calling、Guardrails、Chain-of-Thought、Few-shot

### 产品相关
AI Native 产品、Copilot、智能体、人机协同、Prompt 模板、知识库、意图识别、对话管理、效果评估、AI 适用边界、产品假设、设计 trade-off

### 指标相关
准确率、召回率、F1-Score、用户接受率、Hallucination rate、Format compliance、Token 消耗、推理延迟、人效提升比、自动化率、人机分流比例

### 商业相关
Token 成本优化、推理成本、SaaS / API 定价、B 端交付、POC（概念验证）、pilot 项目、cost-per-query、ROI 判断

---

## 7. 经历包装策略

### 7.1 核心思路：技术与业务的桥梁

证明你是"技术 ↔ 业务"双向 translator：
- 纯技术背景投 AI 产品 → 强调**产品判断**（用户痛点 / ROI / trade-off），淡化纯实现
- 纯产品背景投 AI 产品 → 强调**AI 能力边界**理解（模型选型 / prompt 迭代 / eval 设计），证明你不是 AI-blind
- **判断力优先 + 动手力补位** 永远是正确顺序，不要倒过来

### 7.2 加分项 vs 减分项

| 加分 | 减分 |
|---|---|
| 从 0 到 1 真上线（非 PPT 调研报告）| "做了 AI 项目调研"（没落地）|
| 模型选型 + eval 对比的具体证据 | "Used LLM"（无选型逻辑）|
| Prompt 迭代史（V1→V3 + 失败模式）| "Wrote prompts to improve accuracy"（无迭代细节）|
| 成本优化的经验 + 具体数字 | 无 cost 视角 |
| AI 伦理 / 安全 / 风控的考虑 | 只谈能力不谈风险 |
| 业务 metric 桥接 model metric | 只有 model metric（F1 / accuracy）|

### 7.3 HR Tech / Vertical AI 方向

HR Tech：招聘智能筛选、简历解析、人才画像、智能排班、NLP 简历解析、人才知识图谱、HR Chatbot、RPA + AI 工作流、智能推荐
强调"技术 + HR 业务理解"双向桥梁角色，特别在 prompt 设计时如何 encode HR 专业 judgment。

其他 vertical（医疗 / 法律 / 金融）：核心 pattern 相同——先证明你懂这个 vertical 的业务判断（场景拆分 + ROI），再叠 AI 工具链。

### 7.4 项目段（Projects）vs 实习段（Internships）的差异

- **项目段**：用 6-要素 full bullet（problem → hypothesis → design → AI execution → outcome）。这是你自主判断 + 自主落地的最强证据。
- **实习段**：通常 ownership 等级低（intern 角色），如果整段实习的判断力是别人决定的，bullet 应聚焦"你 contributing 的部分有什么判断"——不是"项目整体如何"。

---

## 8. 与其他文件的耦合

- `role-lenses/C-product-ops.md` §"判断力优先" — 该 lens 下所有 sub-scenarios 共享的总原则；本文件是 AI 产品的具体化
- `general-rules.md` §"role-specific bullet 排序" — 全局原则
- `scenarios/product-strategy.md` §"判断力 hierarchy" — 战略型产品的同源原则（Lens A）
- `scenarios/ai-engineering.md` — 姊妹场景（AI 工程 / Agent 开发角度，action-first）；同 Lens C，投工程岗时改用该文件
- `quality-pass.md` Pass 1 关键词注入 — Prompt Engineering / RAG / Eval 等术语注入位置；优先注入到带判断力的 bullet，不优先注入到 tech-stack list
