# BlueWave SaaS（蓝浪 SaaS）

> 角色：Data Analytics Intern
> 候选人：李雯 Li Wen
> 时间：2024.06 – 2024.09
> 能力标签：A/B test 设计, 指标体系, 异动归因, SQL pipeline, dashboard 搭建, 用户分群

---

## 项目 1｜核心订阅漏斗 A/B 测试与定价实验

> 为公司中端订阅产品（19/29/49 三档）设计并执行 A/B 测试，核心回答"19 档作为 anchor 是否提升 29 档转化"。实验在产品定价页投放，覆盖 1.2M users（北美 + 欧洲），周期 4 周。

### 第一层：项目快照
- 项目类型：自有产品 A/B 实验（4 周），与 PM + Eng 三方协作
- 业务场景：定价页转化是 funnel 的卡点；29 档（main SKU）转化率是季度 OKR 唯一硬指标
- 数据规模：1.2M users 进入实验，~24M page views，~720K 决策事件
- 主要输出：实验设计文档、SQL pipeline、Tableau dashboard、最终读数 readout deck
- 本人角色：实验唯一 analytics owner，端到端负责设计 → 监控 → 分析 → 读数

### 第二层：业务闭环
- 设计并执行 A/B 测试，覆盖 1.2M users，按用户 cohort 50:50 分流（含老用户子分层）
- 在 Snowflake 上搭建 SQL pipeline，每日凌晨自动 ETL 实验事件，沉淀到 8 张分析表
- 在 Tableau 搭建实时监控 dashboard（4 张图），覆盖 conversion rate / ARPU / refund rate / NPS 4 个核心指标
- 第 4 周读数：treatment 组 29 档转化率 +8% lift（p<0.05），treatment 组 ARPU +5%
- 异动归因：发现欧洲市场 lift 显著（+12%），北美仅 +3%；定位为 anchor 价格在欧洲市场的购买力差异更敏感
- 决策建议：欧洲市场全量推 anchor 定价，北美市场暂缓 + 设计第二轮迭代

### 第三层：深挖问答
- **样本量是怎么算的？** 用 power = 0.8, alpha = 0.05, 期望 lift = 5%，反推每组需要 ~520K 用户；按 50:50 分流 → 总样本 1.04M，留 buffer 后定 1.2M
- **怎么处理 novelty effect？** 实验前两周 lift 偏高（+11%），第 3-4 周收敛到 +8%；最终读数取后两周稳态值
- **欧洲 / 北美差异为什么显著？** 在分群层做 interaction analysis，发现欧洲用户对 19 档的"心理 anchor"敏感度更高（购买力差 + 货币 perception），北美用户更看 ROI 总值
- **怎么 sanity check 数据 pipeline？** 实验前用历史数据 backfill 一遍 SQL pipeline，校验 ARPU / conversion rate 与 production dashboard 数字 match（误差 < 0.5%）

### 能力标签
A/B 实验设计（power calculation / 分流策略 / novelty handling），SQL pipeline 搭建（Snowflake），dashboard 搭建（Tableau），异动归因（segment-level interaction analysis），统计推断（p-value / confidence interval）

### 工具栈
SQL（Snowflake / dbt）, Python（pandas / scipy.stats / statsmodels）, Tableau, Mode Analytics, Git

---

## 项目 2｜用户分群体系搭建与 dashboard 落地

> 为产品团队搭建覆盖全产品的用户分群体系，回答"哪些用户最值得追加触达 / 召回"。沉淀为 6 个核心分群 + 3 张 Tableau dashboard。

### 第一层：项目快照
- 项目类型：体系化分析项目（6 周），与 PM + Marketing 协作
- 业务场景：Marketing 团队投放预算无规划，分群粗（仅按 plan tier 切），需要更细的用户画像支撑触达策略
- 主要输出：6 个核心分群定义文档、SQL 实现、3 张 Tableau dashboard（覆盖 Marketing / PM / Exec 3 个 audience）
- 本人角色：体系设计 + SQL 实现 + dashboard 搭建端到端负责

### 第二层：业务闭环
- 定义分群维度：按 RFM（recency / frequency / monetary）+ 产品行为（feature usage breadth / depth）+ 生命周期（new / active / dormant / churned）三轴
- 6 个核心分群：power user / regular user / dormant explorer / dormant power / new active / new churning
- SQL 实现：在 Snowflake 上实现 6 个 logic gate 的 dbt model，每日刷新；输出宽表覆盖全公司 ~1.2M users
- Tableau dashboard：分群规模与流转 dashboard、分群行为画像 dashboard、分群营销 ROI dashboard
- 落地效果：Marketing 团队基于"dormant power"分群设计召回 campaign，召回率从 baseline 2.1% 提升到 4.7%

### 第三层：深挖问答
- **为什么用 RFM 而不是 ML 聚类？** RFM 是业务侧可解释的；ML 聚类（k-means）虽然 unsupervised 漂亮但落地难（PM / Marketing 看不懂）。RFM 在 explainability 与 actionability 上更适合
- **怎么定义"power user"门槛？** 用 frequency 月活 > 20 天 + monetary 月支出 > $49 + breadth 使用 ≥ 5 个核心 feature；门槛取 P75 校准
- **怎么验证分群稳定性？** 跑 4 周历史 backfill，看每个用户在分群之间的流转矩阵；power user 月度稳定率 78%，dormant 86%，认为体系可用
- **怎么处理分群定义随时间漂移？** 在 dashboard 加"门槛监控页"，每月自动重算 P75 / P25 等关键分位数；超过 ±15% drift 触发 review

### 能力标签
用户分群体系设计（RFM / 行为 / 生命周期三轴），dbt 数据建模，Tableau dashboard 设计，stakeholder 协作（Marketing / PM / Exec），分群稳定性验证

### 工具栈
SQL（Snowflake / dbt）, Python（pandas / scikit-learn for sanity check）, Tableau, Notion（文档协作）

---

## 项目 3｜异常检测与归因排查（Q3 留存异动）

> Q3 期间观察到周留存 W2 突降 4.2pp，由我主导异常检测与归因排查，2 周内交付归因结论。

### 第一层：项目快照
- 项目类型：响应式异常归因项目（2 周）
- 业务场景：Q3 第 7 周开始，新用户 W2 留存从基线 38% 跌到 33.8%；exec 要求 2 周内给归因
- 主要输出：归因结论（4 个 root cause + 1 个干扰因素）、修复 backlog 排序、week-over-week 监控 dashboard
- 本人角色：归因主导，与 PM / Eng / Marketing 三方协作

### 第二层：业务闭环
- 定义异常：W2 留存周序列做 z-score，连续 2 周 |z| > 2 触发深入排查
- 拆维度：按 channel / OS / region / cohort / feature usage 五维度切片
- 归因结论：Marketing 渠道 X 引入 cohort 留存差（贡献 1.8pp）+ Android 14 升级触发关键 feature crash（贡献 1.5pp）+ 价格页 bug 误导新用户（贡献 0.7pp）+ seasonal noise（0.2pp 干扰）
- 处置建议：渠道 X 暂停（M）、Android 14 fix 升级（Eng P0）、价格页 fix（Eng P1）；2 周后留存恢复到 37.6%
- 沉淀：归因 playbook 文档 + 5 张监控 dashboard（按维度 dimension cut）

### 第三层：深挖问答
- **怎么排除 seasonal noise？** 拿 12 个月历史同期周留存做 baseline，计算季节性调整后的"真实异动" 4.0pp
- **为什么不直接相加 4 个 root cause（1.8 + 1.5 + 0.7）？** 维度之间有 overlap（如渠道 X 也以 Android 为主）；用 marginal contribution 分解，按 Shapley 值近似分配，最终加和 = 实际异动 4.0pp
- **怎么 sanity check 渠道 X 的 1.8pp？** A/A 模拟：把渠道 X cohort 移除，重算总体留存，看是否回升到 baseline-1.5pp（与归因匹配）；结果 match

### 能力标签
异常检测（z-score / control chart），归因分解（dimension cutting / Shapley 近似），跨维度 interaction 分析，stakeholder 危机沟通

### 工具栈
SQL（Snowflake）, Python（pandas / numpy）, Tableau, Looker（exec dashboard）

---

## 整体反馈（manager 季度评价）

- "L 同学是入职以来最快上手 SQL + 实验设计的 intern，价格 anchor 的 readout 是季度被引用最多的 readout"
- "归因 playbook 已沉淀为 team standard，未来新人 onboard 直接用"
- "下一步建议补 causal inference (DID / synthetic control) 训练，扩展归因方法论"
