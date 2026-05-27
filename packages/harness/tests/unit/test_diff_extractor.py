"""Unit tests for tier1/diff_extractor.py."""
from harness.tier1.diff_extractor import extract_skills_block, extract_summary_block


def test_extract_skills_block_typical():
    tex = r"""
\section{技能与证书}
\begin{itemize}
    \item 数据分析 · Python · SQL
    \item AI 工具 · Claude · Prompt Engineering
\end{itemize}
"""
    out = extract_skills_block(tex)
    assert "数据分析" in out
    assert "AI 工具" in out
    assert " · " in out


def test_extract_skills_block_empty_when_no_section():
    tex = r"\section{Projects}\begin{itemize}\item one\end{itemize}"
    assert extract_skills_block(tex) == ""


def test_extract_skills_block_empty_when_no_items():
    tex = r"\section{技能}\begin{itemize}\end{itemize}"
    assert extract_skills_block(tex) == ""


def test_extract_summary_block_present():
    tex = r"""\section*{Summary}
This is the summary text.
\vspace{0.4em}

\section{Skills}"""
    assert "summary text" in extract_summary_block(tex)


def test_extract_summary_block_absent():
    tex = r"\section{Skills}\begin{itemize}\item x\end{itemize}"
    assert extract_summary_block(tex) == ""


def test_extract_summary_block_strips_whitespace():
    tex = "\\section*{Summary}\n   trimmed   \n\\vspace{0.4em}"
    assert extract_summary_block(tex) == "trimmed"
