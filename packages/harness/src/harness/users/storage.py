"""UserStorage — per-user filesystem layout under data/users/{user_id}/.

Per ADR 0004. Validates user_id against a strict regex (UUID v4 OR slug
3-40 chars [a-z0-9-]) to defend against path traversal. All reads/writes
go through this class so the layout convention is centralized and the
validation can't be bypassed.
"""
from __future__ import annotations

import json
import re
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


_UUID_OR_SLUG = re.compile(
    r"^([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[a-z0-9-]{3,40})$"
)


# Multi-lens onboarding (Wave 4 C.1): centralized lens enum used by
# add_lens_master / has_lens_master / list_lens_masters etc. Mirrors the
# user-profile.schema.json target_lens_default enum exactly.
LENS_ENUM: frozenset[str] = frozenset({
    "A_strategy_research",
    "B_data_analytics",
    "C_product_ops",
    "D_finance_markets",
    "HC_human_capital",
})


class InvalidUserIdError(ValueError):
    pass


class InvalidLensError(ValueError):
    """Raised when a per-lens master operation receives an unknown lens."""


class UserStorage:
    def __init__(self, repo_root: Path):
        self._root = Path(repo_root) / "packages/harness/data/users"

    # ----- path helpers -----

    def _validate_user_id(self, user_id: str) -> None:
        if not user_id or not _UUID_OR_SLUG.match(user_id):
            raise InvalidUserIdError(f"invalid user_id: {user_id!r}")

    def user_dir(self, user_id: str) -> Path:
        self._validate_user_id(user_id)
        return self._root / user_id

    def ensure_user_dir(self, user_id: str) -> Path:
        d = self.user_dir(user_id)
        d.mkdir(parents=True, exist_ok=True)
        (d / "experiences").mkdir(exist_ok=True)
        (d / "runs").mkdir(exist_ok=True)
        return d

    def runs_dir(self, user_id: str) -> Path:
        return self.ensure_user_dir(user_id) / "runs"

    # ----- profile -----

    def load_profile(self, user_id: str) -> dict | None:
        path = self.user_dir(user_id) / "profile.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def save_profile(self, user_id: str, profile: dict) -> None:
        d = self.ensure_user_dir(user_id)
        profile = dict(profile)
        profile["last_updated"] = datetime.now(timezone.utc).isoformat()
        tmp = d / f"profile.json.{secrets.token_hex(4)}.tmp"
        tmp.write_text(json.dumps(profile, ensure_ascii=False, indent=2))
        tmp.replace(d / "profile.json")

    def has_profile(self, user_id: str) -> bool:
        return (self.user_dir(user_id) / "profile.json").exists()

    # ----- master resume -----

    def save_master(
        self,
        user_id: str,
        content: str,
        format: Literal["md", "tex", "docx", "pdf"],
    ) -> Path:
        """Save master resume content. Always writes master.tex.

        Phase 1 stores .tex passthrough; Phase 2 plugs in real parsers
        for .md/.docx/.pdf upstream conversion. Caller passes already-
        converted content here.
        """
        d = self.ensure_user_dir(user_id)
        path = d / "master.tex"
        path.write_text(content)
        return path

    def has_master(self, user_id: str) -> bool:
        return (self.user_dir(user_id) / "master.tex").exists()

    def get_master_tex(self, user_id: str) -> str:
        path = self.user_dir(user_id) / "master.tex"
        if not path.exists():
            raise FileNotFoundError(f"no master.tex for {user_id}")
        return path.read_text()

    # ----- experiences -----

    def list_experiences(self, user_id: str) -> list[dict]:
        index_path = self.user_dir(user_id) / "experiences-index.json"
        if not index_path.exists():
            return []
        try:
            data = json.loads(index_path.read_text())
            return data.get("experiences", []) if isinstance(data, dict) else []
        except (json.JSONDecodeError, OSError):
            return []

    def add_experience(self, user_id: str, file_name: str, content: str) -> str:
        d = self.ensure_user_dir(user_id)
        exp_id = secrets.token_hex(8)
        (d / "experiences" / f"{exp_id}.md").write_text(content)
        existing = self.list_experiences(user_id)
        existing.append({
            "id": exp_id,
            "file_name": file_name,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "char_count": len(content),
            "scoring_status": "queued",
        })
        index_path = d / "experiences-index.json"
        tmp = d / f"experiences-index.json.{secrets.token_hex(4)}.tmp"
        tmp.write_text(json.dumps({"experiences": existing}, ensure_ascii=False, indent=2))
        tmp.replace(index_path)
        return exp_id

    def remove_experience(self, user_id: str, exp_id: str) -> bool:
        d = self.user_dir(user_id)
        existing = self.list_experiences(user_id)
        new_list = [e for e in existing if e.get("id") != exp_id]
        if len(new_list) == len(existing):
            return False
        f = d / "experiences" / f"{exp_id}.md"
        if f.exists():
            f.unlink()
        index_path = d / "experiences-index.json"
        tmp = d / f"experiences-index.json.{secrets.token_hex(4)}.tmp"
        tmp.write_text(json.dumps({"experiences": new_list}, ensure_ascii=False, indent=2))
        tmp.replace(index_path)
        return True

    def get_experience_content(self, user_id: str, exp_id: str) -> str | None:
        f = self.user_dir(user_id) / "experiences" / f"{exp_id}.md"
        if not f.exists():
            return None
        return f.read_text()

    # ----- per-lens masters (Wave 4 C.1 — multi-lens onboarding) -----

    @staticmethod
    def _validate_lens(lens: str) -> None:
        if lens not in LENS_ENUM:
            raise InvalidLensError(
                f"unknown lens: {lens!r}; expected one of {sorted(LENS_ENUM)}"
            )

    def _lens_dir(self, user_id: str, lens: str) -> Path:
        """Resolved per-lens directory under <user_dir>/masters/<lens>/.

        Both user_id and lens are validated before composing the path so
        callers cannot smuggle `..` segments through either argument.
        """
        self._validate_lens(lens)
        return self.user_dir(user_id) / "masters" / lens

    def add_lens_master(
        self,
        user_id: str,
        lens: str,
        tex_content: str,
        method: Literal["user_upload", "rewrite_from_upload_and_bank"],
    ) -> Path:
        """Write `master.tex` + `generated_at.txt` + `generation_method.txt`
        under `data/users/<user_id>/masters/<lens>/`.

        Returns the path to the written master.tex. Idempotent — overwrites
        any existing per-lens master in place. The sibling text files are
        the metadata layer; reading them back is what powers
        `list_lens_masters` and `MasterSelector` priority chain step 1.
        """
        if method not in ("user_upload", "rewrite_from_upload_and_bank"):
            raise ValueError(
                f"invalid method {method!r}; expected user_upload | rewrite_from_upload_and_bank"
            )
        d = self._lens_dir(user_id, lens)
        d.mkdir(parents=True, exist_ok=True)
        master_path = d / "master.tex"
        master_path.write_text(tex_content)
        (d / "generated_at.txt").write_text(
            datetime.now(timezone.utc).isoformat()
        )
        (d / "generation_method.txt").write_text(method)
        return master_path

    def has_lens_master(self, user_id: str, lens: str) -> bool:
        try:
            d = self._lens_dir(user_id, lens)
        except InvalidLensError:
            return False
        return (d / "master.tex").exists()

    def get_lens_master_path(self, user_id: str, lens: str) -> Path | None:
        try:
            d = self._lens_dir(user_id, lens)
        except InvalidLensError:
            return None
        path = d / "master.tex"
        return path if path.exists() else None

    def list_lens_masters(self, user_id: str) -> dict[str, dict]:
        """Inventory every per-lens master present on disk for this user.

        Returns `{<lens>: {path, generated_at, method}}`. Lenses without a
        `master.tex` are omitted. Sibling metadata text files are read
        best-effort — a missing or unreadable sibling becomes `None` in
        the returned dict so callers can still display the master.
        """
        out: dict[str, dict] = {}
        try:
            base = self.user_dir(user_id) / "masters"
        except InvalidUserIdError:
            return out
        if not base.is_dir():
            return out
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            lens = child.name
            if lens not in LENS_ENUM:
                # Defensive: skip anything not matching the canonical enum.
                continue
            master_path = child / "master.tex"
            if not master_path.exists():
                continue
            generated_at: str | None = None
            method: str | None = None
            ga_path = child / "generated_at.txt"
            if ga_path.exists():
                try:
                    generated_at = ga_path.read_text().strip() or None
                except OSError:
                    generated_at = None
            gm_path = child / "generation_method.txt"
            if gm_path.exists():
                try:
                    method = gm_path.read_text().strip() or None
                except OSError:
                    method = None
            out[lens] = {
                "path": master_path,
                "generated_at": generated_at,
                "method": method,
            }
        return out

    def remove_lens_master(self, user_id: str, lens: str) -> bool:
        """Remove `<user_dir>/masters/<lens>/` (master + sibling metadata).

        Returns True when a directory was removed; False if it was absent.
        """
        try:
            d = self._lens_dir(user_id, lens)
        except InvalidLensError:
            return False
        if not d.exists():
            return False
        # Defensive: ensure d is under the storage root before nuking.
        try:
            d.resolve().relative_to(self._root.resolve())
        except (ValueError, OSError):
            return False
        shutil.rmtree(d)
        return True
