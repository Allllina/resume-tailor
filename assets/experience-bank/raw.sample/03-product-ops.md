# Beta Products（贝塔智造）

> 角色：Product Operations Intern (AI focus)
> 候选人：王宇 Wang Yu
> 时间：2024.01 – 2024.05
> 能力标签：prompt engineering, RAG 内容工作流, LangChain agent 原型, 标签体系, AI 工具评估, 内部赋能

---

## 项目 1｜内部内容工作流的 prompt engineering pipeline 优化

> 公司内容团队（运营 / 市场 / 客服 4 个内部团队）每天产出大量营销文案 + 客服话术 + 行业研究稿，原工作流人工编辑耗时长、风格漂移大。我作为 product ops intern 牵头设计 prompt engineering pipeline，把 60% 通用环节自动化，30% cycle time reduction 落地。

### 第一层：项目快照
- 项目类型：内部工具 + 流程优化（10 周）
- 业务场景：4 个内部团队周均输出 ~200 篇内容，每篇平均 cycle time 4 小时（含 review）；目标把 cycle time 压到 2.8 小时
- 数据规模：累计处理 ~600 篇内容做 prompt 微调与评测
- 主要输出：5 个标准 prompt 模板（按内容类型）+ 内部 prompt library + Notion 工作流文档 + 内部分享会
- 本人角色：pipeline owner，端到端负责设计 / 落地 / 培训

### 第二层：业务闭环
- 主导 prompt engineering pipeline 优化，覆盖 4 个内部团队，节省 30% cycle time
- 设计 5 个标准 prompt 模板（marketing copy / customer reply / industry digest / weekly recap / FAQ），按"角色 + 任务 + 风格 + 约束 + few-shot"五段式结构化
- 在 Notion 沉淀 prompt library，按场景标签 + 评测分数 + 使用频次三维索引；累计 38 条 production prompt
- 自建评测 rubric（5 轴：相关性 / 准确性 / 风格一致性 / 长度合规 / 安全合规），人工标注 200 条 + 自动化 200 条
- 落地效果：4 个团队 cycle time 从 4 小时 → 2.8 小时（-30%），内容主管 review pass rate 从 65% → 84%
- 内部分享会 2 场，覆盖 4 个团队 ~30 人；后续 prompt library 已成为新人 onboard 必修

### 第三层：深挖问答
- **prompt 模板为什么不用全 few-shot？** few-shot 的好处是风格 transfer，但 token 成本高 + 难维护；混合方案：风格强约束（marketing）用 5-shot，弱约束（FAQ）用 0-shot + system prompt 抑制
- **怎么 measure cycle time reduction？** 拆 cycle 为 5 段（构思 / 一稿 / review / 二改 / 终稿），按段记录历史样本 + 新工作流样本各 50 条，配对 t-test 验证显著（p<0.01）
- **怎么处理 LLM 风格漂移？** 评测 rubric 的"风格一致性"轴 quarterly 重打分；任何模板 30 天内 drop > 10% 触发 retro + retune
- **怎么 onboard 不熟 LLM 的同事？** 培训分两层：先教"读 prompt 模板就能用"（不需要懂 prompt engineering），后教"会改模板"（懂结构）

### 能力标签
prompt engineering（结构化模板 / 分场景策略 / few-shot vs 0-shot），内部工具落地（Notion 工作流），评测 rubric 设计，跨团队 enablement，AI 工具评估

### 工具栈
ChatGPT API, Claude API, LangChain（部分高级用法）, Notion（工作流 + library 沉淀）, Excel（评测打分）, Slack（培训沟通）

---

## 项目 2｜RAG-based 内容工作流落地

> 把内容团队的"行业研究稿"工作流升级为 RAG-based 系统，让 LLM 在写 weekly digest 时自动检索内部知识库 + 公开 source。8 周。

### 第一层：项目快照
- 项目类型：RAG 工作流 PoC + 落地（8 周）
- 业务场景：行业研究稿原本人工查 30+ source 每篇 ~3 小时，且容易漏 / 重复 / 时效失准
- 数据规模：内部知识库 ~3,200 篇文档（PDF / Notion / Google Doc），公开 source 接 RSS + 抓取 ~12 个站点
- 主要输出：RAG pipeline（chunking / embedding / retrieval / generation 全链路）、weekly digest 自动化 demo、生产化文档
- 本人角色：原型设计 + 落地，与 ML eng 1 人 partner

### 第二层：业务闭环
- RAG 内容工作流落地，节省 30% cycle time（行业研究稿从 3 小时 → 2.1 小时）
- 设计 chunking 策略：800 字符 chunk + 200 字符 overlap；针对 PDF 与 markdown 分别 fine-tune 切片规则
- 选型 embedding model：对比 OpenAI ada-002 / BGE-base-zh / multilingual-e5-large，按 retrieval P@5 选 BGE-base-zh
- 检索 + reranker 双层：top-50 vector retrieval → cross-encoder rerank 取 top-8；P@5 从 0.62 → 0.81
- generation 层用 system prompt 约束"必须在 retrieved chunks 内"，hallucination rate 从 baseline 11% → 3.5%
- 落地后内容主管月度抽查通过率 84%；reject case 主要是"reranker 漏召"而非"幻觉"

### 第三层：深挖问答
- **为什么不用 GPT-4 直接写而要 RAG？** 行业研究稿强依赖时效（policy / 财报 / 行业事件），LLM 的训练数据 cutoff 不够新；RAG 把"事实层"外置才能保证时效
- **怎么 measure hallucination rate？** 抽 50 条生成稿，人工打"是否每个 fact-bearing claim 都能在 retrieved chunks 里找到"；rate = 找不到 source 的 claim 占比
- **chunking 800 字符是怎么定的？** 在 50 条 query 上 grid search 200 / 400 / 800 / 1600 字符 + 0% / 25% / 50% overlap；800 + 25% overlap 在 P@5 与生成质量综合最优
- **RAG 失败 case 主要是什么？** 内部知识库的版本管理弱（同一份文档存 3 版），retriever 召回最旧版；后续给文档加 last_updated metadata + retrieval 时按时间衰减加权

### 能力标签
RAG 系统设计（chunking / embedding / retrieval / reranker / generation 五层），embedding model 选型评测，prompt engineering（grounding 约束），hallucination 评估方法

### 工具栈
LangChain, OpenAI API, BGE embedding, Pinecone（vector DB）, Cohere reranker, Python（pandas / numpy）

---

## 项目 3｜LangChain agent 原型探索

> 探索性项目，4 周；评估 LangChain agent 在客服场景的可行性，回答"是否值得做生产化"。

### 第一层：项目快照
- 项目类型：技术探索（4 周）
- 业务场景：客服场景目前用 RAG + 单轮 LLM；想看 multi-step agent（搜索 / 查订单 / 写回复）能否提升 resolution rate
- 主要输出：3 个 agent 原型 demo + 评估报告（go / no-go decision support）
- 本人角色：原型主创，与 PM 1 人讨论场景

### 第二层：业务闭环
- 搭建 3 个 agent 原型：ReAct-style 搜索 + 单工具 / Plan-and-execute / 多 agent 协作
- 接 4 个 mock tool（订单查询 / 物流查询 / 退款规则 / 知识库 search）
- 在 30 条真实客服 case 上跑 evaluation，agent vs RAG baseline
- 评估结果：agent resolution rate 47% vs RAG 41%（+6pp），但 latency 从 1.2s → 4.8s，cost 从 $0.003 → $0.018 per query
- 决策建议：暂不生产化（成本 / 延迟超 product 阈值）；等 cheaper / faster model 出来再评估
- 沉淀：agent 评测框架 + 30 条 case bank + 3 份 demo 视频

### 第三层：深挖问答
- **为什么是 ReAct + Plan-and-execute + Multi-agent 三种？** 覆盖从轻到重的 architecture spectrum；ReAct 是 baseline，Plan-and-execute 加规划，Multi-agent 加分工
- **agent 失败 case 是什么？** 主要两类：tool 调用错（参数 hallucinate）+ 逻辑卡死（agent 反复调同 tool）；后者通过加 max_iterations + reflect node 可缓解
- **30 条 case 是怎么选的？** 客服历史日志按 difficulty 分 5 档，每档 6 条；保证覆盖 simple lookup / multi-step reasoning / edge case 三类
- **怎么 communicate "no-go" 给 stakeholder？** 强调"暂不生产化但保留方法论"——评测框架 + case bank 已经入库，cheaper model 出来后 day 1 重跑评估

### 能力标签
LangChain agent 设计（ReAct / Plan-and-execute / Multi-agent），agent 评估方法（resolution rate / latency / cost 三维），技术 go-no-go decision support

### 工具栈
LangChain, OpenAI GPT-4 / Claude 3, Python, Notion（评估报告）

---

## 整体反馈（manager 季度评价）

- "W 同学是 product ops 团队第一个把 AI 工具沉淀成 library 的 intern，4 个内部团队的赋能效果显著"
- "RAG 落地是这一期最大产出，hallucination 控制方法已成为内部 reference"
- "下一步建议补 product analytics 训练（北极星指标 / funnel 分析），从 ops 视角往 product strategy 视角延伸"
