"""Unit tests for harness.tier1.bullet_injector."""
from harness.tier1.bullet_injector import inject_bullets


SAMPLE_TEX = r"""
\section{实习经历}

\expheader{科尔尼管理咨询}{商业分析实习生}{2025年06月 - 2025年10月}{上海}
\begin{itemize}
    \item \textbf{old:} kearney bullet 1
    \item \textbf{old:} kearney bullet 2
\end{itemize}

\expheader{益普索Ipsos}{市场战略分析实习生}{2025年05月 - 2025年07月}{北京}
\begin{itemize}
    \item \textbf{old:} ipsos bullet 1
\end{itemize}
""".strip()


def _fake_experiences():
    return [
        {"id": "01-kearney", "company": "A.T. Kearney", "company_zh": "科尔尼"},
        {"id": "02-ipsos", "company": "Ipsos", "company_zh": "益普索"},
        {"id": "99-missing", "company": "Nowhere"},
    ]


def test_no_bullets_returns_unchanged():
    tex_out, skipped = inject_bullets(SAMPLE_TEX, {}, _fake_experiences())
    assert tex_out == SAMPLE_TEX
    assert skipped == []


def test_replaces_kearney_block():
    new_bullets = ["new kearney 1", "new kearney 2", "new kearney 3"]
    tex_out, skipped = inject_bullets(
        SAMPLE_TEX,
        {"01-kearney": new_bullets},
        _fake_experiences(),
    )
    assert skipped == []
    assert "new kearney 1" in tex_out
    assert "new kearney 2" in tex_out
    assert "new kearney 3" in tex_out
    # Old kearney bullets gone.
    assert "kearney bullet 1" not in tex_out
    assert "kearney bullet 2" not in tex_out
    # Ipsos block intact.
    assert "ipsos bullet 1" in tex_out


def test_replaces_multiple_blocks():
    tex_out, skipped = inject_bullets(
        SAMPLE_TEX,
        {
            "01-kearney": ["kearney rewrite"],
            "02-ipsos": ["ipsos rewrite a", "ipsos rewrite b"],
        },
        _fake_experiences(),
    )
    assert skipped == []
    assert "kearney rewrite" in tex_out
    assert "ipsos rewrite a" in tex_out
    assert "ipsos rewrite b" in tex_out
    # Old content gone.
    assert "kearney bullet 1" not in tex_out
    assert "ipsos bullet 1" not in tex_out


def test_skips_unknown_experience_id():
    tex_out, skipped = inject_bullets(
        SAMPLE_TEX,
        {"never-heard-of-it": ["x"]},
        _fake_experiences(),
    )
    assert skipped == ["never-heard-of-it"]
    assert tex_out == SAMPLE_TEX


def test_skips_experience_not_in_tex():
    tex_out, skipped = inject_bullets(
        SAMPLE_TEX,
        {"99-missing": ["whatever"]},
        _fake_experiences(),
    )
    assert skipped == ["99-missing"]
    assert tex_out == SAMPLE_TEX


def test_id_stem_used_when_company_does_not_match():
    """Company names with prefixes (numeric / hyphen) — the stem fallback should still match."""
    tex_with_only_id = r"""
\expheader{kearney consulting}{role}{period}{loc}
\begin{itemize}
    \item old
\end{itemize}
""".strip()
    # Experience has an English company that doesn't appear in tex, but the
    # id stem ("kearney") does.
    exps = [{"id": "01-kearney", "company": "A.T. Kearney"}]
    tex_out, skipped = inject_bullets(
        tex_with_only_id, {"01-kearney": ["new"]}, exps
    )
    assert skipped == []
    assert "new" in tex_out
    assert "old" not in tex_out


def test_empty_bullets_list_is_no_op_not_skipped():
    tex_out, skipped = inject_bullets(
        SAMPLE_TEX,
        {"01-kearney": []},
        _fake_experiences(),
    )
    # Empty list is a no-op — neither replaced nor skipped.
    assert skipped == []
    assert tex_out == SAMPLE_TEX


def test_all_empty_bullet_strings_treated_as_skipped():
    tex_out, skipped = inject_bullets(
        SAMPLE_TEX,
        {"01-kearney": ["", "  "]},
        _fake_experiences(),
    )
    assert skipped == ["01-kearney"]
    assert tex_out == SAMPLE_TEX
