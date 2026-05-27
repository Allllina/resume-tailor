# Market Context — Mainland China / 内地市场

**Status:** Full（与 NA 一同作为 JD→简历优化必须支持的两个市场）。

合并自原 role-competency-extractor 与 resume-rewrite-engine 两份 market-localization 的 Mainland China 章节，分两个层面：JD 解读语境、简历呈现规则。

---

## 1. JD 解读语境（competency model 输出层）

### 1.1 招聘筛选规范
- 平台为主：Boss直聘 / Lagou / 拉勾 / Liepin / 猎聘 / 智联，各自有格式与关键词匹配逻辑
- **Title + 雇主品牌**是 primary 筛选信号。"大厂"经验（BAT / TMD：字节 / 美团 / 滴滴）权重显著
- 学校 tier 仍然 relevant，特别对应届 / 高竞争岗位：985 > 211 > 其他；海外 QS 100 ≈ 985
- 国际经历价值要"翻译"成本地市场术语，不天然 superior
- 招聘人对 hiring manager 而言，本地业务语境的 relevance 比 international polish 更重要

### 1.2 Hidden screening 信号
- "985/211 优先"几乎不会写在 JD 但实际筛选普遍存在
- 年龄与职业进展速度被隐性评估（gap / lateral 移动需要 narrative 解释）
- 平台特异生态经验（微信生态 / 抖音 / 小红书 / 支付宝）往往比通用工具熟练度更值钱
- 团队规模 / 管理 scope 是 seniority 信号（不只是 title）
- 行业本地 track record（在中国市场做过这事）权重远高于纯海外履历

### 1.3 优先排序的能力
- 雇主品牌与 tier 识别度
- 大学 pedigree
- 本地平台与生态专长
- 管理 scope（团队人数 / 预算 / 地理覆盖）
- 中国市场的行业 track record
- 年龄 / 职业进展速度（implicitly）

---

## 2. 简历呈现规则（rewrite engine 输出层）

### 2.1 Resume 哲学
"Show me your pedigree, your scope, and your direct relevance to what we do."

### 2.2 结构惯例

| 维度 | 内地标准 |
|---|---|
| 长度 | 1-2 页，平台格式可能更受限 |
| 格式 | 中文简历是默认；MNC / 跨境角色用中英双语 |
| Summary | 简短、关键词密集；前置学校 tier、岗位关键词、年限 |
| 照片 | 标准且预期，专业头像 |
| 个人信息 | 更详细 — 年龄 / 性别 / 户籍有时包含（科技 / MNC 在演化中）|

### 2.3 内容侧重
- **雇主品牌 tier** 是 primary 信号：BAT / TMD / 大厂经验显著权重，公司名要显眼
- **大学 tier** 重要：985 > 211 > 其他；海外 QS 100 ≈ 985；教育部分常靠前
- **本地平台专长**（微信 / 抖音 / 小红书 / 支付宝生态）可能比通用工具熟练度更值钱
- **管理 scope** 信号 seniority：团队规模 / 预算 / 地理覆盖要明确写
- **项目制格式**对 tech 角色有效：列重大项目 + scope + 技术栈 + 结果

### 2.4 平台优化（Boss / Lagou / 猎聘）
- 资料卡 summary 前 200 字符前置关键词
- 用常被搜索的词，不用创造性表达
- 平台要求时填期望薪资
- 岗位 title 要精确匹配平台搜索分类

### 2.5 Bullet 风格

**Scope + 方法 + 结果，扎根本地语境：**

> "负责3条业务线的数据分析体系搭建，基于Python自动化日报产出流程，将周报产出时间从3天缩短至0.5天，覆盖DAU、转化率、GMV等核心指标。"

### 2.6 Proof 层级
**Pedigree → Scope → Relevance → Impact**（背书 → 范围 → 相关性 → 影响）

学校 / 雇主在前，再说团队 / 预算 / 业务 scope，再说中国市场 relevance，最后量化 impact。

### 2.7 Front door
- 学校 tier
- 雇主品牌（首段公司名）
- summary 关键词

---

## 3. 这个市场常见错误

- 直接 translate 西方简历，不调整结构与重心
- 过度 emphasize 国际经历但没 connect 到本地 relevance
- 用西方工具名而不提本地等价（"Mixpanel" → 写"神策 / GrowingIO"）
- 忽视雇主与学校品牌信号
- 简历过长 / 过详细，超过平台格式约束
- 用英文术语叠加（"我 lead 了一个 team"）— 整句中英夹杂减信任度

---

## 4. 关键词与动词偏好

### 4.1 高信号动词
中文五大类动词（领导力 / 分析力 / 执行力 / 创新力 / 沟通力）以 `general-rules.md` 为单一来源，本文件不重复，避免内地 / NA 共用时漂移。本市场特异的动词偏好如下：

- 内地市场倾向**结果前置 + scope 前置**——动词后立即接业务量级（GMV / DAU / 团队规模）再接结果
- 同一动词在整份简历重复 ≤2 次的规则保持；高频替换表也以 `general-rules.md` 为准

### 4.2 弱动词（避免）
参与 / 协助 / 帮助 / 负责（太被动；"负责"可以用，但后面必须跟具体成果）

### 4.3 量化偏好
- 业务量级：DAU / MAU / GMV / 营收 / 用户量
- 百分比：转化率提升 12pp、留存提升 8%
- 时间：周期缩短 / 项目从立项到上线时间
- 排名：行业 Top X / 部门第一 / 历史最大
- 模糊处理涉及机密的："营收规模数亿级" / "千万级用户量"

### 4.4 中英文混排规范（详见 `general-rules.md`）
- 专业术语保留英文：ROI / DAU / MAU / GMV / NPS / A/B Test / OKR / P&L / MECE / MVP
- 岗位名可中英对照：产品经理（Product Manager）
- 公司名 / 品牌名用英文原名：Kearney / McKinsey / ByteDance
- 整句不要中英夹杂
- 全篇一致：要么全用"用户"要么全用"User"

---

## 5. 与 5 lens 的交互

内地市场下，所有 lens 的描述要避免**翻译腔**与**英文直译**：
- "技术采用曲线评估" → "技术成熟度评估"
- "Spearheaded" 直译 → 主导 / 牵头
- 非通用英文缩写一律翻译为中文

冲突处理：lens 优先（行话 / 能力维度）；本文件优先（语言风格 / 量化习惯 / 结构）。

详见 `role-lenses/A-strategy-research.md` 等 5 个 lens 文件，每个 lens 内部应有 NA / 内地两套示例。

---

## 6. 与 quality-pass.md 的耦合

`quality-pass.md` 的 **Pass 1.5 中文可读性检查**仅在中文简历执行，本文件是其依据：
- 业务面试官能否不经"翻译"直接理解每条 bullet？
- 是否有英文直译的翻译腔？
- 非通用英文缩写是否已翻译？

---

## 7. JD → 简历 Bullet 模式速查

```
[强动词]
  + [scope / 业务线 / 团队 / 预算]
  + [方法 / 工具]
  + [量化结果 / 业务指标]
```

示例：
> "主导 3 条业务线的用户增长策略制定，基于漏斗分析与 A/B 测试，将注册转化率从 18% 提升至 27%（覆盖 200 万 DAU 场景）。"

含：主导（强动词）/ 3 条业务线（scope）/ 漏斗分析 + A/B 测试（方法）/ 18%→27%（量化）/ 200 万 DAU（scope）。
