"""Unit tests for pdf/compiler.py — Docker subprocess mocked.

Tests the cache rule + error handling without requiring Docker on the host.
"""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from harness.pdf.compiler import CompileError, PdfToolchainUnavailable, compile_tex_to_pdf


def _make_proc(returncode: int, stderr: bytes = b""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(b"", stderr))
    return proc


@pytest.mark.asyncio
async def test_raises_when_tex_missing(tmp_path):
    with pytest.raises(CompileError, match="tex not found"):
        await compile_tex_to_pdf(tmp_path / "nope.tex")


@pytest.mark.asyncio
async def test_compiles_when_pdf_absent(tmp_path):
    tex = tmp_path / "resume.tex"
    tex.write_text("\\documentclass{article}\\begin{document}hi\\end{document}")
    pdf = tex.with_suffix(".pdf")

    async def fake_exec(*args, **kwargs):
        # Simulate xelatex producing a .pdf
        pdf.write_bytes(b"%PDF-1.4 fake")
        return _make_proc(0)

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        result = await compile_tex_to_pdf(tex)

    assert result == pdf
    assert pdf.exists()


@pytest.mark.asyncio
async def test_uses_cache_when_pdf_newer(tmp_path):
    tex = tmp_path / "resume.tex"
    tex.write_text("hi")
    pdf = tex.with_suffix(".pdf")
    pdf.write_bytes(b"%PDF-1.4 cached")
    # Make pdf strictly newer than tex
    import os, time
    future = time.time() + 60
    os.utime(pdf, (future, future))

    called = MagicMock()
    with patch("asyncio.create_subprocess_exec", side_effect=called):
        result = await compile_tex_to_pdf(tex)

    assert result == pdf
    called.assert_not_called()


@pytest.mark.asyncio
async def test_recompiles_when_tex_newer_than_pdf(tmp_path):
    tex = tmp_path / "resume.tex"
    tex.write_text("hi")
    pdf = tex.with_suffix(".pdf")
    pdf.write_bytes(b"%PDF-1.4 stale")
    # Make tex strictly newer than pdf
    import os, time
    future = time.time() + 60
    os.utime(tex, (future, future))

    async def fake_exec(*args, **kwargs):
        pdf.write_bytes(b"%PDF-1.4 fresh")
        return _make_proc(0)

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec) as ex:
        await compile_tex_to_pdf(tex)
    ex.assert_called_once()


@pytest.mark.asyncio
async def test_raises_on_subprocess_failure(tmp_path):
    tex = tmp_path / "resume.tex"
    tex.write_text("hi")

    async def fake_exec(*args, **kwargs):
        return _make_proc(1, stderr=b"xelatex: file not found")

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        with pytest.raises(CompileError, match="xelatex failed"):
            await compile_tex_to_pdf(tex)


@pytest.mark.asyncio
async def test_raises_when_subprocess_succeeds_but_no_pdf(tmp_path):
    tex = tmp_path / "resume.tex"
    tex.write_text("hi")

    async def fake_exec(*args, **kwargs):
        # Returns 0 but produces no .pdf
        return _make_proc(0)

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        with pytest.raises(CompileError, match="no .pdf produced"):
            await compile_tex_to_pdf(tex)


@pytest.mark.asyncio
async def test_toolchain_unavailable_when_docker_daemon_down(tmp_path):
    """Docker daemon down → PdfToolchainUnavailable (→ API 503), not a generic
    CompileError (→ 500 that the UI rendered as 乱码). See live smoke 2026-05-24."""
    tex = tmp_path / "resume.tex"
    tex.write_text("hi")

    async def fake_exec(*args, **kwargs):
        return _make_proc(
            1,
            stderr=b"Cannot connect to the Docker daemon at unix:///var/run/docker.sock. "
            b"Is the docker daemon running?",
        )

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        with pytest.raises(PdfToolchainUnavailable):
            await compile_tex_to_pdf(tex)


@pytest.mark.asyncio
async def test_toolchain_unavailable_on_docker_missing_exit_3(tmp_path):
    """compile_pdf.sh exits 3 when docker isn't on PATH → PdfToolchainUnavailable."""
    tex = tmp_path / "resume.tex"
    tex.write_text("hi")

    async def fake_exec(*args, **kwargs):
        return _make_proc(3, stderr=b"compile_pdf.sh: docker not available on PATH")

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        with pytest.raises(PdfToolchainUnavailable):
            await compile_tex_to_pdf(tex)


@pytest.mark.asyncio
async def test_genuine_latex_error_is_compile_error_not_toolchain(tmp_path):
    """A real LaTeX error stays a plain CompileError (→ 500), NOT toolchain (503)."""
    tex = tmp_path / "resume.tex"
    tex.write_text("hi")

    async def fake_exec(*args, **kwargs):
        return _make_proc(1, stderr=b"! LaTeX Error: Environment foo undefined.")

    with patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
        with pytest.raises(CompileError) as excinfo:
            await compile_tex_to_pdf(tex)
    assert not isinstance(excinfo.value, PdfToolchainUnavailable)
