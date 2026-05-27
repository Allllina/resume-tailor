> 本文件仅包含差异化内容。通用框架见 scenario-template.md，写法规则见 general-rules.md
> Lens: HC 人力资本 · 简历版本 HC · 详见 `role-lenses/HC-human-capital.md` · 单归属规则见 `workflow/competency-framework.md §2.1`

# People Analytics / HR 数据分析方向简历优化标准

## 岗位画像

People Analytics / HR Analytics 岗位以数据建模与分析方法服务于人才与组织决策。常见于 MNC 全球总部 People Analytics 团队、互联网大厂的 HR 数据中台 / 组织发展部门、HR Tech / SaaS 公司、咨询公司的 People Analytics 业务线。

与 `human-capital.md` 的区别：本方向更偏数据 / 模型 / 可重复 HR 数据产品；human-capital 更偏咨询、组织诊断与战略建议。两者经常 blended（如 "data-driven HR consultant"），运行时在 `scoring_notes` 标注 secondary lens 即可。

与 Lens B 的 `data-analysis.md` 区别：本方向数据对象是**人 / 组织**（员工生命周期、薪酬、敬业度、招聘漏斗、流失），不是用户 / 业务流量。HR 数据有合规、隐私、样本量小的特殊约束，分析方法论需要适配。

## 核心能力评估维度

### 1. HR 数据建模
简历信号：流失预测模型、薪酬公平性建模、招聘漏斗分析、生存分析（Survival Analysis）、人效（productivity per FTE）建模

### 2. 实验与因果推断
简历信号：A/B testing for HR programs、政策效果评估、Difference-in-Differences、Propensity Score Matching、敬业度驱动因子分析

### 3. HR 数据基础设施
简历信号：Workday / SuccessFactors / Oracle HCM 数据抽取、HR 数据仓库、人才数据看板、自动化报表

### 4. 业务转化与高管沟通
简历信号：向 HRBP / Total Rewards / Talent Acquisition / 业务 leader 输出洞察；模型结果 → HR 政策 / 组织决策的闭环

### 5. 隐私与合规意识
简历信号：GDPR、PII、数据脱敏、HR 数据访问分级、跨境数据合规（特别是涉及海外子公司）

## Bullet 写法：方向特定示例

[X] = 搭建的 HR 数据产品 / 模型 / 推动的人才决策，[Y] = 业务规模（FTE / BU / 招聘漏斗规模）+ 量化结果（流失率改善 / 决策速度 / 成本节约），[Z] = 数据方法 + 工具 + 业务推动手段。

### 中文示例
- ✅ "搭建覆盖 5 个事业部 8,000 FTE 的关键人才流失预测模型（XGBoost），AUC 达 0.82，识别出薪酬倒挂与直属经理任期错配两大驱动，推动 HRBP 团队针对 Top 10% 高风险人才执行定向留任，12 个月流失率下降 18%"
- ✅ "设计敬业度驱动因子分析框架，整合 25,000 份年度敬业度调研与绩效 / 流失数据，运用结构方程模型识别出 5 个高杠杆驱动因子，向 CHRO 汇报后纳入 H2 OD 改进 roadmap"
- ✅ "完成集团薪酬公平性诊断（gender pay gap），覆盖 3,200 名员工 12 个职能，运用 OLS 回归 + Oaxaca-Blinder 分解控制岗位 / 司龄变量后定位 4 个职能存在显著差异，推动 Total Rewards 完成定向调薪 1.8M"
- ✅ "搭建招聘漏斗自动化分析体系（Workday + Tableau），覆盖年均 1,500 个招聘需求，将各环节通过率 / 时间成本 / Source 效率指标实时呈现，推动 TA 团队优化最大流失环节，平均招聘周期从 52 天缩短至 38 天"

### 英文示例
- ✅ "Built a regrettable-attrition prediction model (XGBoost, AUC 0.82) covering 8,000 FTE across 5 business units; identified compensation lag and manager-tenure mismatch as primary drivers; partnered with HRBPs to target the top 10% at-risk population, reducing 12-month attrition by 18%"
- ✅ "Designed engagement-driver analysis framework integrating 25,000 annual survey responses with performance and attrition data; used SEM to identify 5 high-leverage drivers; recommendations adopted by CHRO into H2 OD roadmap"

### 常见错误
- ❌ "做了 HR 数据分析" → 分析了什么对象？什么方法？产出了什么？
- ❌ "搭建了 HR 数据看板" → 覆盖什么数据？谁用？推动了什么决策？
- ❌ "运用 Python 处理 HR 数据" → 工具不是成果；写你解决了什么 HR 业务问题
- ❌ 用业务侧（用户 / GMV）的指标作 HR 分析的产出 → 走错 lens 了，这是 Lens B 不是 Lens HC

## 关键术语表

### HR 数据对象
员工生命周期、Hire-to-Retire、Workforce Demographics、Headcount、FTE、Span of Control、Layer Depth、Tenure、Promotion Velocity、Internal Mobility、招聘漏斗、Funnel Conversion、Time-to-Fill、Time-to-Hire、Source of Hire、Quality of Hire、敬业度（Engagement）、Pulse、eNPS、Stay / Exit Interview

### 分析方法
流失预测（Attrition Prediction）、生存分析（Survival Analysis）、Cox Regression、回归分析、OLS、Logistic Regression、聚类分析、因子分析、结构方程模型 SEM、A/B Testing for HR、Difference-in-Differences、Propensity Score Matching、Oaxaca-Blinder Decomposition、文本挖掘（Exit Interview NLP）

### 工具与平台
Workday、SAP SuccessFactors、Oracle HCM、ADP、Mercer Mettl、Visier、One Model、Tableau、Power BI、Python（Pandas / scikit-learn / lifelines）、R、SQL

### 输出物
人才数据看板、流失预警 / 高潜识别仪表盘、薪酬 benchmarking 报告、组织效能 review、敬业度 deep-dive 报告

### 隐私 / 合规
PII、GDPR、HIPAA（如涉及医疗数据）、数据脱敏、访问分级、Audit Trail、Data Residency、跨境数据合规

## 经历包装策略

### 核心思路
"HR 数据建模 + 业务转化 + 合规意识" 三位一体。要避免读起来像 ①纯 HR 行政（缺数据深度），②纯 data analyst（不懂 HR 业务），③纯 IT / data engineer（缺业务转化）。

### Mercer / Desay SV 经历的核心钩子
- **Mercer 经历** — 强调具体的 people analytics 项目（薪酬 benchmarking 数据库 / 流失分析 / engagement 调研 / 组织效能数据），用 scope（员工 / 岗位 / 行业 / FTE）+ 方法（统计模型 / 工具）+ 结果（被客户采纳 / 决策影响）
- **Desay SV 经历** — 海外子公司组织数据 / 跨境 HR 数据 / 人效分析；强调跨地区数据整合的合规与方法论难度

### 非 HR 数据经历的桥接表

| 原始经历 | People Analytics 方向表述 |
|---|---|
| 用户调研（Ipsos） | 调研方法论 → employee survey / engagement / pulse 设计；样本设计与定性 + 定量结合直接迁移 |
| 业务数据分析 | 把分析对象从用户 / 流量切到员工 / 组织；强调你能 connect 业务指标与人才指标 |
| 战略咨询（Kearney） | 强调商业判断 + 结构化拆解 + 高管沟通；说明你能把数据洞察翻译成可执行 HR 决策 |
| 工程 / 数据建模项目 | 选择有 HR 类应用语境的项目（流失预测 / 文本挖掘 / 推荐算法迁移到内部人才匹配）|

### 加分项
- 有真实跨年度 HR 数据建模经历（不是只有 academic dataset）
- 有 GDPR / 隐私合规处理经验
- 有 Workday / SuccessFactors 等 HR 系统数据抽取经验
- 有向 CHRO / Total Rewards / TA Lead 直接 present 的经历
- 模型 / 分析的洞察被翻译成 HR 政策落地（不只是出报告）
