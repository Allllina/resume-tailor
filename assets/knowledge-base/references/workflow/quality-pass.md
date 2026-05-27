# 三步质量 Pass（逐段优化后执行）

> 参考来源：Resume-Matcher 开源项目的多 Pass 流水线思路，结合本 skill 的实际需求改造。
> 核心理念：**注入→清洗→验证**，三步分离，每步只做一件事。

---

## Pass 1：关键词 Gap 注入

### 目的
确保 JD 中的核心关键词在简历中出现，提升 ATS 通过率。

### 关键词架构来源
关键词清单按 `workflow/keyword-extraction.md` 的 5-tier 架构（Tier 1 核心角色词 / Tier 2 capability / Tier 3 工具方法 / Tier 4 动词 / Tier 5 语义等价词）从 JD 拆解输出。Frequency × Placement 综合优先级也来自该文件。

### 方法
1. 从 Step 3 的 JD 拆解 + `keyword-extraction.md §2-3` 输出关键词清单（按 Tier 分组，标注高优）
2. 逐条扫描优化后的简历全文，使用 **word-boundary 精确匹配**（"python" 不匹配 "pythonic"，"AI" 不匹配 "MAIL"）
3. 输出关键词命中表：

| 关键词 | Tier | 是否命中 | 出现位置 |
|--------|------|---------|---------|
| market sizing | T2 | ✅ | Ipsos bullet 1 |
| competitive analysis | T2 | ✅ | Kearney bullet 2 |
| SQL | T3 | ❌ | — |

4. 对未命中的关键词，判断：
   - **用户确实有这个技能/经历** → 在最相关的 bullet 或 Skills 栏自然注入
   - **用户没有这个技能** → 不注入，标记为不可弥补 gap

### 注入规则
- 放置策略按 `keyword-extraction.md §4`：Tier 1 → headline / summary；Tier 2 → 经历 bullet；Tier 3 → skills section + bullet；Tier 4 → 开 bullet 动词
- 关键词必须融入语境，不能生硬堆砌（❌ "Proficient in SQL, Python, R, Tableau, Power BI, Excel"）
- 优先注入到已有相关内容的 bullet，而非凭空新增 bullet
- Skills 栏的关键词按 JD 出现顺序排列（JD 先提的放前面）

### Credibility Test（与 `keyword-extraction.md §7` 一致）
每个插入的关键词都自问："面试官就这个关键词追问 2 分钟，候选人能 credibly 答出吗？"不能 → 移除或弱化（如 bullet 中的 "Built Tableau dashboards" 降为 skills section 的 "Exposure to Tableau"）。

---

## Pass 1.5：中文可读性检查（仅中文简历执行）

### 目的
确保中文简历的措辞在中文语境下自然易懂，避免英文直译、翻译腔、或业务方无法直观理解的表述。

### 检查方式
逐条 bullet 自问：**如果一个不懂英文的业务面试官读到这句话，能否立即理解在说什么？** 如果需要"翻译"才能理解，就必须改。

### 常见问题类型

| 问题 | 示例 | 修正 |
|------|------|------|
| 英文概念直译 | 技术采用曲线评估 | 技术成熟度评估 |
| 翻译腔长句 | 通过对业务需求和媒体渠道的了解制定系统和产品优化策略 | 基于业务需求和渠道特点制定优化策略 |
| 生造四字词 | 价值量提升逻辑 | 附加值增长空间 |
| 堆砌英文缩写 | 完成TAM/SAM/SOM测算 | 完成市场规模测算（总量/可服务/可获取） |

### 规则
- 英文术语在中文简历中仅保留业界通用缩写（如ROI、AB测试、Python、SQL），不通用的一律翻译为中文
- 如果一个表述需要读两遍才能理解，就换一种说法
- 咨询术语可以保留（如"对标"、"赛道"、"打法"），但学术翻译腔必须消除

---

## Pass 1.6：英文语言审查（仅英文 / 双语简历执行）

### 目的
对称于 Pass 1.5，专门审查英文 bullet 在 native English / 国际化招聘语境下的自然度，包括：brand-name vs generic、直译腔、AI 味、动词重复、CN→EN 翻译精度。

### 检查依据
完整规则见 `english-language-review.md`，本节为概览：

| 检查维度 | 说明 |
|---|---|
| §1.1 Brand-name → generic | bullet 叙述里 Excel → spreadsheet, PowerPoint → deck, Slack → messaging tool；Skills 行保留品牌名（ATS 关键词）|
| §1.2 直译腔 | grep `make use of / in order to / play an important role in / to a large extent` 等 LLM 易输出的中文直译模式 |
| §1.3 AI-flavor 英文 | spearheaded / leveraged / robust / comprehensive / actionable insights 等 cliché；除非 JD 原文用过 |
| §1.4 动词重复 | 同一动词最多 2 次（Owned / Led / Designed / Built / Contributed 等）|
| §1.5 翻译精度 | 中文经历的 EN 翻译必须 cite `translation-glossary.md` canonical 选择 |

### 规则
- bullet 流畅度 vs 原意精度冲突 → **原意精度优先**（保留量化范围 / 所有权强度 / 行业术语具体性）
- AI 高频词若 JD 原文用过 → 保留不替换
- 翻译表（`translation-glossary.md`）若缺某术语 → 触发 user 入表 prompt，确认后 append

### 与 Pass 2 的边界
- Pass 1.6 = **英文专项**（中文经历翻译为英文时的语言审查）
- Pass 2 = **双语 AI 味**（同时覆盖中英 AI 味，含中文俗语 / 网络词 / LLM 自造词）
- Pass 1.6 跑在 Pass 2 之前，先解决英文专项问题，Pass 2 再做 generic AI flavor sweep

---

## Pass 2：AI 味清洗

### 目的
移除 LLM 生成时容易产生的过度修饰词和空洞表达，使简历读起来像人写的。

### AI 味词汇替换表

| AI 高频词 | 替换为 | 说明 |
|-----------|--------|------|
| Spearheaded | Led / Drove | 除非真的是发起人 |
| Leveraged | Used / Applied | 简历不是商业计划书 |
| Synergized | Collaborated / Coordinated | |
| Orchestrated | Managed / Coordinated | 除非管理多个团队 |
| Pioneered | Introduced / Launched | 除非确实是第一个做 |
| Cutting-edge | Advanced / Modern | |
| Streamlined | Simplified / Improved | |
| Revolutionized | Improved / Transformed | |
| Robust | Strong / Reliable | |
| Comprehensive | Full / Complete | |
| Actionable insights | Findings / Recommendations | |
| Drive impact | Improve / Contribute to | |
| Cross-functional synergies | Cross-team collaboration | |
| Strategic initiatives | Projects / Programs | 除非确实是战略级 |
| Stakeholder alignment | Coordination with [具体角色] | |

### 中文 AI 味词汇

| AI 高频词 | 替换为 |
|-----------|--------|
| 赋能 | 支持 / 帮助 / 推动 |
| 抓手 | 方法 / 切入点 |
| 打通闭环 | 完成 / 覆盖全流程 |
| 深度赋能 | 直接删除或改为具体动作 |
| 全链路 | 端到端 / 从X到Y |
| 底层逻辑 | 核心逻辑 / 根本原因 |
| 颗粒度 | 细节 / 精度（视语境） |
| 拉齐 | 对齐 / 统一 |

### 口语化与网络流行词（中文简历专项，对照字节级头部公司简历语言标准）

字节 / 美团 / 米哈游等头部公司的高质量简历（参考 `assets/resume-bank/versions/custom/bytedance_hr_data_analytics/Alina_ByteDance_HR数据分析.tex` 中 bullet 风格）使用**正式书面语**，禁用以下口语 / 网络词：

| 口语 / 网络流行词 | 正式替换 | 用例对照 |
|---|---|---|
| 押注（哪条 / 哪个） | 布局 / 选择 / 优先方向 | "押注哪条赛道" → "下游应用赛道布局" |
| 倒逼 | 促使 / 迫使 / 推动 | "倒逼 OEM 转型" → "促使 OEM 重新定位" |
| 反构成 / 反而构成 | 反而构成 / 实质构成 | （正式书面"反而构成"OK；"反构成"省略式不正式）|
| 跑通 | 完成验证 / 完成端到端原型 | "跑通端到端原型" → "完成端到端原型验证" |
| 把（X 收敛到 Y）| 将（X 收敛至 Y）| "把范围从 X 收敛到 Y" → "将研究范围从 X 收敛至 Y" |
| 实为 | 实质为 / 本质为 | "客户'X'实为 Y" → "客户表面诉求为 X，实质为 Y" |
| 真正决策点是 / 真正价值不在 | 决策核心在 / 核心价值在 | "真正决策点是 X" → "决策核心在 X" |
| 对...影响最深 | 对...影响最大 / 影响最显著 | "对售后影响最深" → "对售后影响最大" |
| 反复出现 | 普遍存在 / 持续显现 | "在接口反复出现" → "在跨部门接口处普遍存在" |
| "客户'X'问句" 引述风格 | "为客户...制定 / 评估 / 分析" 命题式 | "客户'押注哪条赛道'研究" → "为客户制定下游赛道布局" |
| 没必要 / 不能这样 | 不必要 / 不宜 | （删或改正式表达） |
| 看出 / 发现 / 分析显示 / 分析指出 / 校准过程显示（高频引出 insight） | **直接陈述事实**（最佳）；或换 "结论是 X" / "X 已成为..." / "其中 X 影响最大"等具体引导 | "分析显示 AI 计算被 Foundry 主导" → "AI 计算增速最快但被 Foundry 主导" |
| **LLM 自造词 / 不存在的搭配**（如 "切入证据"、"开放进入空间"、"赛道选择建议"等中文专业写作中不存在的临时拼接） | 拆开 + 用通用表达：切入证据 → 入手点 / 起始依据；开放进入空间 → 仍处于分散竞争阶段；赛道选择建议 → 赛道优先级建议 | "以 X 为切入证据" → "从 X 入手" / "针对 X 的趋势" |
| **汇报报告口吻 frame "我看穿了什么"**（"客户表面诉求是 X，实质为 Y" / "看似 X，实为 Y" / "表象 X，本质 Y"等揭示式句式） | 简历不是咨询交付材料，不该 frame "我洞察了什么"。直接**陈述事实 + insight + 输出建议**：识别 X，定位根因为 Y，输出 Z 建议 | "客户表面诉求是'系统不足'，实质为流程权责不清" → "识别 6 大跨部门接口断点，定位根因为流程权责不清与数据口径不统一" |

**正式简历的标志性句式（从字节版提炼，可直接套用）：**

- "**为**国内头部 [行业] 客户**制定** [产出物]，**对比分析** [对象]，**基于** [方法] **筛选** [结论]，**为** [客户场景] **提供量化依据**"
- "**某** [行业 / 客户类型] [项目类型]，**搭建** [模型 / 体系]，**独立负责** [模块] **并按** [拆解维度] **逐层** [动作]，**结论直接用于** [客户使用场景]"
- "**围绕** [战略目标 / KPI]，**从** [访谈 / 数据] **中** [归纳动词] **并** [结构化归类]，**识别出** [非显然 insight]，**直接用于** [决策应用]"
- "**在** [项目背景] **中独立负责** [模块]，**从** [N 个维度] **评估** [对象] **的差异化冲击**，**支撑** [客户决策应用]"

### AI 味标点 / 句式（与词汇同等重要，是 AI 检测的一类硬指纹）

| 反模式 | 为什么是 AI 指纹 | 替换方案 |
|---|---|---|
| **"X——Y" 双破折号引出 insight** | LLM 极常用作 "结论 + 展开" 的连接，人类专业写作中很少这样高频用 | 改 "X：Y"（冒号）/ "X，Y"（逗号）/ 拆成两个分号子句 |
| **"A → B → C → D" 箭头流程链** | "搜索 → 分析 → 推荐 → 提醒"是典型 LLM 自动生成的可视化流程；正式简历应转为名词列举 | 改 "覆盖 A、B、C、D 等环节" / "实现从 A 到 B 再到 C 的完整链路" |
| **"X / Y / Z / W" 过度斜杠并列（≥4 项）** | 中文专业写作用 "、" 顿号；高密度 "/" 是 LLM 排版习惯 | 改 "、" 顿号；列表过长则收敛为类别名词 |
| **"识别出 / 发现 / 看出"句首高频重复** | LLM 习惯用同一动词起 insight 段 | 全篇 "识别出" 限 ≤2 次，其余替换为 "判断 / 看出 / 提炼出 / 注意到" |
| **"X 不是 A 而是 B" 的对比定式过度使用** | LLM 经典套路，开头用 1 次有力，连用就显假 | 全篇 ≤1 次；其余改为正面陈述 |
| **数据范围 "25\% → 66\%" 箭头** | 数据流向用箭头是 LLM 风格 | 改 "由 25\% 升至 66\%" / "从 25\% 升至 66\%" |
| **数字范围 "3-5 倍"中的连字符** | 边缘 AI 指纹（数学连字符其实可保留），但稳妥起见简历优先用 "至" | 改 "3 至 5 倍" |
| **句末感叹号 / 问号** | 简历正文绝不出现 | 删 |

### 保护规则
- 如果 AI 味词汇 **出现在 JD 原文中**，则保留不替换（JD 用了 "streamlined"，简历也可以用）
- 动词替换后检查语义是否改变，改变则回退
- 数据日期段（如 LaTeX `2025.06 -- 2025.10`）的 en-dash 是典型排版连字符，不是 AI 指纹，保留

---

## Pass 3：真实性验证（Source-Grounding 机制）

### 目的
确保优化后的简历每一条事实陈述都可在 ground truth 文件中找到来源，防止 LLM 从训练数据 / 索引一句话总结 / "这种岗位通常..."类推断里凭印象生成内容。

### 核心机制：每条 bullet 必须 cite 源段落

**Step 6 重写产出每条 bullet 时，必须同步输出一条 `source:` 元数据**，格式如下（仅在内部 review 中使用，不渲染到最终简历）：

```
[bullet] 主导半导体 OSAT 行业五年增长战略子课题，对比汽车 / AI 计算 / 存储 / AI 终端 4 类下游对先进封装的需求差异，产出赛道优先级判断进入客户正式汇报。
[source] assets/experience-bank/raw/01-kearney.md § 项目 1 第二层（"下游应用研究重点覆盖汽车、AI 计算、存储、AI 终端四类方向"）+ § 结果与评价（"研究内容进入正式汇报"）
```

每条 bullet 的所有事实陈述（数字、名字、动作、结果）都需要在 `source:` 元数据中能被找到。

### Pass 3 验证流程

执行 Pass 3 时，逐条 bullet 做以下验证：

1. **Source citation 存在性** — 该 bullet 是否有 `source:` 元数据？没有 → 必须重写或删除
2. **Source 文件存在性** — `source:` 引用的文件路径是否在 repo 中存在？不存在 → 拒收
3. **逐事实 grounding** — 把 bullet 拆成事实点（数字 / 名字 / 动作 / 结果），逐个去 source 文件中验证：
   - 数字（如 "12 维 / 358 万 / HR 1.274"）→ 必须在 source 中字面出现或可由 source 直接计算
   - 专有名字（如 "Detoxify / 长电科技"）→ 必须在 source 中出现
   - 动作动词（如 "搭建 / 主导 / 独立负责"）→ 必须能在 source 中找到对应等价描述
   - 结果（如 "RMSE 降低 32%" / "完成 4 类下游应用比较"）→ 必须在 source 中可证

4. **找不到来源时的处理：**
   - 如果该事实是用户口头补充给本次 session 的（如刚说"我会爬虫"）→ 触发"补充资料"workflow，把口头信息**先写进 `user-profile.md` 或 `experience-bank/raw/`**，再回头让 bullet 引用，**绝不**只在简历里使用
   - 如果该事实无任何来源 → 整段标 `[待补充：XX]` 或直接删除该事实片段
   - **绝不**因为"这种岗位 / 这种学校通常会有 X"就补——这是 hallucination，不是 inference

### 不可修改字段（硬锁）
- [ ] 公司名称未被修改
- [ ] 职位名称未被修改（除非用户主动要求调整，如 Strategy Analyst ↔ Business Analyst）
- [ ] 教育背景（学校、专业、学位、时间、**实际修过的课程**）未被修改
- [ ] 实习时间未被修改
- [ ] 联系方式未被修改

> **课程名特别注意（来自 2026-04-26 试跑教训）：** 不允许从"哥大 MS in Applied Analytics 通常会有 Frameworks & Methods"等推断填充课程名。课程名必须 cite 到 `user-profile.md` 教育表 / 用户实际课程清单。找不到源 → 不写课程，仅写学校 + 学位 + 时间。

### 不可添加内容（禁止编造）
- [ ] 未添加用户原始简历 / user-profile / experience-bank/raw / speedlearn-whitelist 中没有的技能
- [ ] 未添加用户没有的证书或资质
- [ ] 未编造量化数字（如原文没有数字，用 `[待补充]` 标注而非虚构）
- [ ] 未添加用户没做过的项目或经历
- [ ] 未升级用户的职级或角色描述（实习生不能写成"主导"整个项目，除非 source 中明确）
- [ ] **未在实习段塞入实习中实际未使用的工具 / 技术**（如 Kearney 实际未用 Python，绝不能在 Kearney bullet 里写 "用 Python 自动化 X"——这种工具关键词应由真实使用过的项目段承载）

### JD-triggered Speedlearn 流程（白名单管理协议）

当 Step 6 重写遇到 **JD 关键词在简历中无对应 source** 时，按以下决策树处理：

```
JD 要求 X 但简历中无 X
  ├─ X 在 speedlearn-whitelist.json 已存在 → 直接注入 Skills section，cite source: speedlearn-whitelist.json#X
  ├─ X 不在 whitelist 但可速成（基于现有能力 3 天可达可面试水平）
  │    → 在 chat 中向用户提议入库（含 basis + speedlearn_path）
  │    → 用户 ✅ → 同次 commit 写进 whitelist + 注入 Skills；记录 _added_for_jd（trigger JD 简称）+ _added_at（日期）
  │    → 用户 ❌ → 不注入，标记为不可弥补 gap
  └─ X 不在 whitelist 且不可速成 → 不注入，作为不可弥补 gap，由 Step 5 gap-bridging 走经历补充建议路径
```

#### Speedlearn 入库的硬条件（用户必须同意时才入库）

入库的每个新条目必须包含以下 3 字段，缺一不可：

| 字段 | 含义 | 示例 |
|---|---|---|
| `name` | 技能 / 工具名 | `Snowflake` |
| `basis` | 为什么基于现有能力 3 天可达 | `会 SQL + Apache Spark，云仓库查询语法与本地 SQL 相通` |
| `speedlearn_path` | 具体怎么学 | `Snowflake free trial + SnowPro Core 入门课 + 一个 sample warehouse 练习` |

可选字段（自动填充）：
- `_added_at`: 入库日期
- `_added_for_jd`: 触发本次入库的 JD 简称（如 `mihoyo-content-sentiment-2026`）

#### 注入位置约束

- ✅ 允许：Skills section 直接列入
- ✅ 允许：Summary 中以"具备 X 能力"形式提及（不允许过度具体）
- ❌ 禁止：实习 / 项目 bullet 中写"我用 X 做了 Y"——这是事实陈述，会让面试官追问"哪个项目用过"，速成技能没有项目支撑会露馅
- ❌ 禁止：基于速成技能写主观经验描述（"熟练掌握 X" / "深度使用 X"）

> **典型场景：** JD 要求 "Tableau 熟练"，用户白名单已有 Tableau —— Skills section 写 "Tableau" 即可，但**绝不**在某段实习 bullet 里写 "用 Tableau 搭建看板服务于业务团队"，因为该实习并未实际使用 Tableau。

### 可修改范围（白名单）
- ✅ Bullet point 措辞与结构（在 source-grounding 约束内）
- ✅ Summary / Qualifications 段落（同样需要 source）
- ✅ 技能栏的排序和分组
- ✅ 经历的排序（相关性排序）
- ✅ Bullet point 的增删（基于已有经历拆分或合并；不允许跨项目合并，见 `general-rules.md` 第 1 条）

### Failure modes（典型违规案例，来自 2026-04-26 试跑）

| 违规类型 | 例子 | 为什么算违规 |
|---|---|---|
| **数字凭印象** | "12 维竞争格局分析与 3 类战略路径推演" | source `01-kearney.md` 中无 12 维 / 3 类，凭"咨询通常 X 维框架"印象编 |
| **工具硬塞** | "用 Python 自动化抽取关键政策条款"（写在 Kearney bullet 里） | source 中 Kearney 项目无任何 Python 使用记录 |
| **课程名推断** | 教育部分写 "Frameworks & Methods" | user-profile 教育表无该课程，凭"哥大通常 X"推断 |
| **空泛过程量化** | "覆盖 30 家企业对标" | 30 家不在 source 中且无实质内容 |
| **宣称客户行为** | "客户基于此完成 go/no-go 决策" | 实习生角色无法 verify；面试追问会答不出 |

### 输出
Pass 3 结束时输出：
- 通过的 bullet：标记 `pass_3: complete`
- 标了 [待补充] 的 bullet：标记 `pass_3: partial`，列出每个 [待补充] 项
- 找到 unsourced claims：标记 `pass_3: failed`，列出问题 bullet 与缺失的 source

`pass_3: failed` 或 `unsourced_claims` 非空 → review queue **必须**人工审核，不允许自动渲染 LaTeX。

---

## 执行时机

所有 Pass 在 **Step 6（逐段优化）完成后、Step 7（补充建议）之前** 执行。

执行顺序严格为 **Pass 1 → Pass 1.5（中文）/ Pass 1.6（英文，互斥或双语全跑）→ Pass 2 → Pass 3**：
- Pass 1 可能引入新关键词，Pass 1.5 / 1.6 需要检查这些新词是否产生翻译腔或语言问题
- Pass 1.5 / 1.6 是语言专项审查，先解决 native readability 问题
- Pass 2 在语言专项之后做 generic AI flavor sweep，覆盖剩余 AI 味
- Pass 2 替换词汇后，Pass 3 需要验证替换是否改变了含义
- Pass 3 是最终安全门，必须在所有修改完成后执行

### 简历语言模式与 Pass 应用

| 简历模式 | Pass 1.5 中文 | Pass 1.6 英文 |
|---|---|---|
| 中文单语 | ✅ 跑 | ❌ skip |
| 英文单语 | ❌ skip | ✅ 跑 |
| 双语（EN page 1 + ZH page 2）| ✅ 跑（中文页）| ✅ 跑（英文页）|

### Failure mode 防御

`quality-pass-runner` 启动前必须 detect 简历语言模式：
1. 读 metadata 或 LaTeX `\setCJKmainfont` 存在性 → 判断双语
2. 默认 skip 中英任一 Pass 是错误（曾在 2026-05-10 IBM 试跑发生跳过 Pass 1.6 的案例，导致 Excel / Talent Framework 等问题事后才修）
3. 强制要求所有 Pass 输出**报告**（即使无 issue），证明 Pass 实际跑过
