"""Bullet 标签 rewriter — single Claude call, strict prompt.

Per Tier 1 Light Tailoring: only the bullet 标签 (粗体开头总结词)
changes; bullet body remains verbatim from master.

The prompt is intentionally short and forbids changes to bullet body —
the model returns ONLY {"new_label": "..."} JSON.
"""
import json
from typing import Any


LABEL_PROMPT = """你是一个简历 bullet 标签优化助手。

任务：根据 JD 关键词，将 bullet 的开头粗体标签（4-8 字）改写为更贴合岗位语境的版本。

**严禁**修改 bullet body 的任何事实陈述。**严禁**添加或删除数字、公司名、工具名、动作。

输入：
- JD 关键词：{keywords}
- Bullet 原文：{bullet}

输出：仅 1 个 JSON 对象 `{{"new_label": "<新标签>"}}`，不要其他内容。
"""


class LabelRewriter:
    def __init__(self, claude: Any):
        self._claude = claude

    async def rewrite(self, bullet: str, jd_keywords: list[str]) -> str:
        """Return new label string. Falls back to extracting prefix-before-colon
        on JSON parse error or missing key.
        """
        prompt = LABEL_PROMPT.format(
            keywords=", ".join(jd_keywords[:10]),
            bullet=bullet,
        )
        response = await self._claude.call(
            system="You are a precise resume label rewriter. Output JSON only.",
            user=prompt,
            max_tokens=100,
            temperature=0.2,
        )
        try:
            result = json.loads(response.strip())
            new_label = result["new_label"]
            if isinstance(new_label, str):
                return new_label
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # Graceful degrade — return original label (text before colon) or ""
        if "：" in bullet:
            return bullet.split("：", 1)[0]
        if ":" in bullet:
            return bullet.split(":", 1)[0]
        return ""
