# Market Context — North America

**Status:** Full（默认市场，全盘跑通基线）。

合并自原 role-competency-extractor 与 resume-rewrite-engine 两份 market-localization 的 NA 章节，分两个层面：JD 解读语境、简历呈现规则。

---

## 1. JD 解读语境（competency model 输出层）

### 1.1 招聘筛选规范
- ATS-first 是默认。多数申请先过自动关键词匹配再进人眼
- 招聘人首扫一份简历 6-10 秒。第一页前 1/3 决定是否继续
- **achievement orientation** 主导："你达成了什么" 重于 "你负责什么"
- 量化 impact 是 gold standard：营收 / 成本节约 / 百分比改进 / scale 指标
- 简洁被推崇：<10 年经验 1 页，资深角色最多 2 页

### 1.2 Hidden screening 信号
- generic "authorized to work in U.S." → neutral（F-1 OPT 满足）
- 显性 sponsorship → positive
- 显性 no-sponsorship / U.S. citizen only / clearance → hard skip
- "X+ years of experience" 通常是底线但有弹性（按 senior level 而定）
- 学校品牌不是决定性，但顶级品牌（HYPSM / 公牛校）打开顶级雇主门槛

### 1.3 优先排序的能力
- 可量化业务 impact
- ownership 与 autonomy 信号
- 进展速度 / 增长 scope
- 最近 2-3 段角色相关性
- 具名工具与技术（technical 角色）

---

## 2. 简历呈现规则（rewrite engine 输出层）

### 2.1 Resume 哲学
"Show me what you achieved, not what you were assigned."

### 2.2 结构惯例

| 维度 | NA 标准 |
|---|---|
| 长度 | <10 年 1 页；senior 最多 2 页（无例外，除非用户显式要求） |
| 格式 | reverse chronological，最近的角色占最多空间 |
| Summary | 3-4 行，可选但推荐用于换轨 / 需要显式 narrative；读起来是 value proposition，不是 career objective |
| 照片 | **不放** |
| 个人信息 | 姓名 / email / 电话 / LinkedIn / 城市州。不写年龄 / 婚姻 / 国籍 |

### 2.3 内容侧重
- 每条 bullet 都回答 "so what?"
- 量化是默认，不是可选
- ownership 信号：led 永远胜过 supported
- recency bias 强 — 最近 2-3 段经历占 80% 注意力
- Skills section：精炼 / keyword-rich / 按类别分组 / 不自评等级

### 2.4 ATS 注意
- ATS 提交版本用单列、文本格式
- 不用 table / text box / 图形
- section header 用标准 label：**Experience / Education / Skills**
- 文件格式：.docx 或 .pdf 视申请系统要求

### 2.5 Bullet 风格

**PAR 模式（Problem → Action → Result）是默认：**

> "Identified a 15% drop in customer NPS scores [problem], redesigned the post-purchase survey flow and implemented an automated follow-up sequence [action], recovering NPS to pre-decline levels within one quarter [result]."

### 2.6 Proof 层级
**Impact → Method → Scope**（影响 → 方法 → scope）

第一句先说 impact，再补方法，最后必要时点 scope。

### 2.7 Front door
- Summary
- 第一段经历的第一条 bullet

这两个位置承担 80% 的"是否继续读"决策。

---

## 3. 这个市场常见错误

- 简历过长，塞满早期无关细节
- duties-based bullets 没 impact 指标
- 缺 ATS 会过滤的关键词
- Summary 通用到任何候选人都能套
- 误把 HK / 内地的 scope 描写习惯带过来（写团队人数、地理覆盖、预算时显得啰嗦）
- 列工具不带语境（"Proficient in Python" 弱于 "Built Python anomaly detection pipeline"）

---

## 4. 关键词与动词偏好

### 4.1 高信号动词（Tier 4）
Led / Built / Designed / Drove / Owned / Spearheaded / Launched / Established / Modeled / Optimized / Reduced / Improved / Identified

### 4.2 弱动词（避免）
Assisted / Helped / Supported / Participated / Contributed / Responsible for / Was involved in

### 4.3 量化偏好
- 美元金额：$2M / $500K（不写 "two million dollars"）
- 百分比：15% / 3x（不写 "fifteen percent"）
- 计数：12 markets / 5 team members / 200+ users
- 时间：within 3 months / over 2 quarters

---

## 5. 与 5 lens 的交互

NA 市场下，每个 lens 的 narrative 与动词偏好以本文件为基础叠加 lens 文件。冲突时**lens 优先**（lens 是岗位族层；NA 是市场层；岗位族决定行话）。

详见 `role-lenses/A-strategy-research.md` 等 5 个 lens 文件。

---

## 6. JD → 简历 Bullet 模式速查

```
[强动词 Tier 4]
  + [Tier 2 capability]
  + [Tier 3 tool/method] (可选)
  + [量化结果 / scope]
```

示例：
> "Led competitive market analysis using SQL-based data extraction and Tableau dashboards, identifying 3 underserved segments that informed a $2M product expansion strategy."

含：led（Tier 4）/ competitive market analysis（Tier 2）/ SQL（Tier 3）/ Tableau（Tier 3）/ $2M（量化）/ product expansion（Tier 2）。
