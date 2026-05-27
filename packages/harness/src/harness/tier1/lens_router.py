"""Step 3 lens routing — keyword first, LLM fallback.

Per HARNESS_DESIGN.md §2.2 Planning. Inspired by JobHunter-Agent
two-stage classifier (keyword → LLM bridge).

Deterministic path: keyword-scan against 5-lens dictionary; if max
score >= CONFIDENCE_THRESHOLD, route deterministically.
LLM fallback: only fires when confidence too low; outputs JSON
with primary_lens + scenario.
"""
from __future__ import annotations

import json
from collections import Counter


KEYWORD_TO_LENS: dict[str, list[str]] = {
    "A_strategy_research": [
        "战略", "行业研究", "竞争格局", "战略咨询", "市场进入", "PEST", "Porter",
        "业务诊断", "战略选择", "价值链",
    ],
    "B_data_analytics": [
        "数据分析", "数据建模", "SQL", "Python", "统计", "异动归因", "指标体系",
        "业务指标", "数据治理",
    ],
    "C_product_ops": [
        "产品运营", "用户运营", "增长", "A/B test", "标签体系", "AIGC", "Agent",
        "Prompt", "RAG", "生成式 AI", "LLM", "内容工作流", "Prompt Engineering",
        "提示词", "提示词工程", "AI 应用",
    ],
    "D_finance_markets": [
        "估值", "投行", "行研", "DCF", "财务建模", "资本市场", "投资分析",
        "投融资", "财务分析",
    ],
    "HC_human_capital": [
        "人力资本", "组织诊断", "任职资格", "薪酬", "绩效", "HR Tech",
        "组织发展", "人才", "招聘", "人力资源",
    ],
}

SCENARIO_KEYWORDS: dict[str, list[str]] = {
    "ai-innovation": ["AIGC", "Agent", "Prompt", "RAG", "生成式 AI", "LLM", "标签体系", "提示词"],
    "consulting": ["战略咨询", "行业研究", "PEST", "Porter", "价值链"],
    "data-analysis": ["数据分析", "建模", "SQL", "异动归因"],
}

CONFIDENCE_THRESHOLD = 3  # min keyword hits to skip LLM fallback


class LensRouter:
    def __init__(self, claude):
        self._claude = claude

    async def route(self, jd_text: str) -> dict:
        scores: Counter = Counter()
        for lens, keywords in KEYWORD_TO_LENS.items():
            for kw in keywords:
                # case-insensitive count
                scores[lens] += jd_text.lower().count(kw.lower())

        primary, top_score = (scores.most_common(1) or [(None, 0)])[0]

        # Deterministic path
        if top_score >= CONFIDENCE_THRESHOLD:
            scenario = self._infer_scenario(jd_text)
            return {
                "primary_lens": primary,
                "scenario": scenario,
                "blend_ratio": dict(scores),
                "used_llm_fallback": False,
                "confidence": min(top_score / 10, 1.0),
            }

        # LLM fallback
        if self._claude is None:
            return {
                "primary_lens": primary or "C_product_ops",
                "scenario": None,
                "blend_ratio": dict(scores),
                "used_llm_fallback": False,
                "confidence": 0.0,
            }

        prompt = (
            'You are a resume-routing assistant. Output ONLY a JSON object: '
            '{"primary_lens": "<one of A_strategy_research/B_data_analytics/'
            'C_product_ops/D_finance_markets/HC_human_capital>", '
            '"scenario": "<short scenario name or null>"}.\n\n'
            f'JD:\n{jd_text}\n'
        )
        response = await self._claude.call(
            system="You are a resume routing assistant. Output JSON only.",
            user=prompt,
            max_tokens=120,
        )
        result = json.loads(response.strip())
        result["used_llm_fallback"] = True
        result["blend_ratio"] = dict(scores)
        result["confidence"] = 0.5
        return result

    def _infer_scenario(self, jd_text: str) -> str | None:
        for scenario, keywords in SCENARIO_KEYWORDS.items():
            if any(kw.lower() in jd_text.lower() for kw in keywords):
                return scenario
        return None
