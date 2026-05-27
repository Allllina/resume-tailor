"""auto_scorer — LLM-driven scoring of an experience along 3 axes.

Per Wave 2.7 P2.2. Output shape conforms to the experience.schema.json
3-axis fields. On any LLM failure (raise / malformed JSON / wrong shape)
returns a deterministic safe-default fallback marked with `_fallback: True`.

Axes:
  - recognition_per_industry: 8 industry columns → high|medium|low|null
  - vertical_fit_per_lens:    5 role-family lens columns → core|adjacent|weak|missing
  - ai_digital_fluency:       single field → strong|moderate|weak|none
"""
from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger


# ---------------- column definitions ----------------

INDUSTRIES = (
    "consulting",
    "finance",
    "internet_strategic",
    "internet_operational",
    "internet_data",
    "education",
    "market_research",
    "brand_marketing",
)

LENSES = (
    "A_strategy_research",
    "B_data_analytics",
    "C_product_ops",
    "D_finance_markets",
    "HC_human_capital",
)

INDUSTRY_VALUES = {"high", "medium", "low", None}
LENS_VALUES = {"core", "adjacent", "weak", "missing"}
AI_VALUES = {"strong", "moderate", "weak", "none"}


# ---------------- prompt ----------------

_SYSTEM_PROMPT = """你是一名简历评估专家。根据候选人提供的一段经历内容（中英混合可接受），
你需要沿三个维度对该段经历做出客观评分，并严格以 JSON 输出（不要任何解释文字、不要 Markdown 代码块）。

输出 JSON 结构必须包含且仅包含三个键：

1. "recognition_per_industry"：八个行业关键字的对象，取值为 "high" / "medium" / "low" / null：
   - consulting（管理咨询）
   - finance（投行/PE/VC/二级）
   - internet_strategic（互联网战略/PMO）
   - internet_operational（互联网运营/产品）
   - internet_data（互联网数据/BI/分析）
   - education（教育/教培）
   - market_research（市场研究/调研）
   - brand_marketing（品牌/市场营销）
   评分依据该行业是否会"认可这段经历的含金量"。无法判断时返回 null。

2. "vertical_fit_per_lens"：五个角色镜头的对象，取值为 "core" / "adjacent" / "weak" / "missing"：
   - A_strategy_research（战略研究）
   - B_data_analytics（数据分析）
   - C_product_ops（产品运营）
   - D_finance_markets（金融市场）
   - HC_human_capital（人力资本/组织）
   评分依据该经历对该镜头岗位的匹配度。

3. "ai_digital_fluency"：单一字段，取值为 "strong" / "moderate" / "weak" / "none"。
   是否体现 AI / 数字化工具熟练度。

严格要求：
- 只输出合法 JSON。
- 所有键必须存在；未知/无关时使用各自允许的最弱值或 null。
- 不要添加多余字段。"""


def _user_prompt(content: str) -> str:
    return f"以下是候选人的一段经历内容，请按系统消息要求评分并输出 JSON：\n\n---\n{content}\n---"


# ---------------- public API ----------------


def fallback_score() -> dict:
    """Deterministic safe defaults used when LLM scoring fails."""
    return {
        "recognition_per_industry": {k: None for k in INDUSTRIES},
        "vertical_fit_per_lens": {k: "missing" for k in LENSES},
        "ai_digital_fluency": "none",
        "_fallback": True,
    }


async def score_experience(content: str, llm: Any) -> dict:
    """Score one experience entry along 3 axes via LLM.

    On any failure path → returns fallback_score() (with _fallback=True).
    """
    if not content or not content.strip():
        return fallback_score()

    try:
        raw = await llm.call(
            system=_SYSTEM_PROMPT,
            user=_user_prompt(content),
            max_tokens=1024,
            temperature=0.0,
        )
    except Exception as e:
        logger.warning(f"auto_scorer: LLM call failed → fallback ({type(e).__name__}: {e})")
        return fallback_score()

    parsed = _parse_json(raw)
    if parsed is None:
        logger.warning("auto_scorer: failed to parse LLM JSON → fallback")
        return fallback_score()

    return _normalize(parsed)


# ---------------- internals ----------------


_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE)


def _parse_json(raw: str) -> dict | None:
    """Tolerant JSON parsing: strip common ```json ... ``` fences, attempt
    to load. Returns None if it can't recover a dict."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    m = _FENCE_RE.match(text)
    if m:
        text = m.group(1).strip()
    # Attempt direct parse
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        # Last-ditch: find the first { and last } and slice
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last < first:
            return None
        try:
            obj = json.loads(text[first : last + 1])
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _normalize(parsed: dict) -> dict:
    """Backfill missing keys + clamp invalid enum values to safe defaults.

    Never raises. Output is guaranteed to have all 3 axes populated with
    valid values across every required column.
    """
    rec_in = parsed.get("recognition_per_industry") or {}
    if not isinstance(rec_in, dict):
        rec_in = {}
    rec_out = {}
    for k in INDUSTRIES:
        v = rec_in.get(k)
        if v in INDUSTRY_VALUES:
            rec_out[k] = v
        else:
            rec_out[k] = None

    fit_in = parsed.get("vertical_fit_per_lens") or {}
    if not isinstance(fit_in, dict):
        fit_in = {}
    fit_out = {}
    for k in LENSES:
        v = fit_in.get(k)
        if v in LENS_VALUES:
            fit_out[k] = v
        else:
            fit_out[k] = "missing"

    ai = parsed.get("ai_digital_fluency")
    if ai not in AI_VALUES:
        ai = "none"

    return {
        "recognition_per_industry": rec_out,
        "vertical_fit_per_lens": fit_out,
        "ai_digital_fluency": ai,
    }
