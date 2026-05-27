"""Summary section injection into .tex artifact.

Per Wave 1 lacuna: SummaryWriter generates Summary text but the original
loop discarded it (master has no Summary section). This injector
inserts the regenerated Summary right before the first \\section{...}
in the document.

If summary_text is empty / whitespace, returns tex unchanged.
If no \\section{...} found, falls back to inserting before \\end{document}.
"""
import re


_SECTION_RE = re.compile(r"\\section\*?\{[^}]+\}")
_END_DOCUMENT_RE = re.compile(r"\\end\{document\}")


def inject_summary(tex: str, summary_text: str) -> str:
    """Insert Summary block before first \\section{...} (or \\end{document} if no sections).

    Format inserted:
      \\section*{Summary}
      <summary_text>
      \\vspace{0.4em}

    Idempotent: if a `\\section*{Summary}` already exists, REPLACE its
    content instead of injecting a second one.
    """
    if not summary_text or not summary_text.strip():
        return tex

    summary_text = summary_text.strip()
    block = f"\\section*{{Summary}}\n{summary_text}\n\\vspace{{0.4em}}\n\n"

    # Idempotency: replace existing Summary section if present
    existing = re.compile(
        r"\\section\*?\{Summary\}\n.*?\\vspace\{0\.4em\}\n\n",
        re.DOTALL,
    )
    if existing.search(tex):
        # re.sub treats backslashes in repl as escape sequences — pass via lambda
        return existing.sub(lambda _m: block, tex, count=1)

    # Insert before first \section{...}
    section_match = _SECTION_RE.search(tex)
    if section_match:
        insert_at = section_match.start()
        return tex[:insert_at] + block + tex[insert_at:]

    # Fallback: before \end{document}
    end_match = _END_DOCUMENT_RE.search(tex)
    if end_match:
        insert_at = end_match.start()
        return tex[:insert_at] + block + tex[insert_at:]

    # Last resort: append at end
    return tex + "\n" + block
