#!/usr/bin/env bash
# Compile a .tex to .pdf via texlive Docker. CJK-capable image.
#
# Usage: compile_pdf.sh <abs-path-to-input.tex>
# Output: same dir as input, replaces .tex extension with .pdf.
#
# Image: texlive/texlive:latest is the official full distribution and includes
# xelatex + CJK fonts. If pulling latest is slow, pin a specific tag (e.g.
# texlive/texlive:TL2024-historic) for reproducibility.
set -e

INPUT_TEX="$1"
if [ -z "$INPUT_TEX" ] || [ ! -f "$INPUT_TEX" ]; then
  echo "compile_pdf.sh: input .tex not found: $INPUT_TEX" >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "compile_pdf.sh: docker not available on PATH" >&2
  exit 3
fi

WORKDIR="$(dirname "$INPUT_TEX")"
TEX_NAME="$(basename "$INPUT_TEX")"

docker run --rm \
  -v "$WORKDIR":/workdir \
  -w /workdir \
  texlive/texlive:latest \
  xelatex -interaction=nonstopmode "$TEX_NAME" >/dev/null
