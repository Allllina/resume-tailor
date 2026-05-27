#!/usr/bin/env python3
"""Seed the asset paths from committed `.sample` siblings (D11.3).

For first-time clones: the real asset paths (e.g. `assets/experience-bank/raw/`,
`assets/resume-bank/versions/<lens>/resume.zh.tex`) are gitignored. Only the
anonymized `.sample` siblings are tracked. This script copies the samples to
the real paths so the harness can boot.

Idempotent: if a real path already exists, it's left alone (so users who
upload their own data via the wizard won't get overwritten by re-running
`make seed-sample`).

Two file-shape conventions handled:
  1. Directory siblings:  `<X>.sample/` → `<X>/`
     example: `assets/experience-bank/raw.sample/` → `assets/experience-bank/raw/`
  2. Filename `.sample` infix:  `<X>.sample.<ext>` → `<X>.<ext>`
     example: `assets/experience-bank/index.sample.json` → `assets/experience-bank/index.json`
              `assets/resume-bank/versions/<lens>/resume.sample.zh.tex` → `resume.zh.tex`

Run from anywhere — resolves repo root from this file's path.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"


def _real_path_for_sample_file(sample_path: Path) -> Path:
    """Strip the `.sample` infix from a filename. e.g.
    `index.sample.json` → `index.json`, `resume.sample.zh.tex` → `resume.zh.tex`.
    """
    parts = sample_path.name.split(".")
    # name shape: <stem>.sample.<ext1>[.<ext2>...]
    if "sample" not in parts:
        return sample_path  # nothing to do
    real_parts = [p for p in parts if p != "sample"]
    return sample_path.with_name(".".join(real_parts))


def _real_path_for_sample_dir(sample_dir: Path) -> Path:
    """`<X>.sample` → `<X>` (directory rename only)."""
    name = sample_dir.name
    if not name.endswith(".sample"):
        return sample_dir
    return sample_dir.with_name(name[: -len(".sample")])


def _walk_sample_dirs() -> list[tuple[Path, Path]]:
    """Yield (sample_dir, real_dir) pairs for every `*.sample/` under `assets/`."""
    out = []
    for p in ASSETS.rglob("*.sample"):
        if p.is_dir():
            out.append((p, _real_path_for_sample_dir(p)))
    return out


def _walk_sample_files() -> list[tuple[Path, Path]]:
    """Yield (sample_file, real_file) pairs for every file matching `*.sample.*`
    under `assets/` — but only where the file is NOT inside a `*.sample/`
    directory (those are handled by `_walk_sample_dirs`)."""
    out = []
    for p in ASSETS.rglob("*.sample.*"):
        if not p.is_file():
            continue
        # skip files already inside a *.sample/ dir (handled by dir copy)
        if any(part.endswith(".sample") for part in p.parts):
            continue
        real = _real_path_for_sample_file(p)
        if real == p:
            continue  # nothing changed; skip
        out.append((p, real))
    return out


def _copy_dir(src: Path, dst: Path, log: list[str]) -> None:
    if dst.exists():
        log.append(f"skip dir   {dst.relative_to(REPO)}  (already populated)")
        return
    shutil.copytree(src, dst)
    n = sum(1 for _ in dst.rglob("*") if _.is_file())
    log.append(f"seed dir   {dst.relative_to(REPO)}  ← {src.name} ({n} files)")


def _copy_file(src: Path, dst: Path, log: list[str]) -> None:
    if dst.exists():
        log.append(f"skip file  {dst.relative_to(REPO)}  (already populated)")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    log.append(f"seed file  {dst.relative_to(REPO)}  ← {src.name}")


def main() -> int:
    if not ASSETS.is_dir():
        print(f"error: {ASSETS} not found", file=sys.stderr)
        return 1

    dir_pairs = _walk_sample_dirs()
    file_pairs = _walk_sample_files()

    if not dir_pairs and not file_pairs:
        print("No `.sample` siblings found under assets/. Nothing to seed.")
        return 0

    log: list[str] = []
    for sample, real in dir_pairs:
        _copy_dir(sample, real, log)
    for sample, real in file_pairs:
        _copy_file(sample, real, log)

    print(f"Resume_Optimizer — seed sample data ({len(dir_pairs)} dirs + {len(file_pairs)} files)")
    print()
    for line in log:
        print(f"  {line}")
    print()
    skipped = sum(1 for line in log if line.startswith("skip"))
    seeded = sum(1 for line in log if line.startswith("seed"))
    if skipped:
        print(f"({skipped} target{'s' if skipped != 1 else ''} already populated; skipped to avoid overwriting your data)")
    if seeded:
        print(f"Seeded {seeded} new path{'s' if seeded != 1 else ''}.")
        print("→ You can now run: make backend  (or upload your own resume via the UI to override)")
    else:
        print("→ All targets already had data. Nothing copied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
