"""Step 5 — pick the master resume for the chosen lens.

Per HARNESS_DESIGN.md §2.2 Planning sub-stage.

Priority chain (Wave 4 C.1.3 + D11 sample-aware fallback):
    1. Per-user per-lens master   — `<user_dir>/masters/<primary_lens>/master.tex`
    2. User single master fallback (legacy / pre-multi-lens upload)
                                  — `<user_dir>/master.tex`
    3. Project lens private master (gitignored, D11)
                                  — `assets/resume-bank/versions/<lens>/resume.zh.tex`
    4. Project lens sample (committed, D11)
                                  — `assets/resume-bank/versions/<lens>/resume.sample.zh.tex`
    5. Project sibling fallback   — first available sibling (sample preferred,
                                    then private real)

`MasterSelection.metadata.source` is one of:
    - "user_uploaded_per_lens"
    - "user_uploaded_legacy"
    - "user_uploaded"             (DEPRECATED — kept for backward compat with
                                   callers that pass `user_master_path` and
                                   bypass the user_dir flow)
    - "project_master"            (D11 — the private gitignored real master)
    - "project_sample"            (D11 — the committed .sample.zh.tex sibling)
    - "project_sample_fallback"

Wave 2.7 backward compatibility: callers may still construct
MasterSelector with `user_master_path=Path(...)`. When set AND `user_dir`
is None, the selector treats that path as the legacy single-master and
returns it with `metadata.source = "user_uploaded"` (matching the
pre-C.1.3 contract that several existing tests rely on). The new
preferred entrypoint is `user_dir=Path(...)` which enables the full
4-step priority chain above.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


LENS_TO_DIR: dict[str, str] = {
    "A_strategy_research": "A_strategy_research",
    "B_data_analytics": "B_data_analytics",
    "C_product_ops": "C_product_ops",
    "D_finance_markets": "D_finance_markets",
    "HC_human_capital": "HC_human_capital_analytics",  # dir name has _analytics suffix
}


@dataclass
class MasterSelection:
    primary_lens: str
    master_path: Path
    metadata: dict
    fallback_used: bool = False


class MasterMissingError(Exception):
    """Raised when neither primary nor any fallback master exists."""


class MasterSelector:
    def __init__(
        self,
        repo_root: Path,
        user_master_path: Path | None = None,
        user_dir: Path | None = None,
    ):
        """Construct a MasterSelector.

        Wave 4 C.1.3 introduces `user_dir`. When set, `.select(lens)`
        consults `user_dir/masters/<lens>/master.tex` first, then falls
        back to `user_dir/master.tex`, then the project lens sample,
        then the project sibling sample. This is the preferred entrypoint
        for new callers.

        `user_master_path` is the Wave 2.7 entry — kept for backward
        compatibility. When it is set without `user_dir`, the selector
        emits the legacy `metadata.source = "user_uploaded"` to keep the
        existing planning.py mapping working. Callers can plumb both
        kwargs simultaneously; `user_dir` takes precedence and the legacy
        path becomes dead code in that path.
        """
        self._versions_dir = repo_root / "assets" / "resume-bank" / "versions"
        self._user_master_path = (
            Path(user_master_path) if user_master_path else None
        )
        self._user_dir = Path(user_dir) if user_dir else None

    def select(self, primary_lens: str) -> MasterSelection:
        # Priority 1 — per-user per-lens master.
        if self._user_dir is not None:
            per_lens = (
                self._user_dir / "masters" / primary_lens / "master.tex"
            )
            if per_lens.exists():
                meta = self._load_per_lens_metadata(
                    self._user_dir / "masters" / primary_lens
                )
                meta.setdefault("source", "user_uploaded_per_lens")
                meta.setdefault("lens", primary_lens)
                return MasterSelection(
                    primary_lens=primary_lens,
                    master_path=per_lens,
                    metadata=meta,
                    fallback_used=False,
                )

            # Priority 2 — legacy single master under user_dir.
            legacy = self._user_dir / "master.tex"
            if legacy.exists():
                return MasterSelection(
                    primary_lens=primary_lens,
                    master_path=legacy,
                    metadata={
                        "source": "user_uploaded_legacy",
                        "lens": primary_lens,
                    },
                    fallback_used=False,
                )
            # else fall through to priority 3.

        # Wave 2.7 backward compat: explicit user_master_path
        # short-circuits to the legacy single-master shape. New callers
        # should pass `user_dir` instead.
        if (
            self._user_master_path is not None
            and self._user_master_path.exists()
        ):
            return MasterSelection(
                primary_lens=primary_lens,
                master_path=self._user_master_path,
                metadata={"source": "user_uploaded"},
                fallback_used=False,
            )

        if primary_lens not in LENS_TO_DIR:
            raise MasterMissingError(
                f"Unknown lens {primary_lens!r}. Known: {list(LENS_TO_DIR)}"
            )

        # Priority 3 — project lens private master (gitignored real file, if
        # present locally — typical for the maintainer's seeded repo).
        primary_dir = self._versions_dir / LENS_TO_DIR[primary_lens]
        primary_tex = primary_dir / "resume.zh.tex"
        if primary_tex.exists():
            meta = self._load_metadata(primary_dir)
            meta["source"] = "project_master"
            return MasterSelection(
                primary_lens=primary_lens,
                master_path=primary_tex,
                metadata=meta,
                fallback_used=False,
            )

        # Priority 4 — project lens sample (committed `.sample.zh.tex` sibling).
        primary_sample = primary_dir / "resume.sample.zh.tex"
        if primary_sample.exists():
            meta = self._load_sample_metadata(primary_dir)
            meta["source"] = "project_sample"
            return MasterSelection(
                primary_lens=primary_lens,
                master_path=primary_sample,
                metadata=meta,
                fallback_used=False,
            )

        # Priority 5 — project sibling fallback (sample preferred, then real).
        if not self._versions_dir.is_dir():
            raise MasterMissingError(
                f"Versions dir not found: {self._versions_dir}"
            )
        for lens_dir in sorted(self._versions_dir.iterdir()):
            if not lens_dir.is_dir() or lens_dir.name == "custom":
                continue
            sample_tex = lens_dir / "resume.sample.zh.tex"
            if sample_tex.exists():
                meta = self._load_sample_metadata(lens_dir)
                meta["source"] = "project_sample_fallback"
                return MasterSelection(
                    primary_lens=primary_lens,
                    master_path=sample_tex,
                    metadata=meta,
                    fallback_used=True,
                )
            tex = lens_dir / "resume.zh.tex"
            if tex.exists():
                meta = self._load_metadata(lens_dir)
                meta["source"] = "project_sample_fallback"
                return MasterSelection(
                    primary_lens=primary_lens,
                    master_path=tex,
                    metadata=meta,
                    fallback_used=True,
                )

        raise MasterMissingError(
            f"No master resume available for {primary_lens} or any sibling. "
            f"Searched: {self._versions_dir}"
        )

    @staticmethod
    def _load_metadata(lens_dir: Path) -> dict:
        meta_path = lens_dir / "metadata.json"
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _load_sample_metadata(lens_dir: Path) -> dict:
        """D11 — load metadata.sample.json sibling. Falls back to
        metadata.json (the gitignored real one) if the sample sibling
        is absent (e.g., user copied real metadata in but kept .sample.zh.tex).
        Returns {} if neither exists.
        """
        sample_meta = lens_dir / "metadata.sample.json"
        if sample_meta.exists():
            try:
                return json.loads(sample_meta.read_text())
            except json.JSONDecodeError:
                return {}
        return MasterSelector._load_metadata(lens_dir)

    @staticmethod
    def _load_per_lens_metadata(lens_dir: Path) -> dict:
        """Read sibling generated_at.txt + generation_method.txt produced
        by `UserStorage.add_lens_master`. Best-effort; missing siblings
        become None."""
        meta: dict = {}
        ga = lens_dir / "generated_at.txt"
        if ga.exists():
            try:
                txt = ga.read_text().strip()
                if txt:
                    meta["generated_at"] = txt
            except OSError:
                pass
        gm = lens_dir / "generation_method.txt"
        if gm.exists():
            try:
                txt = gm.read_text().strip()
                if txt:
                    meta["generation_method"] = txt
            except OSError:
                pass
        return meta
