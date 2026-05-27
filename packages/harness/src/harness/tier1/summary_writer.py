"""Summary section regenerator.

Per Tier 1 Light Tailoring: Summary may be rewritten freely; bullets
remain. The prompt forbids fabricating skills/companies the candidate
doesn't have.
"""
import asyncio
from typing import Any

from harness.exceptions import SubSkillUnavailable
from harness.llm.pii_filtering_provider import InjectionDetectedError
from harness.llm.protocol import CircuitOpen


SUMMARY_PROMPT = """你是 BA 简历 summary 写作助手。

写一段 2-3 句的 Summary（每句 < 25 字），针对目标岗位，强调候选人匹配度。

输入：
- 目标 JD（节选）：{jd_excerpt}
- 候选人 lens：{lens}
- 候选人核心标签：{tags}
{strategy_block}
约束：
- 不发明候选人未具备的工具或经历
- 不使用 'AI 标点' 如 —— 或 →
- 不写"客户表面诉求"等汇报口吻
- 严禁脱离候选人核心标签编造能力

输出：仅 Summary 文本，不要其他。
"""


def _format_strategy_block(strategy_hints: dict | None) -> str:
    """Format Section H hints into a 策略提示 block.

    Wave 4 Step B.3: when the role-competency-extractor produces a Section
    H ("Resume Strategy Implications"), we inject a compact summary into the
    prompt so the LLM weights "emphasize most" / "top half content"
    correctly. Token budget: total injection capped at ~600 chars.
    """
    if not strategy_hints:
        return ""
    emphasize = (strategy_hints.get("emphasize_most") or "").strip()
    top_half = (strategy_hints.get("top_half_content") or "").strip()
    if not emphasize and not top_half:
        return ""
    parts = ["策略提示："]
    if emphasize:
        parts.append(f"- 优先强调：{emphasize}")
    if top_half:
        parts.append(f"- 上半页落点：{top_half}")
    parts.append("")  # trailing blank line before 约束 block
    return "\n".join(parts) + "\n"


class SummaryWriter:
    def __init__(self, claude: Any):
        self._claude = claude

    async def write(
        self,
        jd_excerpt: str,
        lens: str,
        candidate_tags: list[str],
        strategy_hints: dict | None = None,
    ) -> str:
        if self._claude is None:
            raise SubSkillUnavailable(
                "summary_writer",
                "LLM provider not configured",
                llm_unreachable=True,
            )

        prompt = SUMMARY_PROMPT.format(
            jd_excerpt=jd_excerpt[:500],
            lens=lens,
            tags=", ".join(candidate_tags[:8]) if candidate_tags else "（无标签）",
            strategy_block=_format_strategy_block(strategy_hints),
        )
        try:
            response = await self._claude.call(
                system="You are a precise BA resume Summary writer.",
                user=prompt,
                max_tokens=200,
                temperature=0.3,
            )
        except (asyncio.TimeoutError, ConnectionError, CircuitOpen) as e:
            raise SubSkillUnavailable(
                "summary_writer", str(e), llm_unreachable=True
            ) from e
        except InjectionDetectedError as e:
            raise SubSkillUnavailable(
                "summary_writer",
                f"injection detected: {e}",
                llm_unreachable=False,
            ) from e

        if not isinstance(response, str) or not response.strip():
            raise SubSkillUnavailable(
                "summary_writer",
                "LLM returned empty / non-string response",
                llm_unreachable=False,
            )
        return response.strip()
