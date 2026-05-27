---
title: 实习经历 Recognition 评分判准
status: v0.1 draft（待用户审阅 / 修改）
last_updated: 2026-05-03
owner: Resume_Optimizer
related:
  - assets/experience-bank/index.json (recognition_per_industry 字段)
  - packages/strategy-modules/resume-rewrite-engine/SKILL.md (实习筛选优先级硬规则)
---

# Recognition Rubric — 行业认可度评分判准

## 1. 用途

为 `experience-bank/index.json` 的 `recognition_per_industry` 字段提供打分依据，
避免凭印象 / 单次面试反馈直接写死。每条经历 × 每个目标行业打 high / medium / low / unknown。

**与本 rubric 配套但不在本文档中：**
- `vertical_fit_per_lens`（内容对位 lens 的契合度）—— 见独立 rubric（待建）
- `min_slot_priority`（在某场景下「必上 / 可选 / 仅空位」） —— 见 `resume-rewrite-engine/SKILL.md`

## 2. 评分轴定义

**Recognition = 目标行业的招聘方在看到该公司名时，第一反应给到的"信号强度"。**

不是绝对品牌知名度，是 **(招聘方所在行业 × 该公司在该行业的位置)** 的二维评分。同一家公司在不同行业可以打不同分。

| 等级 | 判准 |
|---|---|
| **high** | 招聘方在目标行业里把该公司视为同侪 / 上游 / 顶级招牌；候选人简历上一行就能加分；对口校招池里高频出现 |
| **medium** | 招聘方知道该公司，不视为强信号；不减分但也不是亮点；需要靠 bullet 内容撑起价值 |
| **low** | 招聘方不熟悉、识别成本高 / OR 业内共识门槛低 / OR 跨行业关联弱；放上去会稀释关键经历的注意力（"减分项"） |
| **unknown** | 没有任何 signal 来源；**JSON 写 `null` 走 fallback**（agent 默认 conservative behavior：不主动把该经历推到对应行业岗位的简历里），不要凭印象填 |

## 3. 证据等级（由强到弱）

> 评分必须附 `source` 字段，引用以下证据类型之一。仅 `inference` 级别的评分要标 `unverified: true`。

1. **first_party_interview_feedback** — 目标行业面试官明确说过的话（最高权重）
   - 例：京东 BA 面试官 2026-05-02 — "Desay SV 不知道是什么公司 / Ipsos 市调门槛不高"
2. **first_party_recruiter_feedback** — HR / 内推人 / 校招宣讲会反馈
3. **public_recruiting_signal** — 该公司在目标行业校招池的能见度（官方招聘公告 / 985 校招白名单 / 实习内推帖中提及频次）
4. **community_consensus** — 一亩三分地 / 脉脉 / 牛客 / Reddit 等社区中相关 thread 多数共识
5. **inference** — 没有上述证据时的判断；必须标 `unverified: true`，未来拿到证据立即升级

## 4. 行业列（initial set，可扩）

候选人当前关心的目标行业（与 `role_family` 五分对齐 + 互联网内部按招聘方画像 3 拆 + 几个垂直行业）：

**互联网（按招聘方画像 3 拆）：**
- `internet_strategic` — 商分 / 商业洞察 / 产品策略 / 战略 / 行业研究（招聘方画像偏 ex-consulting，看分析品牌）
- `internet_operational` — 产品运营 / 行业运营 / 策略运营 / 用户运营 / 增长（招聘方画像偏互联网 native，看业务感）
- `internet_pm` — 产品经理（独立 cluster，看产品 sense）

**其他行业：**
- `consulting` — MBB / 二线战略咨询 / 行业研究
- `auto_tech` — 汽车科技 / 智能驾驶 / 车载
- `consumer_research` — 快消 / FMCG / 市场研究
- `finance` — 投行 / 资管 / 金融市场
- `human_capital` — 人力资本咨询 / 组织发展 / HR Tech

> **新增行业 / 拆分前先确认**：候选人是否真的会投这个行业？是否有招聘方画像分歧的实证？避免给"投不到"的行业或没分歧的岗位凑评分。
>
> **`internet` 不再是单列**：所有 internet 经历必须落到 3 个 cluster 之一。如某条经历仅对 internet 三类中的一类有评分依据，其余两个 cluster 标 `unknown`，不要凭印象互相 copy。

## 5. 边界与陷阱

- **同一公司不同业务线必须分开打分**。Mercer 组织咨询 ≠ Mercer Marsh 福利；阿里中台 ≠ 阿里云。在 index.json 里用 `entity` 字段消歧。
- **跨地域 recognition 差异**。如 Desay SV 在中国汽车圈 medium-high，在海外科技圈 low。若场景 routing 跨地域，应在 `experience-bank` 拆出地域 tag。
- **品牌知名度 ≠ 业内认可度**。腾讯名气大，但若岗位是"腾讯客户中心客服"，对互联网 PM 招聘方仍是 low。recognition 看的是 **业务线 + 岗位 weight**，不是 logo。
- **门槛低 = low 信号**。Ipsos 品牌不算差，但"市调 part-time / 暑期项目"在互联网 BA 招聘方眼里被视为门槛低，**门槛本身就是 low signal**。这条要单独写进打分理由（`rationale`），便于 agent 复用。
- **单点反馈 ≠ 行业共识**。一条 first_party_interview_feedback 可作为 anchor，但若结论与多条 community_consensus 冲突，保留两个 source 并取保守值，注明分歧。

## 6. 时效性

- `first_party` 反馈：12 个月内为新鲜；>12 个月需新证据复核
- `public_recruiting_signal`：跟随每年校招季（春招 / 秋招）更新
- 重大事件（公司收购 / 退市 / 业务线裁撤 / 行业风口转向）触发立即重打

## 7. JSON 字段格式（在 index.json 中）

```jsonc
{
  "experience_id": "01-kearney",
  "entity": "Kearney 上海办公室 / 战略咨询线",
  "recognition_per_industry": {
    "internet_strategic": {
      "score": "high",
      "source": "first_party_interview_feedback",
      "source_ref": "京东 BA 面试 2026-05-02",
      "rationale": "面试官主动确认 Mercer + Kearney 是核心放置项",
      "last_verified": "2026-05-02"
    },
    "internet_operational": {
      "score": "medium",
      "source": "inference",
      "unverified": true,
      "rationale": "互联网 native 招聘方对咨询品牌识别度仍在，但不视作 ops sense 强信号"
    },
    "internet_pm": null,
    // ↑ 没证据时直接写 null。agent 读到 null 走 fallback：不主动把该经历推到 PM 岗简历里、
    //    也不在 routing 时给该 cluster 加分。等拿到反馈再升级为显式打分。
    "consulting": {
      "score": "high",
      "source": "public_recruiting_signal",
      "rationale": "MBB 之外二线战略咨询头部，校招池高频"
    },
    "auto_tech": {
      "score": "medium",
      "source": "inference",
      "unverified": true,
      "rationale": "Kearney 有汽车 practice 但本人项目非汽车线"
    }
  }
}
```

## 8. 已 verified 的 entries（首批 anchor）

| Experience | Industry | Score | Source | Notes |
|---|---|---|---|---|
| Mercer 组织咨询 | internet_strategic | high | 京东 BA 面试 2026-05-02 | 面试官点名"只需放 Mercer + Kearney" |
| Kearney 战略咨询 | internet_strategic | high | 京东 BA 面试 2026-05-02 | 同上 |
| Desay SV 海外子公司治理 | internet_strategic | low | 京东 BA 面试 2026-05-02 | "不知道是什么公司"——识别成本高 |
| Ipsos 市场研究 | internet_strategic | low | 京东 BA 面试 2026-05-02 | "市调门槛不高"——门槛信号弱（互联网商分语境下） |
| Ipsos 市场研究 | consumer_research | high | community_consensus | 市调 / FMCG 行业内 Ipsos 是头部老牌；该 lens 下"市调门槛"反而是核心能力 → 反向高信号 |

> 京东 BA 反馈仅覆盖 `internet_strategic` 一列；`internet_operational` / `internet_pm` 评分待新反馈来源。其他 industry 列（consulting / auto_tech / finance / human_capital）以及 米哈游、京东实习（如有）评分待回填，建议候选人逐条确认证据等级再写入。
>
> **关键 anchor**：同一份经历（Ipsos）在不同行业列下评分相反——这正是 recognition 必须按 (招聘方所在行业 × 公司位置) 二维打分、不能给"绝对品牌分"的原因。

## 9. 与 vertical_fit_per_lens 的关系（重要）

| 字段 | 回答的问题 | 决定什么 |
|---|---|---|
| `recognition_per_industry` | 招聘方看到这家公司会不会"眼前一亮" | 品牌信号 / 是否上简历的第一道筛 |
| `vertical_fit_per_lens` | 这条经历的内容能不能直接映射到目标 lens 的能力 | bullet 是否需要重写 / 角度切换 |

**组合规则（首版草案，等 vertical_fit rubric 落地后正式写入 SKILL.md）：**

| recognition × fit | 决策 |
|---|---|
| 都高 | 必上 |
| recognition 高 / fit 低 | 上，但 bullet 努力靠拢岗位能力（rewrite） |
| recognition 低 / fit 高 | 上但不优先；用 bullet 内容补品牌弱点 |
| 都低 | 删掉（除非空位且无替代） |

完整选用规则放在 `resume-rewrite-engine/SKILL.md` 的"实习筛选优先级"硬规则。

## 10. 待修订（请用户审阅）

**已确认（2026-05-04）：**
- [x] 互联网拆为 `internet_strategic` / `internet_operational` / `internet_pm` 三列
- [x] 首批 4 条评分确认；新增 Ipsos × `consumer_research` = high
- [x] 4 象限决策符合直觉（recognition 低 / fit 高 仍属"不优先"）
- [x] high / medium / low 三档粒度足够，不加 borderline

**已确认（2026-05-04 第二轮）：**
- [x] `unknown` 在 JSON 中写 `null` 走 fallback（agent 默认 conservative）
- [x] 京东不是 experience-bank 实习条目；京东 BA 面试反馈已作为 source 锚定 §8 四条 `internet_strategic` 评分，无需再增条目
- [x] `vertical_fit_per_lens` rubric 已起草（同目录 sister 文档，asymmetric reference 避免短循环）

**仍待决：**
- 暂无。下一步：按本 rubric + vertical-fit rubric 给 6 条经历回填 `index.json`。
