# Lens C — 产品运营（Product Operations）

**对应简历版本：** C
**对应 role_family：** `C_product_ops`
**下位 scenarios：** `product-ops.md` / `data-ops.md` / `customer-success.md` / `ai-innovation.md`

---

## 0. 总原则：判断力 > 动手能力（产品岗 bullet 写作 hierarchy）

**产品岗的核心是判断力 + 动手能力，但动手能力作为加分项，前提是简历先体现了产品判断力。** 这条原则适用于本 lens 下**全部 sub-scenarios**（product-ops / data-ops / customer-success / ai-innovation）。

### 为什么这个顺序重要

产品 HM 扫简历时回答的第一个问题是"这个人想清楚再做，还是别人 ask 什么就做什么"：

- 一条 bullet 开头是 **"Built X using Y" / "搭建了 X 体系" / "技术栈 abc + 做了 d 件事"** → 答案是后者 → 候选人被归类为"工程师 / 运营执行者，可被 assign 产品任务"
- 一条 bullet 开头是 **"诊断出 X 用户群体的 Y 痛点，假设 Z 方向能解决，设计 A 方案 trade-off B，验证后 C"** → 答案是前者 → 候选人被归类为"产品思考者，能 ship"

动手能力（搭体系 / 写代码 / 上线产品）单独看是**中性甚至偏 execution-leaning 信号**；只有当判断力先 established 之后，动手能力才能被 reframe 为加分项（AI 产品里是"会写 prompt / 会评估模型 / 能快速验证假设"）。

### Bullet 简明规则

> 一条产品 bullet 的**前 60-70% 文字 = 判断力信号**（问题判断 + 用户洞察 + 产品假设 + 设计 trade-off）；**后 30-40% = 执行**（具体动作 + 工具 + 结果）。
>
> 如果一条 bullet 写不出判断力部分，**就不要写这条 bullet**，即使执行很 impressive。宁可少写一条，也不写一条 engineer-flavored 的纯执行 bullet。

### 判断力的 4 个可显化维度

每条 bullet 至少含以下 1-2 个判断力维度（任选）：

| 维度 | 写什么 | 例 |
|---|---|---|
| **用户痛点诊断** | 你识别了什么用户痛点 / 业务问题 | "识别出 7 日留存断崖出现在第 3 天而非 1 日，定位为 ..." |
| **场景拆分 / 优先级判断** | 你怎么决定从哪个场景切入 | "80/20 拆解客服场景：80% 规则可枚举 + 20% 需语义判断；后者是 AI 介入的高 ROI 切入点" |
| **产品假设** | 你提出的解决思路是什么，对比了哪些备选 | "Hypothesized 触达体系应分层而非一刀切；3 种触达方案分别针对 ..." |
| **设计 trade-off** | 你做了哪些关键设计权衡 | "选 RAG 而非 fine-tuning：维护成本 + 热更新 vs 长尾问题稳定性的权衡" |

### Sub-scenario specific 加分项

不同 sub-scenarios 在判断力 established 后，加分项不同：

| Sub-scenario | 加分项类型 | 具体维度 |
|---|---|---|
| `ai-innovation.md` | AI 工程能力 | 模型选择 rationale / Prompt 迭代史 / Eval 设计（详见该文件 §2）|
| `product-ops.md` | 运营执行能力 | 漏斗分析 / 触达体系 / 分层运营 / 转化路径 |
| `data-ops.md` | 数据驱动能力 | Dashboard 设计 / 指标体系 / 异动归因 / 业务支持 |
| `customer-success.md` | 客户成功能力 | 客户分层 / 流失预警 / 续约率提升 |

**通用规则**：所有 sub-scenarios 都先按本节 § 0 的判断力 hierarchy 写 bullet，加分项是在判断力 established 之后再 layered 进去。

详细的 AI 产品 6-要素 bullet 结构 + 模型 / Prompt / Eval 加分项 → 见 `scenarios/ai-innovation.md` §1-3。

---

## 1. What recruiters screen for

招聘人在筛"能不能用流程 + 迭代而非授权来推动产出，把用户洞察 + 数据 + 执行串起来让产品团队更有效"。底层：**用户共情 + 跨职能协调 + 操作严谨 + 通过流程驱动结果**。

---

## 2. Prioritize

- **用户洞察** — 理解用户行为 / 做用户研究 / 把用户需求翻译成产品决策的证据
- **Growth / 转化 / 留存 / 漏斗逻辑** — metrics-aware 思考用户在产品中的移动。漏斗分析 / cohort / 留存指标
- **跨职能协调** — 与工程 / 设计 / 营销 / 数据团队配合。influence without authority
- **执行与迭代** — ship feature / run experiment / manage launch / iterate based on feedback。bias toward action
- **问题诊断与流程优化** — 找瓶颈 / 建 playbook / 改 workflow
- **数据驱动决策** — 用数据支持产品决策（不是纯分析师）

---

## 3. De-emphasize

- 纯战略抽象没实施 / metrics 关联（→ Lens A）
- 深度技术实现细节（code architecture / infrastructure）
- 像项目经理简历（仅 timeline 管理没产品洞察）
- 学术研究没产品应用

---

## 4. Language signals

| 信号 | NA 动词 | 内地动词 |
|---|---|---|
| 强 | launched / iterated / coordinated / diagnosed / optimized / drove (growth/adoption/retention) | 上线 / 迭代 / 拉通 / 诊断 / 优化 / 推动（增长 / 留存 / 转化） |
| 弱 | planned (无执行) / managed (仅 timeline) / researched (无产品 link) | 规划 / 跟进 / 协助 / 看 |

---

## 5. Bullet pattern

**[Action] + [产品 / 用户语境] + [跨职能要素] + [执行细节] + [用户 / 业务指标 impact]**

### NA 示例
> "Coordinated cross-functional launch of in-app onboarding redesign across product, engineering, and design teams, diagnosing a 40% Day-1 drop-off through funnel analysis and driving iteration that improved activation rate by 15%."

### 内地示例
> "拉通产品 / 研发 / 设计三方推动新人引导改版上线，基于漏斗分析定位首日 40% 流失节点，主导 3 轮迭代将激活率提升 15%（覆盖月新增 50 万用户场景）。"

---

## 6. 与 scenarios 的下位关系

本 lens 单归属以下 scenarios（与 `competency-framework.md §2.1` MECE 铁律一致）：

| Scenario | 主要适用 |
|---|---|
| `scenarios/product-ops.md` | 通用产品运营（功能 / 流程 / 用户运营） |
| `scenarios/data-ops.md` | 数据运营（dashboard / 报表 / 业务支持，非纯分析师） |
| `scenarios/customer-success.md` | 客户成功 / 用户成功（客户生命周期管理） |
| `scenarios/ai-innovation.md` | AI 产品 / agent 类产品运营 |

边界岗位：`growth-strategy` 与 `product-strategy` 由 Lens A 单归属（即使 JD 偏 ops 视角，仍加载 A 的 scenario 文件，在 `scoring_notes` 标注 secondary lens C）。AI strategy 类岗位：仍加载 `ai-innovation`，secondary lens 标 A 或 B。详见 `competency-framework.md §2.2`。

---

## 7. 候选人证据钩子

- **Ipsos（02-ipsos.md）** — 用户研究 / 客户洞察 → 产品决策的桥接
- **Desay SV（03-desaysv.md）** — 业务运营 / 海外子公司 / 流程优化（如适用）
- **Projects（06-projects.md）** — AI agent / 产品类项目 / 增长项目

---

## 8. 与 target_market 的交互

NA：metric-first，"increased X by Y%"。
内地：scope-first（覆盖业务线 / DAU / GMV）+ 跨职能动词（拉通 / 推动 / 协同）+ 量化结果。

---

## 9. Anti-narrative

- "Project manager with product interest"
- "Coordinator who scheduled meetings"
- "Data analyst who happens to do product work"
