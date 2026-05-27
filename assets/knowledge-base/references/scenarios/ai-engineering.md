> 本文件仅包含差异化内容。通用框架见 `scenario-template.md`，写法规则见 `general-rules.md`。
> Lens: C 产品运营 · 简历版本 C · 详见 `role-lenses/C-product-ops.md` · 单归属规则见 `workflow/competency-framework.md §2.1`
> 姊妹场景：`scenarios/ai-innovation.md`（AI 产品 PM 视角，judgment-first 6-要素 bullet）

# AI 工程方向简历优化标准（Engineering / Agent Development）

适用岗位：AI 工程师 / Agent 开发 / 数据策略实习 / ML 工程师 / LLM 应用开发——介于纯产品 PM 和纯 SDE 之间的复合角色，核心要求是**写代码 + 想清楚业务**双能力。

常见公司：内地大厂 AI 部门（字节 AI / 阿里 DAMO / 腾讯 AI Lab）、AI 创业公司（RAG / Agent / LLM application）、传统企业数字化转型 AI 团队、自动驾驶 / 机器人公司 AI 应用部门。

## 0. 与 AI 产品岗（ai-innovation.md）的核心差异

| 维度 | AI 产品 PM 岗（`ai-innovation.md`）| AI 工程岗（本文件）|
|---|---|---|
| 主旋律 | 用户洞察 + 产品判断 + AI 执行 | 工程能力 + 技术深度 + 业务理解 |
| Bullet 起手 | 名词标签（用户洞察 / 产品架构 / 模型选型）| 动词起手（实现 / 设计 / 搭建 / 主导）|
| 技术栈位置 | bullet 内嵌（服务产品叙事）| 单独 prefix 行（ATS 友好）|
| 量化重心 | 业务 metric 为主 | 工程 metric + 业务 metric 双轨 |
| 判断力 vs 动手力 | 判断力 > 动手力 | **判断力 = 动手力（并列）** |

**为什么区分**：同一个 AI 项目投 PM 岗 vs 工程岗，bullet 写法完全不同。reviewer 视角不同：PM reviewer 看候选人会不会想产品；工程岗 reviewer 看候选人会不会写代码 + 能不能想清楚业务上下文。

---

## 1. 技术栈：独立 prefix 行 + 分类（最关键格式差异）

工程岗简历**标准结构**：

```
项目标题                                              [时间]

技术栈
- 后端：Python · FastAPI · LangGraph · LangChain · Anthropic / OpenAI · Pydantic · SQL · pytest
- 前端：TypeScript · React 19 · TanStack · Tailwind CSS · Vite
- 工程：Docker · Git

- bullet 1
- bullet 2
- bullet 3
```

**为什么 prefix 行**：
- ATS 系统按关键词索引，prefix 单行命中率最高
- 工程岗 reviewer 第一眼想看 "她会哪些技术"——藏在 bullet 字里行间会被错过
- 业务描述和技术栈分层清晰，互不打扰

### 1.1 技术栈精简原则

**砍掉**：
- 框架同生态自带库（FastAPI 自带 uvicorn / pydantic-settings → 不列）
- 通用工具（httpx / pyyaml / json → 不列）
- 单纯 utility（loguru / tenacity → 不列）

**保留**：
- JD 命中关键词
- 核心 stack（语言 + 框架 + 数据库）
- 工程纪律 signal（testing / Docker / CI）

**目标**：12-16 items 跨 2-3 行。

### 1.2 PM 岗不适用此格式

PM 岗用 **bullet 内嵌**（让技术栈服务于产品叙事），不用 prefix 行。详见 `ai-innovation.md`。

---

## 2. Bullet 结构：动词起手 + 模块 + 技术 + 量化

工程岗 bullet 标准 pattern：

```
[动词] + [核心模块] + [技术栈 inline] + [关键数据 / 结果]
```

**实例**：

- **实现** Skill 工具函数集：用 Python 把 JD 解析、能力建模、内容重写等业务逻辑封装为 5 个独立 Skill；每个 Skill 用 Pydantic schema 锁定输入输出、jsonschema 校验、tenacity 实现 retry / timeout 异常处理；配套数百项 pytest 测试。

- **设计**基于 LangGraph + LangChain-Anthropic 的 5-Agent 串行编排框架，覆盖 JD 解析、能力建模、gap 诊断、内容生成、真实性核查 5 个阶段，按 Mode L / F 路由不同执行路径；经三轮 Prompt 迭代显著降低幻觉率。

- **搭建** Pass 3 真实性核查 verifier，用 LangGraph StateGraph 把生成结果拆为 claim 列表逐条与 ground truth 文件比对，无源 claim 触发 user verify 闭环。

**对比 PM 岗 bullet 模板**（来自 `ai-innovation.md`）：

```
[Problem identification] + [Hypothesis] + [Design trade-off] + [AI execution] + [Outcome]
```

PM 岗是 problem-first；工程岗是 action-first。**两种模板不能混用**——同一项目投不同岗位需要重写 bullet。

---

## 3. Bullet 1：必须 anchor 业务问题（即使工程岗）

工程岗也需要 bullet 1 anchor 业务问题 + 量化产出。但**表达方式不同**：不喊"用户痛点"作 emotional language，直接讲"目标场景 + 量化产出"。

**模板**：

```
bullet 1 = [系统描述]，面向 [target use case]，[scalability signal]；
          [traction / 量化产出]。
```

**实例**：

> 主导自研端到端 AI 简历定制系统，面向跨行业高频投递场景，多用户架构支持扩展；已在多场景真实投递中迭代验证，单 JD 改写时长大幅缩短。

✓ 系统描述（端到端 AI 简历定制系统）
✓ Target use case（跨行业高频投递）
✓ Scalability signal（多用户架构）
✓ Traction（多场景真实投递 + 改写时长大幅缩短）

---

## 3.5 多 bullet 项目的 hierarchy 设计

当一个项目占 3+ bullets 时（典型如 capstone / 头牌项目 / 长期项目），每条 bullet 必须挂一个独立主轴。bullets 之间不是平行罗列，而是从不同角度组合成完整叙事。

**为什么这条规则重要**：

reviewer 扫到一个长项目时，会下意识找"这个候选人最厉害的点是什么"。如果 4 bullets 全是 "实现 X / 搭建 Y / 实现 Z" 类动词起手的 implementation 描述，reviewer 读完 only knows 候选人完成了多个组件，**不知道候选人做了什么判断**——重心模糊，最终归类为"工程师 / 执行者"而非"工程师 + 产品思考者"。

工程岗判断力 = 动手力并列（§0），所以即使 bullet 起手是动词，bullet 内容必须显化判断信号，否则退化成 §0 表里 AI 产品 PM 岗反模式（动手力压过判断力）的工程岗变体。

**多 bullet hierarchy 推荐主轴序列**：

| Bullets 数 | 主轴序列 |
|---|---|
| 4 bullets | 业务 anchor → 架构判断 → 工程取舍 → 用户面 / 稳定性 |
| 3 bullets | 业务 anchor → 架构判断 → 工程实现 + 用户价值合并 |
| 2 bullets | 业务 anchor → 核心模块 + 关键判断 |

**每个主轴的判断信号关键词**：

| 主轴 | 判断信号关键词 |
|---|---|
| 业务 anchor | "面向 X 场景"、"支持 Y 类扩展"、"已在 N 场景验证"、"覆盖 ... 等差异化方向" |
| 架构判断 | "按 X 而非 Y 切分"、"使 Z 改动可独立迭代"、"降低后续 N 成本"、"与 X 解耦以便 ..." |
| 工程取舍 | "选 X（vs Y）以..."、"接受 X 换 Y"、"trade-off 是 ..."、"... 级而非 ... 级" |
| 用户面 / 稳定性 | "暴露 X 状态以 Y"、"避免 Z 静默降级"、"非营销页 / 可操作工作台"、"失败路径显式可见" |

**反模式（必须避免）**：
- 4 bullets 全部动词起手 + 模块描述 + 技术栈 + 结果（"实现 X 用 Y / 搭建 Z 用 W / 实现 A 用 B"），没有任何 bullet 显化判断维度
- bullet 之间主轴重复（如 bullet 2 和 bullet 3 都在描述模块拆分）
- 详见 §4.6 反模式 + §6 例 4 before/after

---

## 4. 5 个 framing 反模式（必须避免）

### 4.1 "为自己" 个人玩具 framing

❌ "为自己多次跨行业投递的痛点构建..."

**为什么不行**：听起来像 personal toy / 课程作业 / 自嗨项目。工程岗 reviewer 想找的是 "design for scale" mindset 的候选人。

✓ 改：

> "面向跨行业高频投递场景，多用户架构支持扩展"

兼容 dogfooding 现状（你确实是首期用户）+ scalability vision。

### 4.2 "内部机制做卖点" framing

❌ "把'可机器验证的真实性'作为产品的差异化方向..."

**为什么不行**：这是 internal quality control mechanism，**不是用户感知层 differentiation**。reviewer 读到会觉得是在自夸 internal 设计。

✓ 改：直接陈述具体机制 + 用户价值：

> "搭建 Pass 3 真实性核查 verifier，用 LangGraph StateGraph 把生成结果拆为 claim 列表逐条与 ground truth 文件比对，无源 claim 触发 user verify 闭环，确保每条 bullet 可溯源至经历库。"

具象机制（LangGraph StateGraph + claim 列表）+ 用户价值（每条 bullet 可溯源）。

### 4.3 同一系统拆 N 个项目 padding

❌ 把同一个 system 拆成 "Skill 库" + "Agent 编排器" 两个 project 标题，时间都是同一段时间

**为什么不行**：招聘官会发现是同一个 system —— **像 padded resume**，简历诚实度受损。

✓ 改：合并为 1 个 project，用 bullet 标签（如 "Skill 库实现" / "Agent 编排"）区分双重能力。

bullet 内的标签让 reviewer 读 bullet 时立即 get 到 Skill + Agent 双能力，信号同样强。

### 4.4 R-2 红线：fabricate 技术栈

❌ 看到 JD 要求 "pandas / scipy / Dify" 就往 bullet 里塞，但实际代码里没用过

**为什么不行**：违反 R-2（不添加虚假技能）。面试官追问"你的 pandas 怎么用的？"→ 答不出 → 整段失信。

✓ 写之前必须 verify：

1. 读项目 `pyproject.toml` / `requirements.txt` / `package.json` 看实际依赖
2. 关键库 `grep -r "from X" src/` 确认真的 import 过
3. 没真用过的库 **不列**，即使是 JD 明确要求

**典型 fail 案例**：在 AI Agent 项目里塞 "用 pandas 完成 14 场景查询" —— 实际 decision matrix 是 markdown reference 文件，根本不用 pandas。

### 4.5 Bullet 标签全是 architecture 描述

❌ 第 1 个 bullet 起手 "基于 LangGraph + Claude API 设计 5-Agent 串行编排..."

**为什么不行**：全是 "怎么造的"，不是 "它给谁解决什么"。Reviewer 读完会问"OK 你用了 LangGraph，所以呢？"。

✓ 改：bullet 1 业务 anchor（见 §3）+ 后续 bullets 才 dive into 技术细节。

---

### 4.6 多 bullet 全是动作罗列没独立主轴

❌ 4 bullets 全部 "实现 5 个 X 模块" / "搭建 Y verifier" / "实现 Z 工作台" / "实现 A 系统" 类动词起手罗列，每个 bullet 都是模块描述 + 技术栈 + 结果

**为什么不行**：reviewer 读完只 get 到"候选人做了 N 件事"，没 get 到"做了什么判断 / 为什么这样做"。即使每件事都 impressive，组合起来仍是 execution-leaning signal — 跟 §0 表里"AI 产品 PM 岗的判断力 > 动手力"反过来变成了"全是动手没判断"，工程岗简历 reviewer 同样不买账。

**典型 fail 案例**（来自 Resume Optimizer 小红书 #6 投递 v1）：

> - 独立设计并开发端到端 AI 简历定制系统，...self-hosted MVP；已在 10+ 真实投递中验证。
> - **实现** 5 个独立 Skill 模块编排框架（JD 解析 / 能力建模 / ...），每个 Skill 用 Pydantic schema 锁定输入输出 + tenacity 实现 retry / timeout。
> - **搭建** Pass 3 真实性核查 verifier，用 LangGraph StateGraph 把生成结果拆为 claim 列表逐条与 ground truth 比对。
> - **实现** FastAPI 后端 + React 19 / TypeScript / TanStack 前端工作台，通过 LLM health gate + run 状态机 + artifact readiness 三层状态暴露提升可观测性。

bullets 2-4 全部 "实现 X / 搭建 Y / 实现 Z" 同款 framing，全是 implementation 描述，无判断信号。

✓ 改：按 §3.5 表给每个 bullet 挂独立主轴（业务 anchor / 架构判断 / 工程取舍 / 用户面 + 稳定性）；动词起手保留（工程岗格式 §2），但 bullet 内容必须显化判断 — 用"按 X 而非 Y 切分"、"接受 X 换 Y"、"避免 Z 静默降级"等关键词把判断维度暴露给 reviewer。

详细 before/after 见 §6 例 4。

---

## 5. AI 指纹清理（与 `quality-pass.md` Pass 2 协同）

工程岗简历 reviewer 同样会嫌弃 AI-written bullets。常见 AI 指纹：

| 反模式 | 替换 |
|---|---|
| `→` 箭头（JD 解析 → 能力建模 → ...）| 顿号 / "覆盖 X / Y / Z 个阶段" |
| 4+ 项斜杠并列（a / b / c / d / e）| 分组成 ≤3 项，用顿号 |
| "X 而非 Y" 对比定式 | 全篇 ≤1 次；其余正面陈述 |
| "可机器验证 X" 内部机制做卖点 | 直接陈述机制 + 用户价值 |
| "为自己 X 次..." dogfooding 暴露 | "面向 X 场景 + 多用户架构" |
| "双重痛点 / 多元化方案 / 复合工具" 高密度抽象 | 拆开具体陈述 |
| "schema 遵守 / format compliance" 半英文 | "输出格式规范度" 全中文化 |
| "lens / scenarios" 英文专有词 | "岗位类型 / 场景" 中文化 |

---

## 6. 前后对照实例

### 例 1：Bullet 1（业务 anchor）

❌ 工程视角 fail（全是 architecture）：

> 基于 LangGraph + Claude API 设计 5-Agent 串行编排，覆盖 JD 解析、能力建模、gap 诊断、内容生成、真实性核查 5 个阶段，按 Mode L / F 路由不同执行路径；经三轮 Prompt 迭代显著降低幻觉率。

问题：没说**这个 Agent 是给谁解决什么问题**。

✓ 业务 anchor fix：

> 主导自研端到端 AI 简历定制系统，面向跨行业高频投递场景，多用户架构支持扩展；已在多场景真实投递中迭代验证，单 JD 改写时长大幅缩短。

完整 anchor：系统类型 + target use case + scalability + traction。

### 例 2：Bullet 2（模块实现，工程岗角度）

❌ 套 PM 岗 judgment-first 模板：

> 识别求职者跨行业投递三类痛点，假设可机器验证真实性是差异化方向，设计三层架构...

问题：工程岗 reviewer 想看你**会写什么代码**，不是看你**怎么想产品**。

✓ 工程视角 fix（动词起手 + 模块 + 技术 + 量化）：

> 实现 Skill 工具函数集：用 Python 把 JD 解析、能力建模、内容重写、敏感字段过滤等业务逻辑封装为 5 个独立 Skill；每个 Skill 用 Pydantic schema 锁定输入输出、jsonschema 校验、tenacity 实现 retry / timeout 异常处理；配套数百项 pytest 测试。

工程信号完整：实现什么 + 怎么实现 + 技术栈 + 测试。

### 例 3：技术栈处理

❌ Tech stack 散在 bullets：

```
- bullet 2: ...用 Python + pandas 完成...用 scipy 完成...用 LangGraph...
- bullet 3: ...React 19 + TanStack...
```

问题：
- ATS 抓取困难
- reviewer scan 慢
- 还可能有 fabrication（pandas / scipy 真用了吗？）

✓ Tech stack 独立 prefix：

```
技术栈
- 后端：Python · FastAPI · LangGraph · LangChain · Anthropic / OpenAI · Pydantic · SQL · pytest
- 前端：TypeScript · React 19 · TanStack · Tailwind CSS · Vite
- 工程：Docker · Git
```

（Pre-condition：每个 item 都 verified 真的 import 过）

---

### 例 4：多 bullet 项目 hierarchy（4 bullets 头牌项目，配 §3.5 + §4.6）

❌ **罗列式 fail（动词起手 + 模块描述 + 技术栈，4 bullets 同 framing 无独立主轴）**：

> - 独立设计并开发端到端 AI 简历定制系统，面向跨行业高频投递场景，self-hosted 单用户 MVP；已在 10+ 真实投递中验证。
> - 实现 5 个独立 Skill 模块编排框架（JD 解析 / 能力建模 / 缺口诊断 / 内容改写 / 真实性核查），每个 Skill 用 Pydantic schema 锁定输入输出 + tenacity 实现 retry / timeout，配套 pytest 测试。
> - 搭建 Pass 3 真实性核查 verifier，用 LangGraph StateGraph 把生成结果拆为 claim 列表逐条与 ground truth 比对，无源 claim 触发用户 verify 闭环。
> - 实现 FastAPI 后端 + React 19 / TypeScript / TanStack 前端工作台（Inbox / Setup / Run Detail），通过 LLM health gate + run 状态机 + artifact readiness 三层状态暴露提升可观测性。

**问题诊断**：
- bullet 1 有业务 anchor ✓（"跨行业 / MVP / 10+ 验证"）
- bullets 2-4 全部 "实现 / 搭建 / 实现" 同款动词起手 + 模块描述 + 技术栈 + 结果
- 每个 bullet 内 zero 判断信号（只说"做了 X"，没说"为什么这样做 X"）
- reviewer 读完 only knows 候选人完成了 4 件事，重心模糊

✓ **judgment-hierarchy fix（每个 bullet 挂独立主轴 + 显化判断信号）**：

> - **主导**自研端到端 AI 简历定制系统，面向跨行业高频投递场景（候选人 / 客户角色复用），self-hosted MVP 架构**预留多用户扩展接口**；已在 10+ 真实投递中迭代验证，**覆盖战略 / 数据分析 / AI 产品 / 内容运营 / GTM 等差异化方向**，**使一份基础经历可稳定适配多类岗位**。  ← **业务 anchor**
> - **按 JD 解析 / 能力建模 / 缺口诊断 / 内容改写 / 真实性核查 5 个业务阶段（而非按技术层）拆分**独立 Skill 模块，每个 Skill 用 Pydantic schema 锁定输入输出 + tenacity 实现 retry / timeout，**使方法论改动可在不影响其他 Skill 的前提下独立迭代，降低后续场景扩展的工程成本**。  ← **架构判断**
> - 设计 Pass 3 真实性核查机制：用 LangGraph StateGraph 把生成结果拆为 claim 列表逐条与 ground truth 经历库做 **bullet 级（而非整段级）溯源，接受少量 false positive 换全量可验证性**，无源 claim 触发用户 verify 闭环，从机制上约束 LLM 编造经历 / 虚构技能 / 夸大量化数字。  ← **工程取舍**
> - 用 FastAPI + React 19 / TypeScript / TanStack 实现**可操作工作台（Inbox / Setup / Run Detail，非营销页）**，暴露 LLM health gate + run 状态机 + artifact readiness 三层执行状态，**使 LLM 不可用 / PDF toolchain 缺失等失败路径显式可见，避免静默降级**。  ← **用户面 + 稳定性**

每个 bullet 在动词后立即挂判断维度（业务 anchor / 架构判断 / 工程取舍 / 用户面 + 稳定性），4 个 bullets 组合起来 reviewer 一秒读出叙事："这个候选人想清楚 → 做架构决定 → 做工程权衡 → 在意用户面和稳定性"。判断信号关键词参考 §3.5 表（"而非"、"使 ... 可独立迭代"、"接受 X 换 Y"、"避免 ... 静默降级"）。

---

## 7. 场景路由：投不同岗位用不同模板

| 投递岗位 | 用 | 关键差异 |
|---|---|---|
| AI 产品 PM / AI 创新产品 / 智能化产品负责人 | `ai-innovation.md` | judgment-first 6-要素 bullet |
| AI 工程 / Agent 开发 / 数据策略 / ML 工程师 | **本文件** | action-first + 技术栈 prefix |
| 半工半产（小团队 / Startup 不分岗）| 取交集 | bullet 1 业务 anchor + 后续 bullets action-first |

**判断标准**：JD 是否要求"写代码 / Python / 框架 / SQL / @tool / 大模型 API" 等硬技能 → 是 → 工程岗模板（本文件）；JD 偏重"产品规划 / 用户研究 / 设计 / PRD / 跨职能协作" → 产品岗模板（`ai-innovation.md`）。

---

## 8. Failure modes 索引（来自实战）

| 违规类型 | 来源场景 | 修复 |
|---|---|---|
| Bullet 1 全是 architecture，没业务 anchor | 数据策略 AI Agent 简历 v1 | bullet 1 加业务问题 + 量化产出（§3）|
| 同一系统拆 2 个项目 inflate | 数据策略 AI Agent 简历 v1 | 合并为 1 项目 + bullet 标签区分 |
| 塞 pandas / scipy 实际未用 | 数据策略 AI Agent 简历 v2 | verify pyproject.toml + grep imports |
| "为自己..." personal toy framing | NIO / ABB master | "面向 X 场景 + 多用户架构"（§4.1）|
| "可机器验证真实性" 内部机制当卖点 | Resume Optimizer 项目 v3 | 具象机制 + 用户价值（§4.2）|
| AI 高频词（X 而非 Y / 双重痛点 / 复合工具）| 多份草稿 | 拆开正面陈述（§5）|
| Tech stack 散落 bullets 而非 prefix | Resume Optimizer 项目 v3 | 独立 prefix 行分类列（§1）|
| 多 bullet 全是动作罗列，没独立主轴 / 没判断维度 | Resume Optimizer 小红书 #6 投递 v1 | §3.5 hierarchy + §4.6 反模式 + §6 例 4（每个 bullet 挂独立主轴 + 显化判断信号）|

---

## 9. 与其他 reference 的耦合

| 文件 | 协同关系 |
|---|---|
| `scenarios/ai-innovation.md` | 姊妹文件（AI 产品 PM 角度），§7 场景路由表显式分流 |
| `role-lenses/C-product-ops.md` | 本文件归属 lens C（与 ai-innovation 同 lens 的工程岗 sub-scenario）；C-lens 下位 scenarios 表含本文件 |
| `role-lenses/C-product-ops.md` § 0 | "判断力优先 hierarchy" 是产品岗总原则；工程岗判断力 = 动手力并列，本文件是该原则的工程岗变体 / 例外 |
| `general-rules.md` § Bullet 六元素 + Role-specific 元素排序差异 | 本文件是"产品 lens C"行的工程岗补充版 |
| `workflow/quality-pass.md` Pass 1.6 + 2 | English review + AI 味清洗仍适用 |
| `profile-hygiene.md` | R-19 隐私守卫仍适用（任何场景都不能写 PII / 薪酬 / NDA）|

---

## 维护

- 每跑完一个 AI 工程 / Agent 开发岗位投递，将新发现的 framing 反模式或 fabrication failure 追加到 §8 Failure modes 索引
- 每季度梳理 §1 技术栈精简原则，确保 cuts 列表反映最新的"什么是冗余、什么是核心"判断
