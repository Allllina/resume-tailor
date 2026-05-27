"""Compile .tex → .pdf via Docker XeLaTeX. Cached in data/runs/<id>/resume.pdf.

Decision X (per Wave 2.5 plan): use the texlive Docker image rather than a
Python LaTeX renderer (reportlab) so the PDF matches the LaTeX template
1:1. Tradeoff: requires Docker on the host.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger


class CompileError(Exception):
    pass


class PdfToolchainUnavailable(CompileError):
    """The PDF toolchain (Docker + texlive) isn't available — e.g. the Docker
    daemon isn't running or `docker` isn't installed. Distinct from a genuine
    LaTeX compile error so the API can return 503 + a clear, actionable message
    instead of a generic 500 (which the UI would render as garbage in the
    PDF iframe)."""
    pass


def _compile_script() -> Path:
    return (
        Path(__file__).resolve().parents[3] / "scripts" / "compile_pdf.sh"
    )


async def compile_tex_to_pdf(tex_path: Path) -> Path:
    """Compile (or return cached) PDF for the given .tex file.

    Cache rule: if .pdf exists AND mtime ≥ .tex mtime, skip recompile.
    """
    tex_path = Path(tex_path)
    if not tex_path.exists():
        raise CompileError(f"tex not found: {tex_path}")
    pdf_path = tex_path.with_suffix(".pdf")
    if pdf_path.exists() and pdf_path.stat().st_mtime >= tex_path.stat().st_mtime:
        return pdf_path

    script = _compile_script()
    if not script.exists():
        raise CompileError(f"compile_pdf.sh not found at {script}")

    proc = await asyncio.create_subprocess_exec(
        "bash",
        str(script),
        str(tex_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode(errors="replace")[:800]
        # Distinguish "toolchain unavailable" (Docker daemon down / not
        # installed) from a genuine LaTeX error. compile_pdf.sh exits 3 when
        # docker isn't on PATH; a down daemon surfaces "Cannot connect to the
        # Docker daemon" on stderr. Either way the fix is environmental, not a
        # bad .tex — so callers should surface a 503 + setup hint, not a 500.
        low = err.lower()
        if (
            proc.returncode == 3
            or "cannot connect to the docker daemon" in low
            or "is the docker daemon running" in low
            or "docker: command not found" in low
            or "docker not available" in low
        ):
            raise PdfToolchainUnavailable(
                "PDF preview needs Docker + the texlive image, but the Docker "
                "daemon isn't reachable. Start Docker Desktop (and pull "
                "texlive/texlive:latest) to enable PDF rendering."
            )
        raise CompileError(f"xelatex failed (exit {proc.returncode}): {err}")
    if not pdf_path.exists():
        raise CompileError("xelatex returned 0 but no .pdf produced")
    logger.debug(f"pdf compiled: {pdf_path}")
    return pdf_path
