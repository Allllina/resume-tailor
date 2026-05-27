# Lens B — 数据 / 分析（Data / Analytics）

**对应简历版本：** B
**对应 role_family：** `B_data_analytics`
**下位 scenarios：** `data-analysis.md` / `user-insights.md` / `public-opinion.md`

---

## 1. What recruiters screen for

招聘人在筛"能不能独立用数据回答业务问题，并解释答案为什么重要"。底层：**技术流畅 + metrics 思维 + 数据→洞察转化 + 方法论严谨**。

---

## 2. Prioritize

- **SQL / Python / 分析工具熟练** — 具名工具 + 实质使用证据（不是 "familiar with"）。写过的 query / pipeline / script / dashboard
- **Metrics 思维** — 定义 / 跟踪 / 改进指标的证据。owned KPI / 搭过的 dashboard / 设计过的测量框架
- **实验与建模** — A/B testing / forecasting / regression / clustering 等应用到真实问题
- **数据→洞察转化** — 关键 differentiator。不是 "ran analysis" 而是 "identified that X was driving Y, which led the team to change Z"
- **可衡量结果** — 百分比改进 / 成本节约 / 效率提升 / 营收 impact 绑定到分析工作
- **数据 infrastructure 意识** — pipeline / warehouse / ETL 理解（senior 角色）

---

## 3. De-emphasize

- 没分析深度或具名方法的"研究"
- presentation-heavy 但背后没 substantive data work
- business strategy 语言但没 technical 接地
- generic "analysis" 没说明分析了什么 / 怎么做 / 结果是什么

---

## 4. Language signals

| 信号 | NA 动词 | 内地动词 |
|---|---|---|
| 强 | built / automated / modeled / measured / optimized / identified (via data) / reduced / improved | 搭建 / 自动化 / 建模 / 量化 / 优化 / 挖掘 / 归因 / 提升 |
| 弱 | researched (无方法) / presented (无分析内容) / managed (data 无 specifics) | 处理 / 整理 / 跟进 / 看数据 |

---

## 5. Bullet pattern

**[Action] + [数据方法 / 工具] + [回答的业务问题] + [发现] + [可衡量 impact]**

### NA 示例
> "Built an automated Python pipeline processing 2M+ daily user events, identifying a 23% drop-off in onboarding flow that led to a UX redesign increasing 7-day retention by 8%."

### 内地示例
> "搭建覆盖 200 万 DAU 的用户行为分析体系，基于 Python 自动化日报与漏斗分析定位注册流程 23% 流失节点，推动产品侧完成 5 项交互优化，7 日留存提升 8%。"

---

## 6. 与 scenarios 的下位关系

本 lens 单归属以下 scenarios（与 `competency-framework.md §2.1` MECE 铁律一致）：

| Scenario | 主要适用 |
|---|---|
| `scenarios/data-analysis.md` | 通用 data analyst（数据深度为主） |
| `scenarios/user-insights.md` | 用户研究 / 行为分析（research 与定性 + 定量结合） |
| `scenarios/public-opinion.md` | 舆情分析 / 内容数据 |

边界岗位：偏数据的 business analyst 仍由 Lens A 的 `business-analysis.md` 加载，secondary lens B 标注在运行时 `scoring_notes`；偏底层 pipeline / 分析的 data ops 仍由 Lens C 的 `data-ops.md` 加载，secondary lens B 同理。详见 `competency-framework.md §2.2`。

---

## 7. 候选人证据钩子

- **Mercer（04-mercer.md）** — people analytics / org diagnostics 数据深度
- **Ipsos（02-ipsos.md）** — 用户研究 / 调研方法论 / 数据综合
- **Desay SV（03-desaysv.md）** — 业务数据分析（出海 / 海外子公司绩效数据）
- **Projects（06-projects.md）** — Python / SQL / Tableau 应用项目

---

## 8. 与 target_market 的交互

NA：tool name + impact metric。"Built X using Y, achieving Z."
内地：先讲 scope（DAU / GMV / 业务线），再讲方法（Python / SQL），最后量化业务指标。避免英文工具名独占（"用 Mixpanel" → "基于 Mixpanel / 神策 等行为分析平台"）。

---

## 9. Anti-narrative

- "Data enthusiast with Python and SQL skills"
- "Analyst who runs reports without forming views"
- "Tech person trying to do business work"
