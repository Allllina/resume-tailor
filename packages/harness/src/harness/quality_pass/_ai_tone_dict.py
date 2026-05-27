"""Deterministic phrase tables for quality-pass Pass 1.5 and Pass 2."""
from __future__ import annotations


AI_TONE_REPLACEMENTS: tuple[dict[str, str], ...] = (
    {"term": "cross-functional synergies", "replacement": "cross-team collaboration"},
    {"term": "actionable insights", "replacement": "findings"},
    {"term": "stakeholder alignment", "replacement": "coordination with stakeholders"},
    {"term": "strategic initiatives", "replacement": "projects"},
    {"term": "drive impact", "replacement": "improve"},
    {"term": "cutting-edge", "replacement": "advanced"},
    {"term": "Spearheaded", "replacement": "Led"},
    {"term": "spearheaded", "replacement": "led"},
    {"term": "Leveraged", "replacement": "Used"},
    {"term": "leveraged", "replacement": "Used"},
    {"term": "Synergized", "replacement": "Collaborated"},
    {"term": "synergized", "replacement": "collaborated"},
    {"term": "Orchestrated", "replacement": "Managed"},
    {"term": "orchestrated", "replacement": "managed"},
    {"term": "Pioneered", "replacement": "Introduced"},
    {"term": "pioneered", "replacement": "introduced"},
    {"term": "Streamlined", "replacement": "Improved"},
    {"term": "streamlined", "replacement": "improved"},
    {"term": "streamline", "replacement": "improve"},
    {"term": "Revolutionized", "replacement": "Improved"},
    {"term": "revolutionized", "replacement": "improved"},
    {"term": "Robust", "replacement": "reliable"},
    {"term": "robust", "replacement": "reliable"},
    {"term": "Comprehensive", "replacement": "complete"},
    {"term": "comprehensive", "replacement": "complete"},
    {"term": "深度赋能", "replacement": "支持"},
    {"term": "打通闭环", "replacement": "完成"},
    {"term": "全方位", "replacement": ""},
    {"term": "赋能", "replacement": "支持"},
    {"term": "助力", "replacement": "支持"},
    {"term": "抓手", "replacement": "方法"},
    {"term": "全链路", "replacement": "端到端"},
    {"term": "底层逻辑", "replacement": "核心逻辑"},
    {"term": "颗粒度", "replacement": "细节"},
    {"term": "拉齐", "replacement": "对齐"},
    {"term": "押注", "replacement": "选择"},
    {"term": "倒逼", "replacement": "促使"},
    {"term": "跑通", "replacement": "完成验证"},
    {"term": "没必要", "replacement": "不必要"},
    {"term": "不能这样", "replacement": "不宜"},
    {"term": "分析显示", "replacement": ""},
    {"term": "分析指出", "replacement": ""},
    {"term": "校准过程显示", "replacement": ""},
    {"term": "真正决策点是", "replacement": "决策核心在"},
    {"term": "真正价值不在", "replacement": "核心价值不在"},
    {"term": "对...影响最深", "replacement": "影响最大"},
    {"term": "反复出现", "replacement": "普遍存在"},
    {"term": "切入证据", "replacement": "入手点"},
    {"term": "开放进入空间", "replacement": "仍处于分散竞争阶段"},
    {"term": "赛道选择建议", "replacement": "赛道优先级建议"},
    {"term": "!", "replacement": ""},
    {"term": "！", "replacement": ""},
    {"term": "?", "replacement": ""},
    {"term": "？", "replacement": ""},
)


CHINESE_READABILITY_REPLACEMENTS: tuple[dict[str, str], ...] = (
    {"term": "技术采用曲线评估", "replacement": "技术成熟度评估", "reason": "english_direct_translation"},
    {
        "term": "通过对业务需求和媒体渠道的了解制定系统和产品优化策略",
        "replacement": "基于业务需求和渠道特点制定优化策略",
        "reason": "english_direct_translation",
    },
    {"term": "价值量提升逻辑", "replacement": "附加值增长空间", "reason": "english_direct_translation"},
    {"term": "TAM/SAM/SOM", "replacement": "市场规模（总量/可服务/可获取）", "reason": "non_universal_abbreviation"},
    {"term": "开放进入空间", "replacement": "仍处于分散竞争阶段", "reason": "english_direct_translation"},
    {"term": "赛道选择建议", "replacement": "赛道优先级建议", "reason": "english_direct_translation"},
)


STANDARD_TECHNICAL_TERMS: frozenset[str] = frozenset(
    {
        "AB测试",
        "BERT",
        "Excel",
        "LangGraph",
        "PPT",
        "Python",
        "ROI",
        "SQL",
    }
)


__all__ = [
    "AI_TONE_REPLACEMENTS",
    "CHINESE_READABILITY_REPLACEMENTS",
    "STANDARD_TECHNICAL_TERMS",
]
