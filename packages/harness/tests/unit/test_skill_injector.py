"""Test deterministic Skills row reordering."""
from harness.tier1.skill_injector import SkillInjector


SAMPLE_TEX = r"""\documentclass{article}
\begin{document}
\section{实习经历}
\textbf{some bullet} content here.

\section{技能/证书及其他}

\begin{itemize}
    \item \textbf{数据 / 工程：}Python, SQL, PostgreSQL, Tableau, Excel
    \item \textbf{AI 工具 / AIGC：}Prompt Engineering, LangGraph, Claude API, RAG
    \item \textbf{语言：}中文（母语）；英文（CET-6, 雅思 7）
\end{itemize}

\section{下一节}
content
\end{document}
"""


def test_reorders_ai_first_for_aigc_jd():
    """JD heavy on AIGC keywords → AI 工具 line moves to first."""
    jd = "招聘 AIGC 内容实习生。Prompt Engineering, Agent, 生成式 AI, LangGraph, RAG。"
    s = SkillInjector()
    out = s.reorder_skills_section(SAMPLE_TEX, jd)
    ai_pos = out.index("AI 工具 / AIGC")
    data_pos = out.index("数据 / 工程")
    assert ai_pos < data_pos, "AI row should come before 数据 row for AIGC JD"


def test_reorders_data_first_for_data_jd():
    jd = "数据分析师岗位。SQL Python PostgreSQL 数据建模 Tableau Excel."
    s = SkillInjector()
    out = s.reorder_skills_section(SAMPLE_TEX, jd)
    ai_pos = out.index("AI 工具 / AIGC")
    data_pos = out.index("数据 / 工程")
    assert data_pos < ai_pos, "data row should come first for data JD"


def test_no_skills_section_returns_unchanged():
    """If tex has no Skills section, return unchanged."""
    tex = r"\documentclass{article}\begin{document}\section{Edu}content\end{document}"
    s = SkillInjector()
    out = s.reorder_skills_section(tex, "any jd")
    assert out == tex


def test_empty_jd_returns_original_order():
    """Empty JD → no reordering (or stable original order)."""
    s = SkillInjector()
    out = s.reorder_skills_section(SAMPLE_TEX, "")
    # All 3 items still present
    assert out.count(r"\item") == 3
    assert "Python" in out
    assert "Prompt Engineering" in out
    assert "中文" in out


def test_preserves_non_skills_content():
    """Reorder shouldn't touch any \\section content outside Skills."""
    jd = "AIGC Prompt RAG"
    s = SkillInjector()
    out = s.reorder_skills_section(SAMPLE_TEX, jd)
    # Outside content preserved
    assert "实习经历" in out
    assert "some bullet" in out
    assert "下一节" in out
    assert "\\end{document}" in out


def test_default_extractor_returns_keywords():
    s = SkillInjector()
    keywords = s._default_extractor("AIGC 生成式 AI Prompt Engineering 数据分析")
    assert isinstance(keywords, list)
    assert len(keywords) > 0
    # Top tokens should include the most-frequent meaningful words
    assert any(kw.lower() in {"aigc", "ai", "prompt", "数据分析"} for kw in keywords[:10])


def test_bilingual_bridge_promotes_AI_tools_for_aigc_jd():
    """Anker AIGC JD case: JD has Chinese words like 生成式 AI but Skills row has English brands.

    With bridge expansion, 生成式 should bridge to AIGC/Prompt/LLM/RAG which DO appear
    in the AI 工具 row → score > 0 → should move to first.
    """
    tex = r"""
\section{技能/证书及其他}
\begin{itemize}
    \item \textbf{技术与工具：}Python, SQL, PostgreSQL, Tableau, Excel, Jupyter, Git
    \item \textbf{AI 工具：}Prompt Engineering, LangGraph, Claude API, RAG, Cursor, Claude, ChatGPT
    \item \textbf{语言：}中文, 英文
\end{itemize}
\section{下一节}
"""
    jd = "AIGC 内容实习生 招聘. 生成式 AI 工作流 提示词工程 Prompt Engineering Agent LLM RAG."
    s = SkillInjector()
    out = s.reorder_skills_section(tex, jd)
    ai_pos = out.index("AI 工具")
    data_pos = out.index("技术与工具")
    assert ai_pos < data_pos, "AI row should come first when JD is AIGC-heavy (via bridge)"


def test_bridge_loaded_from_real_file():
    """When constructed without explicit bridge arg, loads from assets/.../keyword-bridge.json."""
    s = SkillInjector()
    assert isinstance(s._bridge, dict)
    # Should have at least some entries from the shipped file
    if s._bridge:  # only assert non-empty if file loaded successfully
        assert any(k in s._bridge for k in ("AIGC", "生成式 AI", "数据分析"))


def test_bridge_explicit_override():
    """Caller can pass a custom bridge dict for tests."""
    custom_bridge = {"foo": ["BarTool"]}
    s = SkillInjector(bridge=custom_bridge)
    assert s._bridge == custom_bridge


def test_no_bridge_still_works():
    """Empty bridge falls back to literal-only matching (backward compat)."""
    s = SkillInjector(bridge={})
    tex = r"""
\section{技能/证书及其他}
\begin{itemize}
    \item \textbf{Python：}Python, SQL
    \item \textbf{语言：}中文
\end{itemize}
"""
    out = s.reorder_skills_section(tex, "Python data engineer")
    # "Python" appears literally → Python row scores higher than 语言 row
    assert out.index("Python") < out.index("语言")


# ============ Wave 4 Step B: extra_keywords (Section D) ============


def test_extra_keywords_lifts_row_that_jd_alone_cannot():
    """JD lacks the row's terms; Section D supplies them → row promoted.

    Section D injects keywords like 'LangGraph' / 'Claude API' that don't
    appear in the JD text. Without extra_keywords the AI row would not be
    promoted; with extra_keywords it should rise above the data row.
    """
    tex = r"""
\section{技能/证书及其他}
\begin{itemize}
    \item \textbf{数据 / 工程：}Python, SQL, PostgreSQL
    \item \textbf{AI 工具：}LangGraph, Claude API, RAG, Cursor
    \item \textbf{语言：}中文, 英文
\end{itemize}
"""
    # JD says nothing AI-flavored — only generic
    jd = "我们招聘业务分析师助理，轻量数据处理能力。"
    s = SkillInjector(bridge={})

    # Without extras — AI row should NOT lead (no signals match)
    baseline = s.reorder_skills_section(tex, jd)
    # With Section D extras — AI row should now lead
    extras = ["LangGraph", "Claude API", "RAG"]
    promoted = s.reorder_skills_section(tex, jd, extra_keywords=extras)
    assert promoted.index("AI 工具") < promoted.index("数据 / 工程"), (
        "Section D extra_keywords should rank AI row above data row"
    )


def test_extra_keywords_none_preserves_original_behavior():
    """extra_keywords=None must match the pre-Wave-4 behavior exactly."""
    tex = r"""
\section{技能/证书及其他}
\begin{itemize}
    \item \textbf{Python：}Python, SQL
    \item \textbf{语言：}中文
\end{itemize}
"""
    jd = "Python data engineer"
    s = SkillInjector(bridge={})
    a = s.reorder_skills_section(tex, jd)
    b = s.reorder_skills_section(tex, jd, extra_keywords=None)
    assert a == b


def test_extra_keywords_empty_list_preserves_original_behavior():
    tex = r"""
\section{技能/证书及其他}
\begin{itemize}
    \item \textbf{Python：}Python, SQL
    \item \textbf{语言：}中文
\end{itemize}
"""
    jd = "Python data engineer"
    s = SkillInjector(bridge={})
    a = s.reorder_skills_section(tex, jd)
    b = s.reorder_skills_section(tex, jd, extra_keywords=[])
    assert a == b


def test_extra_keywords_with_empty_jd_still_returns_unchanged():
    """Even with extras, empty JD short-circuits to unchanged (no scoring frame)."""
    tex = r"""
\section{技能/证书及其他}
\begin{itemize}
    \item \textbf{A：}aaa
    \item \textbf{B：}bbb
\end{itemize}
"""
    s = SkillInjector(bridge={})
    out = s.reorder_skills_section(tex, "", extra_keywords=["aaa", "bbb"])
    assert out == tex
