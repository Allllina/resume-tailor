# LaTeX 输出指南

## 模板位置

`assets/knowledge-base/references/templates/resume-zh.tex` — 中文一页简历模板（XeLaTeX 编译）

## 格式基准（硬编码，2026-04-25 定稿）

以下格式规范来自美团投递版，所有中文简历必须遵循：

### 包与字体
- `\documentclass[10pt, a4paper]{article}` + `\usepackage[fontsize=9.5pt]{scrextend}`
- 中文支持：`\usepackage[UTF8, scheme=plain, fontset=fandol]{ctex}`（不用 xeCJK + fontspec）
- 仅需 5 个包：`geometry`, `ctex`, `titlesec`, `enumitem`, `hyperref`
- **不使用**：`xcolor`, `graphicx`, `fancyhdr`, `wrapfig`, `tabularx`, `fontspec`, `xeCJK`

### 页面与间距
- Margin：`top=0.4in, bottom=0.4in, left=0.55in, right=0.55in`
- 全黑字体：`\hypersetup{colorlinks=false, pdfborder={0 0 0}}`
- 无页码、无缩进、无段距

### 标题格式
```latex
\titleformat{\section}
    {\large\bfseries}  % 无 \sffamily，无 \color
    {}
    {0em}
    {}
    [\vspace{-0.6em}{\rule{\textwidth}{0.8pt}}]  % 无 \textcolor

\titlespacing*{\section}{0pt}{0.4em}{0.4em}  % 注意是 0.4em 不是 0.6em
```

### 列表格式
```latex
\setlist[itemize]{
    leftmargin=1.2em,
    itemsep=2pt,    % 不是 1pt
    parsep=2pt,     % 不是 0pt
    topsep=4pt,     % 不是 2pt
}
% 不设置 label=\textcolor{primary}{\textbullet}（使用默认黑色圆点）
```

### 自定义命令
```latex
\newcommand{\expheader}[4]{%
    \vspace{3pt}%       % 不是 4pt
    {\bfseries #1} \hfill {#3} \\    % 无 \small，无 \color{secondary}
    {#2} \hfill {#4}%                 % 无 \small，无 \color{secondary}
    \vspace{3pt}%       % 不是 2pt
}
% eduheader、projheader 同理
```

### 头部信息（居中布局）
```latex
\begin{center}
    {\LARGE\bfseries {{NAME}}} \\[4pt]    % 无 \sffamily
    {{PHONE_1}} \enspace|\enspace
    {{PHONE_2}} \enspace|\enspace
    {{EMAIL}} \enspace|\enspace
    {{LOCATION}}
    \\[2pt]
    LinkedIn: {{LINKEDIN}}
\end{center}
```
- **不使用** minipage 左右分栏布局
- **不使用** `\href{mailto:...}` 包裹邮箱（全黑无链接色）

### \sloppy 位置
`\sloppy` 放在 `\begin{document}` **之前**，不是之后。

### 内容密度参考
典型一页简历容量（9.5pt + 紧凑 margin）：
- 教育经历：2段
- 实习经历：3-4段完整展开（每段2条bullet）+ 可选"其他经历"单行
- 项目经历：2段（2+1 或 2+2 条bullet）
- 技能：2行

## 输出流程

### 1. 读取模板
读取 `resume-zh.tex` 模板文件。

### 2. 替换占位符
将模板中的 `{{PLACEHOLDER}}` 替换为优化后的实际内容。

**占位符命名规则：**
- `{{NAME}}`, `{{PHONE_1}}`, `{{PHONE_2}}`, `{{EMAIL}}`, `{{LOCATION}}`, `{{LINKEDIN}}` — 个人信息
- `{{EDU_SCHOOL_1}}`, `{{EDU_MAJOR_1}}`, `{{EDU_TIME_1}}`, `{{EDU_LOCATION_1}}`, `{{EDU_COURSES_1}}` — 教育（按序号）
- `{{EXP_COMPANY_N}}`, `{{EXP_ROLE_N}}`, `{{EXP_TIME_N}}`, `{{EXP_LOCATION_N}}` — 经历标题
- `{{EXP_BULLET_N_M}}` — 第N段经历的第M条bullet
- `{{PROJ_NAME_N}}`, `{{PROJ_TIME_N}}`, `{{PROJ_BULLET_N_M}}` — 项目
- `{{SKILL_CAT_N}}`, `{{SKILL_LIST_N}}` — 技能分类和列表
- `{{OTHER_EXP}}` — 其他经历（单行，可选）

### 3. 结构调整
根据优化结果，可能需要调整模板结构：
- **增减经历段数**：复制或删除 `% --- 经历 N ---` 区块
- **增减bullet数**：在 `\begin{itemize}` 中增删 `\item`
- **增减项目数**：复制或删除项目区块
- **增减技能分类**：在技能 section 中增删 `\item`
- **调整经历排序**：按JD匹配度重新排列区块顺序

### 4. 排版规则

**中文简历名字规则：**
- 中文简历的姓名部分只写中文名（如"Alina"），不附加英文名或拼音
- 英文简历的姓名部分写英文名（如"Jingwen (Alina) Chen"），不附加中文名

**字号规则（硬编码）：**
- 基准 10pt + scrextend 9.5pt，正文所有内容统一字号
- 不使用 `{\small}` 缩小任何正文内容
- 仅板块标题（`\section`）使用 `\large` 略大于正文
- 自定义命令（`\expheader`、`\eduheader`、`\projheader`）内部不使用 `{\small}`

**课程标签：**
- 使用"核心课程"（不是"主修课程"）

**中文简历教育经历格式（硬编码）：**
- 学校名只写中文（如"哥伦比亚大学"，不写"Columbia University"）
- 专业只写中文，不附英文（如"应用分析"，不写"Applied Analytics"）
- 学位用"硕士"或"本科"，格式为：`硕士 | 专业：应用分析`
- 地点用中文（"纽约"不是"New York, NY"）
- 英文简历保持英文写法不变

**公司名称规则（硬编码，不可修改）：**

| 公司 | 中文简历写法 | 英文简历写法 |
|------|------------|------------|
| Kearney | 科尔尼管理咨询 | A.T. Kearney |
| Ipsos | 益普索Ipsos | Ipsos Strategy3 |
| Desay SV | 德赛西威（头部汽车电子上市公司） | Desay SV (leading China-based automotive Tier-1 supplier, publicly listed) |
| Mercer | 美世咨询 | Mercer Consulting |

**岗位名称规则（硬编码，不可修改）：**

| 公司 | 中文简历岗位名称 | 英文简历岗位名称 |
|------|----------------|----------------|
| Kearney | 商业分析实习生 | Strategy Analyst Intern（咨询投Strategy Analyst，互联网投Business Analyst） |
| Ipsos | 市场战略分析实习生 | Market Strategy Analyst Intern |
| Desay SV | 战略变革实习生 | Strategy & Transformation Analyst Intern |
| Mercer | 管理咨询实习生 | Talent Consulting Analyst Intern |

- 中文简历统一使用中文岗位名称，不附英文
- 英文简历使用英文岗位名称，不附中文

**实习 Bullet Point 结构规则（硬编码）：**
- 每条 bullet 必须先用半句话介绍项目背景（这个项目/课题是为了什么），再写自己在其中做了什么、产出什么结果
- 格式：`\textbf{主题标签：}[项目背景半句话]，[我做了什么]，[产出/结果]`
- 项目背景示例：「为国内头部半导体封测客户制定五年增长战略」「公司启动欧洲市场年度战略复盘」「某石油央企哈萨克斯坦子公司组织重组项目」
- 背景描述应简短（15字以内为佳），不喧宾夺主

**写作风格规则（硬编码）：**
- **少用括号**：信息用逗号或自然语序衔接，不要用括号罗列。错误：「四层诊断（理念—指标—执行—应用）」→ 正确：「从理念、指标、执行、应用四层诊断」
- **少用箭头**：不用 → 或 $\rightarrow$ 表达过程或数量变化。错误：「（29→22部门）」→ 正确：「将部门从29个整合至22个」
- **结尾写 impact 而非动作**：bullet 结尾应说明产出/影响，而非停留在"推动客户启动xx"。错误：「推动客户启动架构调整」→ 正确：「明确职责边界并减少跨部门协调冗余」
- **不列无意义维度**：如果列举维度本身不产生信息增量，用框架价值替代。错误：「涉及学历经验、知识技能、资格证书等维度」→ 正确：「将硬性资格与软性资格拆分定义，建立能力等级与薪酬区间的联动框架」
- **数量表达**：200+名（表"超过200"），不写 +200名（读起来像加法）
- **不同项目不揉杂**：华为对标和组织架构诊断是独立的分析动作，应拆成不同 bullet
- **同一项目不拆成多条 bullet**：如果两条 bullet 描述的是同一个项目的不同模块，应合并为一条。错误：市场规模测算写一条、患者流建模再写一条（实际是同一个项目）→ 正确：合并为一条，先写整体模型，再写负责的具体模块
- **数据源要准确**：不要凭印象编造数据源名称。错误：「KOL深访」（市场规模测算项目中实际是HCP访谈）→ 正确：核对经历仓库中的原始描述后再写
- **项目背景写矛盾，不写公司规模**：背景应点出这个项目要解决的核心矛盾，不是介绍公司体量或发展阶段。错误：「在公司从百亿迈向千亿的组织升级背景下」→ 正确：「公司绩效体系与战略脱节」
- **背景要短，不要铺陈**：矛盾一句话点到即可，不需要展开解释矛盾的具体表现。错误：「公司绩效体系与战略目标脱节，不同类型组织套用同一套考核逻辑，从理念、指标体系、管理执行、结果应用四层展开诊断」→ 正确：「公司绩效体系与战略脱节，通过管理层与焦点小组访谈诊断根因」
- **bullet 内部逻辑要连贯**：不了解项目的读者也要能跟着读下来。每一句之间要有因果或递进关系，不能跳跃。错误：「公司绩效体系与战略脱节，区分"业务"与"服务"组织的绩效边界」（"区分"从哪来的？）→ 正确：「公司绩效体系与战略脱节，通过访谈诊断根因，发现核心问题在于业务与服务组织混用同一套考核逻辑，据此设计分层指标体系」
- **收尾句式不重复**：同一份简历中，相同的结尾模式不能出现两次。如已用过「为xx提供量化依据」，其他 bullet 需换说法，如「直接用于确定xx优先级排序」

**"其他经历"格式（非 \otherexp 命令）：**
```latex
\vspace{3pt}
{\bfseries 其他实习经历：}公司A\ 岗位A（时间A）\enspace|\enspace 公司B\ 岗位B（时间B）
\vspace{3pt}
```

### 5. LaTeX 特殊字符转义
替换内容时必须转义以下字符：
- `%` → `\%`
- `&` → `\&`
- `#` → `\#`
- `_` → `\_`（在文本中；数学模式中不需要）
- `$` → `\$`
- `{` / `}` → `\{` / `\}`（在非命令语境中）
- `~` → `\textasciitilde{}`
- `^` → `\textasciicircum{}`

**注意：** bullet 中的中文内容通常不需要转义，主要注意英文技术术语中的特殊字符。

### 6. 输出
将替换完成的 `.tex` 文件保存到 outputs 目录，文件名格式：`{姓名}_{目标岗位/方向}.tex`

## 编译说明

告知用户：
- 上传到 Overleaf
- 选择编译器为 **XeLaTeX**
- ctex + fandol 字体集在 Overleaf 上开箱即用，无需额外配置
