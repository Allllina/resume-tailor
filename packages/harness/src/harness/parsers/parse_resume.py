"""parse_resume — convert .md / .tex / .docx / .pdf bytes to a unified
ParsedResume dataclass with raw_tex, sections dict, confidence, warnings.

Per Wave 2.7 P2.1. Confidence floors:
  .tex passthrough → 1.0 (or 0.85 if shape warnings).
  .md (deterministic transformer) → 0.95.
  .docx (heuristic walk over paragraphs) → 0.85.
  .pdf (text extraction + heading regex) → 0.6 (UI surfaces this for review).
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Literal


# ---------------- public types ----------------


@dataclass
class ParsedResume:
    format: str
    raw_tex: str
    sections: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)


Format = Literal["md", "tex", "docx", "pdf"]


# ---------------- entry point ----------------


def parse_resume(content: bytes, format: Format) -> ParsedResume:
    """Dispatch by format. content is always raw bytes from upload."""
    if format == "tex":
        return _parse_tex(content)
    if format == "md":
        return _parse_md(content)
    if format == "docx":
        return _parse_docx(content)
    if format == "pdf":
        return _parse_pdf(content)
    raise ValueError(f"unsupported format: {format!r}")


# ---------------- helpers ----------------


_LATEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _escape_latex(s: str) -> str:
    """Escape LaTeX special characters. Order matters: backslash first so we
    don't re-escape the backslashes we just inserted."""
    out: list[str] = []
    for ch in s:
        if ch in _LATEX_ESCAPE_MAP:
            out.append(_LATEX_ESCAPE_MAP[ch])
        else:
            out.append(ch)
    return "".join(out)


_SECTION_RE = re.compile(r"\\section\*?\{([^}]+)\}")


def _extract_tex_sections(text: str) -> dict[str, str]:
    """Walk \\section{..} / \\section*{..} markers and assign body text
    until the next section to that section."""
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections[title] = body
    return sections


_DEFAULT_DOCUMENTCLASS = (
    "\\documentclass[11pt,a4paper]{article}\n"
    "\\usepackage[utf8]{inputenc}\n"
    "\\usepackage[T1]{fontenc}\n"
    "\\usepackage{xcolor}\n"
    "\\begin{document}\n"
)
_DEFAULT_DOC_END = "\n\\end{document}\n"


# ---------------- .tex ----------------


def _parse_tex(content: bytes) -> ParsedResume:
    text = content.decode("utf-8", errors="replace")
    warnings: list[str] = []
    if "\\documentclass" not in text:
        warnings.append("missing \\documentclass — file may not be a complete LaTeX document")
    if "\\begin{document}" not in text:
        warnings.append("missing \\begin{document} — file may not be a complete LaTeX document")
    sections = _extract_tex_sections(text)
    confidence = 1.0 if not warnings else 0.85
    return ParsedResume(
        format="tex",
        raw_tex=text,
        sections=sections,
        confidence=confidence,
        warnings=warnings,
    )


# ---------------- .md ----------------


_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _md_inline_to_tex(line: str) -> str:
    """Convert markdown inline emphasis to LaTeX, escaping all non-emphasis
    text. We tokenize on **bold** / *italic* so the emphasis content gets
    \\textbf{}/\\textit{} and the surrounding plain text gets _escape_latex
    applied (so & % $ # _ { } ~ ^ \\ are all safely converted).

    Markdown emphasis is intentionally narrow — only **bold**, *italic*.
    """
    # First, splice out **bold** spans and *italic* spans, escaping the
    # plain segments and wrapping the emphasis segments with the right
    # LaTeX commands.

    # Combined regex: capture either bold or italic in named groups
    pattern = re.compile(
        r"(?P<bold>\*\*(?P<bold_inner>.+?)\*\*)"
        r"|(?P<italic>(?<!\*)\*(?!\*)(?P<italic_inner>.+?)(?<!\*)\*(?!\*))"
    )
    out: list[str] = []
    last = 0
    for m in pattern.finditer(line):
        # Plain text before this match — escape it
        out.append(_escape_latex(line[last:m.start()]))
        if m.group("bold") is not None:
            inner = m.group("bold_inner")
            out.append(r"\textbf{" + _escape_latex(inner) + "}")
        else:
            inner = m.group("italic_inner")
            out.append(r"\textit{" + _escape_latex(inner) + "}")
        last = m.end()
    out.append(_escape_latex(line[last:]))
    return "".join(out)


def _parse_md(content: bytes) -> ParsedResume:
    text = content.decode("utf-8", errors="replace")
    body_lines: list[str] = []
    sections: dict[str, str] = {}
    current_section: str | None = None
    current_body: list[str] = []

    in_itemize = False

    def _close_itemize():
        nonlocal in_itemize
        if in_itemize:
            body_lines.append(r"\end{itemize}")
            in_itemize = False

    def _flush_section():
        if current_section is not None:
            sections[current_section] = "\n".join(current_body).strip()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.lstrip()

        # Bullets — group consecutive `- ` lines into an itemize block
        if stripped.startswith("- "):
            if not in_itemize:
                body_lines.append(r"\begin{itemize}")
                in_itemize = True
            item_text = _md_inline_to_tex(stripped[2:])
            body_lines.append(r"  \item " + item_text)
            current_body.append(stripped[2:])
            continue
        else:
            _close_itemize()

        # Headings
        if stripped.startswith("### "):
            _flush_section()
            current_section = stripped[4:].strip()
            current_body = []
            body_lines.append(r"\subsection{" + _escape_latex(current_section) + "}")
            continue
        if stripped.startswith("## "):
            _flush_section()
            current_section = stripped[3:].strip()
            current_body = []
            body_lines.append(r"\section{" + _escape_latex(current_section) + "}")
            continue
        if stripped.startswith("# "):
            _flush_section()
            current_section = stripped[2:].strip()
            current_body = []
            body_lines.append(r"\section*{" + _escape_latex(current_section) + "}")
            continue

        # Plain paragraph line — escape special chars and apply inline
        # transforms (bold / italic). _md_inline_to_tex handles both.
        if stripped:
            body_lines.append(_md_inline_to_tex(stripped))
            current_body.append(stripped)
        else:
            body_lines.append("")
            current_body.append("")

    _close_itemize()
    _flush_section()

    raw_tex = _DEFAULT_DOCUMENTCLASS + "\n".join(body_lines) + _DEFAULT_DOC_END
    return ParsedResume(
        format="md",
        raw_tex=raw_tex,
        sections=sections,
        confidence=0.95,
        warnings=[],
    )


# ---------------- .docx ----------------


def _parse_docx(content: bytes) -> ParsedResume:
    from docx import Document  # imported lazily to keep harness import-cost low

    warnings: list[str] = []
    try:
        doc = Document(io.BytesIO(content))
    except Exception as e:
        return ParsedResume(
            format="docx",
            raw_tex="",
            sections={},
            confidence=0.0,
            warnings=[f"failed to open docx: {e}"],
        )

    sections: dict[str, str] = {}
    body_parts: list[str] = []
    current_title: str | None = None
    current_body: list[str] = []

    def _flush():
        if current_title is not None:
            sections[current_title] = "\n".join(current_body).strip()

    for para in doc.paragraphs:
        text = (para.text or "").strip()
        if not text:
            continue
        style_name = ""
        try:
            style_name = (para.style.name or "") if para.style else ""
        except Exception:
            style_name = ""

        if style_name.startswith("Heading"):
            _flush()
            current_title = text
            current_body = []
            body_parts.append(r"\section*{" + _escape_latex(text) + "}")
            continue

        # Plain paragraph
        body_parts.append(_escape_latex(text))
        if current_title is None:
            # text before any heading — keep as a leading "" pseudo-section
            current_title = ""
            current_body = []
        current_body.append(text)

    _flush()

    raw_tex = _DEFAULT_DOCUMENTCLASS + "\n".join(body_parts) + _DEFAULT_DOC_END
    return ParsedResume(
        format="docx",
        raw_tex=raw_tex,
        sections=sections,
        confidence=0.85,
        warnings=warnings,
    )


# ---------------- .pdf ----------------


_KNOWN_HEADINGS = (
    "SUMMARY",
    "OBJECTIVE",
    "EDUCATION",
    "EXPERIENCE",
    "WORK EXPERIENCE",
    "PROFESSIONAL EXPERIENCE",
    "SKILLS",
    "PROJECTS",
    "PUBLICATIONS",
    "AWARDS",
    "CERTIFICATIONS",
    # Chinese
    "教育背景",
    "工作经历",
    "项目经历",
    "技能",
    "个人简介",
    "实习经历",
    "获奖经历",
)
_KNOWN_HEADINGS_SET = {h.upper() for h in _KNOWN_HEADINGS}


def _looks_like_heading(line: str) -> bool:
    """A line is a heading if it's short and either:
      - matches a known heading (CN or EN), OR
      - is ALL-CAPS Latin (and not too long).
    """
    s = line.strip()
    if not s or len(s) > 60:
        return False
    if s.upper() in _KNOWN_HEADINGS_SET:
        return True
    # ALL-CAPS Latin with at least 3 alpha chars and no lowercase
    has_alpha = False
    for ch in s:
        if ch.isalpha():
            has_alpha = True
            if ch.islower():
                return False
    return has_alpha and len(s) <= 40


def _parse_pdf(content: bytes) -> ParsedResume:
    import pdfplumber

    warnings = ["PDF extraction is approximate — please review the parsed sections"]
    text_parts: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    text_parts.append(t)
    except Exception as e:
        return ParsedResume(
            format="pdf",
            raw_tex="",
            sections={},
            confidence=0.0,
            warnings=[f"failed to extract pdf: {e}"],
        )

    full_text = "\n".join(text_parts)
    sections: dict[str, str] = {}
    body_parts: list[str] = []
    current_title: str | None = None
    current_body: list[str] = []

    def _flush():
        if current_title is not None:
            sections[current_title] = "\n".join(current_body).strip()

    for raw_line in full_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _looks_like_heading(line):
            _flush()
            current_title = line
            current_body = []
            body_parts.append(r"\section*{" + _escape_latex(line) + "}")
            continue
        body_parts.append(_escape_latex(line))
        if current_title is None:
            current_title = ""
            current_body = []
        current_body.append(line)

    _flush()

    raw_tex = _DEFAULT_DOCUMENTCLASS + "\n".join(body_parts) + _DEFAULT_DOC_END
    return ParsedResume(
        format="pdf",
        raw_tex=raw_tex,
        sections=sections,
        confidence=0.6,
        warnings=warnings,
    )
