# Lens A — 战略 / 研究 / 咨询（Strategy / Research / Consulting）

**对应简历版本：** A
**对应 role_family：** `A_strategy_research`
**下位 scenarios：** `consulting.md` / `growth-strategy.md` / `product-strategy.md` / `business-analysis.md`

---

## 1. What recruiters screen for

招聘人在筛"能不能走进一个房间，面对资深 executive，把没见过的问题 frame 成可执行 recommendation"。底层问题：**结构化思维 + 商业判断 + 综合研究 + 推动决策**。

---

## 2. Prioritize（重点突出）

- **结构化问题解决** — 把 ambiguous 问题拆成可执行框架的证据。case competition / 战略项目 / 真实决策中应用的分析框架
- **商业判断** — 不是 awareness，是 applied judgment。business model / revenue driver / 市场动态 / 竞争定位
- **研究与综合** — 多源信息收集 + pattern 识别 + 形成 coherent view。市场 sizing / 竞争分析 / 行业研究
- **Stakeholder management** — 向资深者 present / influence / advise。Client interaction / board presentation / executive briefing
- **Recommendation 质量** — 候选人的工作导向决策。不只是 "analyzed X" 而是 "recommended Y, which was adopted because Z"
- **假设驱动工作风格** — "we hypothesized X, tested via Y, concluded Z" 是咨询 native 思维信号

---

## 3. De-emphasize（弱化）

- 没业务意义的过度技术细节（model architecture 没有 business outcome）
- 纯执行 bullet 没分析 / 战略信号
- 像 data engineering 简历的 tool-heavy 描述
- 纯 ops 工作没判断 / recommendation 成分

---

## 4. Language signals

| 信号 | NA 动词 | 内地动词 |
|---|---|---|
| 强 | led / structured / synthesized / recommended / advised / identified / evaluated / quantified | 主导 / 牵头 / 拆解 / 综合 / 提炼 / 建议 / 评估 / 量化 |
| 弱 | assisted / helped / supported / participated / contributed | 参与 / 协助 / 帮助 / 配合 |

---

## 5. Bullet pattern

**[Action] + [战略 / 分析语境] + [方法] + [recommendation / 洞察] + [业务结果]**

### NA 示例
> "Led competitive landscape analysis across 12 Southeast Asian markets, synthesizing primary interviews and secondary data into a market-entry recommendation adopted by the regional leadership team, informing a $15M investment decision."

### 内地示例
> "主导 8 家头部车企新能源转型路径研究，结合 30+ 高管访谈与公开财报数据搭建对标矩阵，产出战略建议被客户高管层采纳，直接影响 2026 年产品组合决策。"

---

## 6. 与 scenarios 的下位关系

本 lens 是上位族，**单归属**以下 scenarios（与 `competency-framework.md §2.1` MECE 铁律一致）：

| Scenario | 主要适用 |
|---|---|
| `scenarios/consulting.md` | 显性 strategy / consulting 角色（咨询公司岗 / 内部战略部门） |
| `scenarios/business-analysis.md` | 业务分析师（含跨学科分析、TAM/SAM、商业建模、向高层 recommend） |
| `scenarios/growth-strategy.md` | 增长战略 |
| `scenarios/product-strategy.md` | 产品战略 |

边界岗位（"data-driven strategy" / "growth ops" / 偏数据的 business analyst 等）：scenario 文件**仍由本 lens 加载**，secondary lens 标注由运行时输出 `scoring_notes`，不在本文件分流。详见 `competency-framework.md §2.2` Blended Lens 处理规则。

---

## 7. 候选人证据钩子（与 experience-bank/raw 的映射建议）

参考 `assets/profile/user-profile.md` 与 `assets/experience-bank/raw/`：

- **Kearney（01-kearney.md）** — 核心硬证据：consulting native，框架应用，client-facing
- **Ipsos（02-ipsos.md）** — 研究综合，多源数据 → 洞察 → 客户 recommendation
- **Desay SV（03-desaysv.md）** — 战略项目（如果与新能源 / 出海 / 海外子公司治理相关）
- **SDIC（05-sdic.md）** — 政策 / 产业研究角度

具体 bullet 选择由 `resume-rewrite-engine` 根据 JD 与 candidate audit 决定。

---

## 8. 与 target_market 的交互

NA：动词 + 量化 + 单句 punchy；优先讲 impact，再补方法。
内地：避免方法论堆砌（"通过结构化桌面研究与多维度竞争基准对标..."）→ 用具体事实替代方法论名词；"通过研究 5 家企业 + 对标 7 个维度，发现 X 结论"。

---

## 9. Anti-narrative（避免读起来像）

- "Generalist business student exploring options"
- "Project coordinator who scheduled meetings"
- "Researcher who compiled data without forming views"
