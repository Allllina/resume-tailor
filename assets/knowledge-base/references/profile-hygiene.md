# 求职画像 Hygiene — user-profile / experience-bank 的隐私边界

> 设计参考：腾讯校招 skill 的 `career_memory.py`。本文是 candidate 侧改写版。
> 配套脚本：`scripts/profile_hygiene.py`（runtime sanitize 拒写敏感信息）。
> 加入版本：v0.6.x（与 R-19 隐私边界细则联动）。

---

## 1. 设计原则

`user-profile.md` 和 `experience-bank/raw/*.md` 是**长期复用**的求职画像 ground truth，不是临时 chat 状态。

凡要写入这两类文件的内容，必须满足两个条件：

1. **用户明确确认的事实**（不是 skill 推断 / chat 中模糊提及）
2. **会长期影响求职建议**（不是 transactional state，如某次面试时间）

任何敏感信息（PII / 薪酬 / NDA）写进长期文件 = 长期外泄风险，即使本地存储也是。

---

## 2. 允许记录

仅记录**用户明确提供、会影响求职建议的长期信息**：

### 基本信息
- 姓名（中英文）/ 邮箱 / 目标地区 / 学历阶段
- 联系电话（可选——见 §4 例外说明）

### 教育与技能
- 学校 / 专业 / 学位 / 时间 / 实际修过的课程
- 技能栈（编程语言、工具、框架）
- 语言能力（中文母语 / IELTS / CET-6 等已确认证书）

### 经历摘要（experience-bank/raw）
- 公司名 / 角色 title / 时间 / 工作地
- 项目目标 / 业务场景 / 你的具体行动 / 客观结果
- BQ 面试框架（三层结构 / 业务闭环 / 深挖问答）

### 求职偏好
- 目标行业 / 目标 lens / 目标公司类型
- 排版风格偏好（中文 / 英文 / 双语 / LaTeX）
- 沟通风格偏好（精简 / 详细 / 哪种语气）

### 优化历史
- 每次投递的目标岗位 / 核心调整 / 输出文件名
- 不写 offer 结果 / 不写薪酬 / 不写公司 hiring 内部反馈

---

## 3. 禁止记录（runtime 守卫触发）

写入 `user-profile.md` / `experience-bank/raw/*.md` 时，`scripts/profile_hygiene.py` 会 regex sanitize。命中以下任一即 **raise + 拒写**：

### 3.1 通用 PII
- 身份证 / 护照号
- 住址、银行卡号、社保卡号
- API key / secret / token / password / cookie
- 验证码 / OTP

### 3.2 候选人侧专属：薪酬 / offer 字段
- 月薪 / 年薪 / 年包（"月薪 25K"、"年包 50 万"等）
- 签字费 / sign-on bonus / 十三薪 / RSU / 股票期权数量
- offer 档位（"SSP 档 / SP 档 / 档位 A"等）
- base salary / total comp / offer package / salary / 薪资
- **期望薪资**（transactional state，不进 long-term profile）

> **检测方式（context-aware）**：守卫按薪酬上下文关键词判断，**不**裸匹配金额——业务成果指标如"成本节省 200 万 / GMV 500 万 / 营收提升 30%"不会被拦。这样既挡住薪酬泄漏，又不误杀简历该有的量化成果。

> **WHY**：薪酬属于 transactional context，只在当下投递有意义。写进 profile 后，下次跨 5 个岗位投递时这条数据反而成干扰。

### 3.3 候选人侧专属：NDA / 未脱敏客户名
- 真实涉密客户全名（除非项目已公开披露）
- "保密协议"、"内部代号"等 NDA 标记字段

> **WHY**：实习涉及 NDA 是常态。把真实 client name 写进 experience-bank/raw 等于在你机器留下 NDA 违约证据。简历投递时客户名要脱敏化（"某头部 OSAT 客户"、"某全球医疗设备客户"）。

### 3.4 不可推断的字段
- 性格 / 家庭背景 / 经济状况 / 政治观点 / 宗教 / 健康
- 即使用户某次 chat 提到了，**不写入 profile**

---

## 4. 例外：基本信息中的电话

`user-profile.md` 的 "基本信息" section 已包含手机号（resume contact info）。**这是 baseline 资产，不属于"新写入"**——`profile_hygiene.py` 不会扫现有文件，只在 `append --file user-profile.md` 时拒新增。

**新写入电话号码的合法路径**：
- 用户明确说"更新我的手机号为 X" → 用户手动编辑文件，不走脚本
- 任何其他路径（如 skill 从 JD 中提取 / chat 中无意提及）→ 走脚本，会被拒

---

## 5. 使用规则

### 5.1 写入前 sanitize
任何 skill workflow 想把内容写入 `user-profile.md` 或 `experience-bank/raw/*.md` 时：

```bash
python scripts/profile_hygiene.py check --text "<待写内容>"
# exit 0 = 通过；exit 1 = 命中敏感字段，必须先脱敏
```

或合并 sanitize + append：

```bash
python scripts/profile_hygiene.py append \
    --file assets/profile/user-profile.md \
    --text "目标地区：上海 / 深圳"
```

### 5.2 读取前优先级
对话开始或个性化建议生成时，**只读必要 section**，不要 dump 整个 profile。比如优化简历时只读「教育」+「经历清单」+「目标岗位」相关字段，不读"用户偏好"、"BQ 框架"等无关 section。

### 5.3 更新 vs 推断
**用户明确说**「我新增了一段 X 经历 / 把目标方向从 A 改成 B」→ 触发"补充资料"workflow，更新对应文件。

**模糊提及 / 推断信号**（如用户说"我可能更喜欢 product 方向"）→ **不要更新 profile**，仅 chat 内使用。再次确认后才入。

### 5.4 冲突解决
当 profile 与用户当前 chat 不一致时，优先用户当前说法。但**不要直接覆盖**——先问"你的目标方向是要从 X 改为 Y 长期生效，还是只这次投递用？"。

---

## 6. "Forget me" 命令

用户随时可触发删除：

### 6.1 删除某字段 / section

```bash
python scripts/profile_hygiene.py forget --field "优化历史"
# 删除 H2/H3 标题中含「优化历史」的整段
```

支持的 field 子串包括但不限于：联系方式 / 优化历史 / 个人兴趣 / 用户偏好 / BQ 框架。

### 6.2 删除整个 profile

默认 `forget --all` **可恢复**：把 user-profile.md + experience-bank/raw 移入同目录下 `.backup/<name>.<时间戳>`。只有加 `--confirm` 才永久删除。

```bash
python scripts/profile_hygiene.py forget --all
# 移入 .backup 备份（可恢复）；恢复时把备份文件 / 目录移回原位即可

python scripts/profile_hygiene.py forget --all --confirm
# 永久删除 user-profile.md + experience-bank/raw（不可恢复）；下次 skill 启动时重建空 template
```

### 6.3 触发条件

用户说以下任一表达 → 执行 forget 命令，**不追问原因**：

- "忘记我 / 删除记忆 / 不要保存 X"
- "把 X 字段从 profile 删掉"
- "我要重新开始"
- "delete my profile" / "forget me"

---

## 7. 与其他 reference 的耦合

- `general-rules.md` — 写作规则；本文是隐私层，互不冲突
- `quality-pass.md` Pass 3 (source-grounding) — bullet 事实必须 cite to ground truth；本文管 ground truth 本身的卫生
- `english-language-review.md` — 英文 readability；不涉及隐私
- `translation-glossary.md` — 翻译表；不涉及隐私

---

## 8. Failure modes（典型违规）

| 违规场景 | 错误做法 | 正确做法 |
|---|---|---|
| 用户 chat 中说"我刚拿了一个 35K/月 的 offer" | 写进 user-profile 优化历史 | chat 内 ack，profile 不写薪酬数字 |
| 实习项目客户是"某车企 X"（NDA 涉密）| 直接写"X 车企" 进 experience-bank | 脱敏成"某头部车企客户"再写 |
| 用户上传简历附件含手机号 | OCR 解析时整段塞进 experience-bank | 解析时跳过 contact info section |
| 用户说"我可能喜欢 product 方向" | 立即更新 user-profile 目标 lens | 仅 chat 内试用，确认后再 update |
| 用户问"上次投递哪些公司了？" | dump 整个 user-profile 优化历史给 chat | 只显示用户问的字段，不暴露其他 |

---

## 9. 与 R-19（隐私边界细则）的关系

SKILL.md 中 R-19 是高层 hard rule：

> R-19 隐私边界 — 不写敏感字段进 user-profile / experience-bank；用户随时可触发 forget。

本文是 R-19 的**详细实施**，回答 3 个具体问题：
- 什么算敏感？（§3）
- 怎么 enforce？（§5 + `profile_hygiene.py`）
- 怎么 forget？（§6）

R-19 违反 = trust foundation 受损。其他细则（动词去重等）违反 = 质量下降可修复；R-19 违反 = 数据已落盘难撤回。所以列入红线 2「用户主权」。
