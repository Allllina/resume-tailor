"""Test Summary injection into .tex."""
from harness.tier1.summary_injector import inject_summary


SAMPLE_TEX = r"""\documentclass{article}
\begin{document}

\begin{center}
{\LARGE 张明}
\end{center}

\section{教育经历}
content
\section{实习经历}
more
\end{document}
"""


def test_inserts_before_first_section():
    out = inject_summary(SAMPLE_TEX, "兼具 BA 思维与 AI 工具实操。")
    sum_pos = out.index("Summary")
    edu_pos = out.index(r"\section{教育经历}")
    assert sum_pos < edu_pos


def test_summary_block_format():
    out = inject_summary(SAMPLE_TEX, "Test summary.")
    assert r"\section*{Summary}" in out
    assert "Test summary." in out
    assert r"\vspace{0.4em}" in out


def test_empty_summary_returns_unchanged():
    out = inject_summary(SAMPLE_TEX, "")
    assert out == SAMPLE_TEX


def test_whitespace_summary_returns_unchanged():
    out = inject_summary(SAMPLE_TEX, "   \n  ")
    assert out == SAMPLE_TEX


def test_idempotent_replaces_existing():
    once = inject_summary(SAMPLE_TEX, "First summary.")
    twice = inject_summary(once, "Second summary.")
    # Only one Summary section should exist
    assert twice.count(r"\section*{Summary}") == 1
    # And it should contain the new text
    assert "Second summary." in twice
    assert "First summary." not in twice


def test_no_section_falls_back_to_end_document():
    tex = r"""\documentclass{article}
\begin{document}
content with no sections
\end{document}
"""
    out = inject_summary(tex, "fallback summary")
    # Summary inserted before \end{document}
    sum_pos = out.index("fallback summary")
    end_pos = out.index(r"\end{document}")
    assert sum_pos < end_pos


def test_strips_leading_trailing_whitespace():
    out = inject_summary(SAMPLE_TEX, "  \n  Summary text  \n  ")
    assert "  \n  Summary text  \n  " not in out
    assert "Summary text" in out


def test_handles_multiline_summary():
    summary = "Line 1.\n\nLine 2."
    out = inject_summary(SAMPLE_TEX, summary)
    assert "Line 1." in out
    assert "Line 2." in out


def test_handles_section_star_too():
    """\\section*{...} (no number) also counts as a section anchor."""
    tex = r"""\documentclass{article}
\begin{document}
\section*{Profile}
profile content
\end{document}
"""
    out = inject_summary(tex, "Bio summary.")
    sum_pos = out.index("Bio summary")
    profile_pos = out.index(r"\section*{Profile}")
    assert sum_pos < profile_pos
