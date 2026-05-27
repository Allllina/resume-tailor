"""Prompt constants for optional quality-pass LLM review."""
from __future__ import annotations


_PASS_1_5_SYSTEM_PROMPT = (
    "You are quality-pass-runner Pass 1.5. Review Chinese resume text for "
    "readability, English direct-translation phrasing, non-universal acronyms, "
    "and awkward business Chinese. Return concise JSON if used by a caller."
)


_PASS_2_SYSTEM_PROMPT = (
    "You are quality-pass-runner Pass 2 enforcing R-11 AI-tone cleanup. Find "
    "LLM-typical resume language in English and Chinese while preserving terms "
    "that appear in the JD. Return concise JSON if used by a caller."
)


def render_pass_1_5_user_prompt(*, target_market: str, resume_text: str) -> str:
    return (
        f"Target market: {target_market}\n\n"
        "Resume text:\n"
        f"{resume_text}\n\n"
        "Flag Chinese readability issues and propose idiomatic replacements."
    )


def render_pass_2_user_prompt(*, target_market: str, resume_text: str, jd_text: str) -> str:
    return (
        f"Target market: {target_market}\n\n"
        "JD terms to protect:\n"
        f"{jd_text}\n\n"
        "Resume text:\n"
        f"{resume_text}\n\n"
        "Flag AI-tone phrases and replacements, skipping JD-native terms."
    )


__all__ = [
    "_PASS_1_5_SYSTEM_PROMPT",
    "_PASS_2_SYSTEM_PROMPT",
    "render_pass_1_5_user_prompt",
    "render_pass_2_user_prompt",
]
