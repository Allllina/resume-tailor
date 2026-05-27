"""User upload + profile endpoints (Wave 2.7 P2.3 + P3 backend touches).

All endpoints read X-User-Id header (default default) and
namespace storage under data/users/{user_id}/.

  POST   /api/users/profile/upload-resume   — multipart 'file', single resume
  POST   /api/users/experiences/upload      — multipart 'files', batch (cap 30)
  GET    /api/users/me                      — profile + counts
  GET    /api/users/me/master/tex           — master.tex content (text/x-tex)
  PATCH  /api/users/me                      — update candidate_names / target_market_default
  DELETE /api/users/me                      — cascade delete user_dir
  DELETE /api/users/experiences/{exp_id}    — remove one experience

Wave 4 C.1.4 multi-lens onboarding:
  POST   /api/users/lens-targets            — primary + secondary lens picks
  POST   /api/users/masters/generate        — schedule per-lens master generation
  GET    /api/users/masters                 — per-lens master inventory + status
  DELETE /api/users/masters/{lens}          — remove a per-lens master
"""
from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.responses import PlainTextResponse
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from harness.config import config
from harness.exceptions import SubSkillUnavailable
from harness.llm.factory import get_llm_provider
from harness.llm.health import get_monitor
from harness.parsers import parse_resume
from harness.users.auto_scorer import score_experience
from harness.users.storage import (
    InvalidLensError,
    InvalidUserIdError,
    LENS_ENUM,
    UserStorage,
)


router = APIRouter()

_DEFAULT_USER_ID = "default"

_RESUME_MAX_BYTES = 5 * 1024 * 1024  # 5MB — typical PDF résumés are 200-1000KB
_EXP_MAX_BYTES = 2 * 1024 * 1024  # 2MB — accommodate .docx / .pdf experiences
_EXP_MAX_FILES = 30  # per experience-upload-input.schema.json maxItems


# ---------------- helpers ----------------


def _resolve_user_id(x_user_id: Optional[str]) -> str:
    return x_user_id or _DEFAULT_USER_ID


def _detect_format(file_name: str) -> str | None:
    name = (file_name or "").lower()
    for ext in (".md", ".tex", ".docx", ".pdf"):
        if name.endswith(ext):
            return ext[1:]
    return None


def _storage() -> UserStorage:
    return UserStorage(config.repo_root)


def _decode_text(content: bytes) -> str:
    """Best-effort text decode for .md/.tex experience storage."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("utf-8", errors="replace")


# ---------------- POST /api/users/profile/upload-resume ----------------


@router.post("/api/users/profile/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(default=None),
):
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    fmt = _detect_format(file.filename or "")
    if fmt is None:
        raise HTTPException(
            400,
            f"unsupported format for filename {file.filename!r}; expected .md/.tex/.docx/.pdf",
        )

    content = await file.read()
    if not content:
        raise HTTPException(400, "empty file")
    if len(content) > _RESUME_MAX_BYTES:
        raise HTTPException(
            413,
            f"file too large: {len(content)} bytes > {_RESUME_MAX_BYTES} (200KB cap)",
        )

    try:
        parsed = parse_resume(content, format=fmt)
    except Exception as e:
        logger.warning(f"resume parse failed for user {user_id}: {e}")
        raise HTTPException(400, f"failed to parse {fmt} resume: {e}")

    if not parsed.raw_tex:
        raise HTTPException(400, "parsed resume is empty (parser produced no LaTeX)")

    # Persist as master.tex (always .tex on disk per UserStorage contract)
    storage.save_master(user_id, parsed.raw_tex, format="tex")

    # Update profile (preserve existing fields)
    profile = storage.load_profile(user_id) or {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_names": [],
    }
    profile["master_format"] = fmt
    profile["master_uploaded_at"] = datetime.now(timezone.utc).isoformat()
    profile["master_parse_confidence"] = parsed.confidence
    # Persist the underlying parse signals so /resume can show users WHY
    # the score is what it is — format alone doesn't explain a 60% PDF
    # or an 85% .docx without surfacing the parser's actual findings.
    profile["master_parse_meta"] = {
        "format": fmt,
        "file_bytes": len(content),
        "warnings": parsed.warnings,
        "section_count": len(parsed.sections),
        "section_names": list(parsed.sections.keys())[:32],  # cap; some parsers emit many
        "raw_tex_bytes": len(parsed.raw_tex.encode("utf-8")) if parsed.raw_tex else 0,
    }
    storage.save_profile(user_id, profile)

    return {
        "ok": True,
        "format": fmt,
        "confidence": parsed.confidence,
        "warnings": parsed.warnings,
        "section_count": len(parsed.sections),
    }


# ---------------- POST /api/users/experiences/upload ----------------


def _score_and_persist(user_id: str, exp_id: str, content: str) -> None:
    """Background task: call LLM auto-scorer + write 3-axis fields back
    into experiences-index.json for this exp_id."""
    try:
        import asyncio

        llm = get_llm_provider()
        scoring = asyncio.run(score_experience(content, llm))
    except Exception as e:
        logger.warning(f"auto-scorer crashed for {user_id}/{exp_id}: {e}")
        from harness.users.auto_scorer import fallback_score
        scoring = fallback_score()

    _persist_scoring(user_id, exp_id, scoring)


async def _score_one(exp_id: str, content: str, llm) -> tuple[str, dict]:
    """Single-experience scoring coroutine, used by both single + batch paths."""
    try:
        scoring = await score_experience(content, llm)
    except Exception as e:
        logger.warning(f"auto-scorer crashed for {exp_id}: {e}")
        from harness.users.auto_scorer import fallback_score
        scoring = fallback_score()
    return exp_id, scoring


def _score_batch_in_parallel(user_id: str, contents_by_id: dict[str, str]) -> None:
    """Run all queued experiences through the auto-scorer concurrently.

    Replaces the previous one-task-per-experience pattern where FastAPI's
    BackgroundTasks scheduler ran them serially, multiplying the per-call
    LLM timeout by N. With asyncio.gather the total wall-clock is bounded
    by max(single_call_time, timeout), not N × timeout.
    """
    if not contents_by_id:
        return
    import asyncio

    try:
        llm = get_llm_provider()
    except Exception as e:
        logger.warning(f"auto-scorer batch: LLM init failed → fallback all ({type(e).__name__}: {e})")
        from harness.users.auto_scorer import fallback_score
        for exp_id in contents_by_id:
            _persist_scoring(user_id, exp_id, fallback_score())
        return

    async def _run() -> list[tuple[str, dict]]:
        return await asyncio.gather(
            *(_score_one(eid, txt, llm) for eid, txt in contents_by_id.items()),
            return_exceptions=False,
        )

    try:
        results = asyncio.run(_run())
    except Exception as e:
        logger.warning(f"auto-scorer batch gather crashed → fallback all ({type(e).__name__}: {e})")
        from harness.users.auto_scorer import fallback_score
        for exp_id in contents_by_id:
            _persist_scoring(user_id, exp_id, fallback_score())
        return

    for exp_id, scoring in results:
        _persist_scoring(user_id, exp_id, scoring)


def _persist_scoring(user_id: str, exp_id: str, scoring: dict) -> None:
    """Write a finished scoring dict back into experiences-index.json. Split
    out from _score_and_persist so the batch path can call it from inside an
    asyncio.gather without re-running the LLM."""
    storage = _storage()
    try:
        d = storage.user_dir(user_id)
    except InvalidUserIdError:
        return
    index_path = d / "experiences-index.json"
    if not index_path.exists():
        return
    try:
        data = json.loads(index_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    items = data.get("experiences", []) if isinstance(data, dict) else []
    updated = False
    for item in items:
        if item.get("id") == exp_id:
            item["scoring_status"] = "done"
            item["recognition_per_industry"] = scoring.get("recognition_per_industry", {})
            item["vertical_fit_per_lens"] = scoring.get("vertical_fit_per_lens", {})
            item["ai_digital_fluency"] = scoring.get("ai_digital_fluency", "none")
            if scoring.get("_fallback"):
                item["scoring_fallback"] = True
            item["scored_at"] = datetime.now(timezone.utc).isoformat()
            updated = True
            break

    if not updated:
        return

    tmp = d / f"experiences-index.json.{secrets.token_hex(4)}.tmp"
    tmp.write_text(json.dumps({"experiences": items}, ensure_ascii=False, indent=2))
    tmp.replace(index_path)

    # Update profile.experiences_scored_count
    profile = storage.load_profile(user_id)
    if profile is None:
        return
    scored = sum(1 for it in items if it.get("scoring_status") == "done")
    profile["experiences_scored_count"] = scored
    profile["experience_count"] = len(items)
    storage.save_profile(user_id, profile)


@router.post("/api/users/experiences/upload")
async def upload_experiences(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    x_user_id: Optional[str] = Header(default=None),
):
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    if not files:
        raise HTTPException(400, "no files provided")

    # Cap before doing the I/O so a 31st 50KB file doesn't leak storage
    if len(files) > _EXP_MAX_FILES:
        raise HTTPException(
            413,
            f"too many files: {len(files)} > {_EXP_MAX_FILES} (per-upload cap)",
        )

    # Phase 1: validate and decode ALL files before writing any to disk.
    # This prevents partial side-effects (e.g. 3 of 5 files persisted) when
    # a later file in the batch fails validation.
    validated: list[tuple[str, str]] = []  # (display_filename, decoded_text)
    for upload in files:
        fmt = _detect_format(upload.filename or "")
        if fmt is None:
            raise HTTPException(
                400,
                f"unsupported format for filename {upload.filename!r}; expected .md/.tex/.docx/.pdf",
            )
        content = await upload.read()
        if not content:
            raise HTTPException(400, f"empty file: {upload.filename!r}")
        if len(content) > _EXP_MAX_BYTES:
            raise HTTPException(
                413,
                f"file too large: {upload.filename!r} {len(content)} bytes > {_EXP_MAX_BYTES} (50KB cap)",
            )

        # For .docx/.pdf we parse to text; for .md/.tex we store raw
        if fmt in ("docx", "pdf"):
            try:
                parsed = parse_resume(content, format=fmt)
            except Exception as e:
                raise HTTPException(400, f"failed to parse {upload.filename!r}: {e}")
            text = parsed.raw_tex if parsed.raw_tex else ""
            if not text.strip():
                raise HTTPException(
                    400,
                    f"could not extract text from {upload.filename!r}",
                )
        else:
            text = _decode_text(content)
            if not text.strip():
                raise HTTPException(
                    400,
                    f"empty content after decoding {upload.filename!r}",
                )

        validated.append((upload.filename or "experience", text))

    # Phase 2: all files valid — write to disk atomically one-by-one.
    out_records: list[dict] = []
    for file_name, text in validated:
        exp_id = storage.add_experience(user_id, file_name, text)
        out_records.append({
            "id": exp_id,
            "file_name": file_name,
            "scoring_status": "queued",
        })

    # Schedule background scoring as a single batch task that runs the LLM
    # calls in parallel via asyncio.gather. Previously each upload added its
    # own BackgroundTask which FastAPI runs serially, so N experiences × the
    # per-call timeout (default 60s) = N minutes of "stuck" UI when the LLM
    # is slow/unreachable. The batched task collapses that to wall-clock ~=
    # one timeout regardless of N (memory: harness asyncio loop holds N
    # in-flight HTTP requests, bounded by _EXP_MAX_FILES=30).
    if out_records:
        batch: list[tuple[str, str]] = []
        for rec in out_records:
            batch.append((rec["id"], rec["file_name"]))
        # Capture text contents alongside ids for the batch task.
        # Rebuild content for each since UploadFile is single-read.
        contents_by_id: dict[str, str] = {}
        for rec in out_records:
            raw_path = storage.user_dir(user_id) / "experiences" / f"{rec['id']}.md"
            if raw_path.is_file():
                try:
                    contents_by_id[rec["id"]] = raw_path.read_text(encoding="utf-8")
                except OSError:
                    pass
        background_tasks.add_task(_score_batch_in_parallel, user_id, contents_by_id)

    # Update profile.experience_count immediately (scored_count updated by bg task)
    profile = storage.load_profile(user_id) or {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_names": [],
    }
    profile["experience_count"] = len(storage.list_experiences(user_id))
    storage.save_profile(user_id, profile)

    return {"ok": True, "experiences": out_records}


# ---------------- POST /api/users/experiences/rescore ----------------


@router.post("/api/users/experiences/rescore")
async def rescore_queued_experiences(
    background_tasks: BackgroundTasks,
    x_user_id: Optional[str] = Header(default=None),
):
    """Re-enqueue every experience with scoring_status='queued'.

    Bulk-migrated users (e.g. default seeded from repo assets) have
    experiences in 'queued' state but no background task scheduled. This
    endpoint walks the index, schedules _score_and_persist for each queued
    item using the stored raw text, and returns the count of jobs queued.
    Idempotent: items already 'done' are skipped.
    """
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        d = storage.user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    items = storage.list_experiences(user_id)
    queued_ids: list[str] = []
    contents_by_id: dict[str, str] = {}
    for it in items:
        if it.get("scoring_status") != "queued":
            continue
        exp_id = it.get("id")
        if not exp_id:
            continue
        # Read the raw experience text. storage layout: <user_dir>/experiences/<exp_id>.md
        raw_path = d / "experiences" / f"{exp_id}.md"
        if not raw_path.is_file():
            continue
        try:
            text = raw_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.strip():
            continue
        contents_by_id[exp_id] = text
        queued_ids.append(exp_id)
    if contents_by_id:
        background_tasks.add_task(_score_batch_in_parallel, user_id, contents_by_id)
    return {"ok": True, "scheduled": len(queued_ids), "experience_ids": queued_ids}


# ---------------- GET /api/users/me ----------------


@router.get("/api/users/me")
async def get_me(x_user_id: Optional[str] = Header(default=None)):
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    profile = storage.load_profile(user_id)
    items = storage.list_experiences(user_id)
    scored = sum(1 for it in items if it.get("scoring_status") == "done")
    return {
        "user_id": user_id,
        "profile": profile,
        "has_resume": storage.has_master(user_id),
        "experience_count": len(items),
        "experiences_scored_count": scored,
        "experiences": [
            {
                "id": it.get("id"),
                "file_name": it.get("file_name"),
                "scoring_status": it.get("scoring_status", "queued"),
            }
            for it in items
        ],
    }


# ---------------- DELETE /api/users/experiences/{exp_id} ----------------


@router.delete("/api/users/experiences/{exp_id}")
async def delete_experience(
    exp_id: str,
    x_user_id: Optional[str] = Header(default=None),
):
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    removed = storage.remove_experience(user_id, exp_id)
    if not removed:
        raise HTTPException(404, f"experience {exp_id!r} not found")

    # Update count in profile
    items = storage.list_experiences(user_id)
    profile = storage.load_profile(user_id)
    if profile is not None:
        profile["experience_count"] = len(items)
        profile["experiences_scored_count"] = sum(
            1 for it in items if it.get("scoring_status") == "done"
        )
        storage.save_profile(user_id, profile)

    return {"ok": True, "experience_count": len(items)}


# ---------------- GET /api/users/me/master/tex ----------------


@router.get("/api/users/me/master/tex", response_class=PlainTextResponse)
async def get_master_tex(x_user_id: Optional[str] = Header(default=None)):
    """Return the user's master.tex content as text/x-tex.

    Powers the /resume route preview pane in the frontend. 404 if the
    user hasn't uploaded a resume yet (front-end uses this signal to
    show the empty state).
    """
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    try:
        content = storage.get_master_tex(user_id)
    except FileNotFoundError:
        raise HTTPException(404, "no master uploaded")

    return PlainTextResponse(content, media_type="text/x-tex")


# ---------------- GET /api/users/me/master/pdf ----------------


@router.get("/api/users/me/master/pdf")
async def get_master_pdf(x_user_id: Optional[str] = Header(default=None)):
    """Compile the uploaded master.tex to PDF + stream it. Mirrors the
    /api/users/masters/{lens}/pdf path for the original (pre-AI) master."""
    from fastapi.responses import FileResponse
    from harness.pdf.compiler import CompileError, PdfToolchainUnavailable, compile_tex_to_pdf

    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    try:
        # Borrow get_master_tex_path semantics: write the in-memory tex
        # to the per-user master.tex path (the storage layer already
        # stores it there) and pass that path into the compiler.
        master_tex_path = storage.user_dir(user_id) / "master.tex"
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))
    if not master_tex_path.exists():
        raise HTTPException(404, "no master uploaded")
    try:
        pdf_path = await compile_tex_to_pdf(master_tex_path)
    except PdfToolchainUnavailable as e:
        logger.warning(f"master pdf toolchain unavailable for {user_id}: {e}")
        raise HTTPException(
            503,
            detail={"code": "pdf_toolchain_unavailable", "message": str(e)},
        )
    except CompileError as e:
        logger.warning(f"master pdf compile failed for {user_id}: {e}")
        raise HTTPException(
            500,
            detail={"code": "pdf_compile_failed", "message": f"PDF compile failed: {e}"},
        )
    return FileResponse(str(pdf_path), media_type="application/pdf", filename="master.pdf")


# ---------------- PATCH /api/users/me ----------------


_VALID_MARKETS = {"north-america", "mainland-china", "hong-kong"}


class PatchProfileBody(BaseModel):
    """Partial profile patch. All fields optional; only present fields are updated."""

    candidate_names: Optional[List[str]] = Field(default=None)
    target_market_default: Optional[str] = Field(default=None)

    @field_validator("candidate_names")
    @classmethod
    def _names_non_empty(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        cleaned = [name.strip() for name in v if isinstance(name, str) and name.strip()]
        return cleaned

    @field_validator("target_market_default")
    @classmethod
    def _market_enum(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in _VALID_MARKETS:
            raise ValueError(
                f"target_market_default must be one of {sorted(_VALID_MARKETS)}; got {v!r}"
            )
        return v


@router.patch("/api/users/me")
async def patch_me(
    body: PatchProfileBody,
    x_user_id: Optional[str] = Header(default=None),
):
    """Update mutable profile fields (candidate_names, target_market_default).

    Returns the same shape as GET /api/users/me so the client can
    refresh its cache without a follow-up fetch.
    """
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    profile = storage.load_profile(user_id) or {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_names": [],
    }

    if body.candidate_names is not None:
        profile["candidate_names"] = body.candidate_names
    if body.target_market_default is not None:
        profile["target_market_default"] = body.target_market_default

    storage.save_profile(user_id, profile)

    items = storage.list_experiences(user_id)
    scored = sum(1 for it in items if it.get("scoring_status") == "done")
    return {
        "user_id": user_id,
        "profile": storage.load_profile(user_id),
        "has_resume": storage.has_master(user_id),
        "experience_count": len(items),
        "experiences_scored_count": scored,
        "experiences": [
            {
                "id": it.get("id"),
                "file_name": it.get("file_name"),
                "scoring_status": it.get("scoring_status", "queued"),
            }
            for it in items
        ],
    }


# ---------------- DELETE /api/users/me ----------------


@router.delete("/api/users/me")
async def delete_me(x_user_id: Optional[str] = Header(default=None)):
    """Cascade-delete the entire user_dir (master + experiences + runs + profile).

    Per ADR 0004, the destination is computed via UserStorage.user_dir()
    which validates user_id (regex) before producing the path — so we
    can never rmtree an attacker-supplied path. Idempotent: returns ok
    even if the dir doesn't exist (e.g. a never-touched user_id).
    """
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        target = storage.user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    # Defensive guard: target must live under the storage root.
    try:
        target.resolve().relative_to(storage._root.resolve())
    except (ValueError, OSError):
        raise HTTPException(400, "invalid user dir resolution")

    if target.exists():
        shutil.rmtree(target)
        logger.info(f"deleted user_dir for {user_id}: {target}")

    return {"ok": True}


# =====================================================================
# Wave 4 C.1.4 — multi-lens onboarding endpoints
#
# Status tracking: the simpler of the two options in the spec is a
# file-marker. When a generation is scheduled we write a `.generating`
# sentinel under `<user_dir>/masters/<lens>/`; the background worker
# removes it on completion. This survives process restarts (in-memory
# dicts do not) and stays consistent with the rest of the storage layer
# which is filesystem-canonical.
# =====================================================================


_VALID_LENSES = LENS_ENUM


def _generating_marker_path(storage: UserStorage, user_id: str, lens: str) -> Path:
    return storage.user_dir(user_id) / "masters" / lens / ".generating"


def _is_generating(storage: UserStorage, user_id: str, lens: str) -> bool:
    try:
        return _generating_marker_path(storage, user_id, lens).exists()
    except (InvalidUserIdError, InvalidLensError):
        return False


def _mark_generating(storage: UserStorage, user_id: str, lens: str) -> None:
    p = _generating_marker_path(storage, user_id, lens)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(datetime.now(timezone.utc).isoformat())


def _clear_generating(storage: UserStorage, user_id: str, lens: str) -> None:
    try:
        p = _generating_marker_path(storage, user_id, lens)
    except (InvalidUserIdError, InvalidLensError):
        return
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass


# ---------------- POST /api/users/lens-targets ----------------


class LensTargetsBody(BaseModel):
    primary: str = Field(...)
    secondary: List[str] = Field(default_factory=list)

    @field_validator("primary")
    @classmethod
    def _primary_in_enum(cls, v: str) -> str:
        if v not in _VALID_LENSES:
            raise ValueError(
                f"primary must be one of {sorted(_VALID_LENSES)}; got {v!r}"
            )
        return v

    @field_validator("secondary")
    @classmethod
    def _secondary_in_enum(cls, v: List[str]) -> List[str]:
        if not isinstance(v, list):
            raise ValueError("secondary must be a list")
        for item in v:
            if item not in _VALID_LENSES:
                raise ValueError(
                    f"secondary entry must be one of {sorted(_VALID_LENSES)}; got {item!r}"
                )
        # Deduplicate while preserving order
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out


@router.post("/api/users/lens-targets")
async def post_lens_targets(
    body: LensTargetsBody,
    x_user_id: Optional[str] = Header(default=None),
):
    """Persist primary + secondary lens targets to profile.json.

    Idempotent. Validates lens enum membership at the body layer.
    Rejects 422 when primary is also in secondary (a target cannot be
    both primary and secondary).
    """
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    if body.primary in body.secondary:
        raise HTTPException(
            422,
            f"primary {body.primary!r} cannot also be in secondary",
        )

    profile = storage.load_profile(user_id) or {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "candidate_names": [],
    }
    profile["target_lens_default"] = body.primary
    profile["target_lens_secondary"] = body.secondary
    storage.save_profile(user_id, profile)

    return {
        "ok": True,
        "primary": body.primary,
        "secondary": body.secondary,
    }


# ---------------- POST /api/users/masters/generate ----------------


class GenerateMasterBody(BaseModel):
    lens: str = Field(...)

    @field_validator("lens")
    @classmethod
    def _lens_in_enum(cls, v: str) -> str:
        if v not in _VALID_LENSES:
            raise ValueError(
                f"lens must be one of {sorted(_VALID_LENSES)}; got {v!r}"
            )
        return v


def _generate_master_background(user_id: str, lens: str) -> None:
    """Background task: load upload + experiences, call the master_gen
    engine, persist the result via UserStorage.add_lens_master, update
    profile.masters_generated, and clear the in-flight marker.

    Wrapped in a top-level try/except so a worker crash never leaks past
    the BackgroundTasks runtime — the marker is always cleared.
    """
    storage = _storage()
    try:
        # 1. Load upload tex.
        try:
            upload_tex = storage.get_master_tex(user_id)
        except FileNotFoundError:
            logger.warning(
                f"master generation aborted: no upload for {user_id}"
            )
            _clear_generating(storage, user_id, lens)
            return
        # 2. Load experiences index.
        experiences = storage.list_experiences(user_id)
        # 3. Locate raw experience root.
        try:
            raw_root = storage.user_dir(user_id) / "experiences"
        except InvalidUserIdError:
            _clear_generating(storage, user_id, lens)
            return
        # 4. Resolve target_market from profile.
        profile = storage.load_profile(user_id) or {}
        target_market = profile.get("target_market_default") or "mainland-china"
        # 5. Run the master generator.
        try:
            import asyncio as _asyncio

            from harness.master_gen import generate_master_for_lens

            llm = get_llm_provider()
            result = _asyncio.run(
                generate_master_for_lens(
                    upload_tex=upload_tex,
                    experiences=experiences,
                    raw_files_root=raw_root,
                    lens=lens,
                    target_market=target_market,
                    llm=llm,
                    repo_root=config.repo_root,
                )
            )
        except SubSkillUnavailable as e:
            # Phase 2 (fail-fast): master_gen now raises SubSkillUnavailable
            # rather than returning a verbatim-copy fallback. This is a
            # background task so we can't return 503 directly; clear the
            # in-flight marker and log with full context. Phase 2.D will
            # write a failure sentinel into the master dir so GET /masters
            # can surface "generation failed — retry" to the UI.
            logger.warning(
                f"master_gen unavailable for {user_id}/{lens}: "
                f"sub_skill={e.sub_skill} llm_unreachable={e.llm_unreachable} "
                f"reason={e.reason}"
            )
            _clear_generating(storage, user_id, lens)
            return
        except Exception as e:
            logger.warning(
                f"master_gen crashed for {user_id}/{lens}: {e}"
            )
            _clear_generating(storage, user_id, lens)
            return

        # 6. Persist via storage. method maps the engine's _method to the
        # spec enum: anything LLM-driven → "rewrite_from_upload_and_bank";
        # fallback → "user_upload" (we kept the upload verbatim).
        method_marker = (
            "user_upload"
            if result._method == "fallback_no_llm"
            else "rewrite_from_upload_and_bank"
        )
        try:
            storage.add_lens_master(
                user_id, lens, result.master_tex, method_marker
            )
        except (InvalidUserIdError, InvalidLensError, ValueError) as e:
            logger.warning(
                f"master_gen persist failed for {user_id}/{lens}: {e}"
            )
            _clear_generating(storage, user_id, lens)
            return

        # 7. Update profile.masters_generated[lens].
        profile = storage.load_profile(user_id) or {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "candidate_names": [],
        }
        masters_log = profile.get("masters_generated") or {}
        if not isinstance(masters_log, dict):
            masters_log = {}
        masters_log[lens] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "method": method_marker,
        }
        profile["masters_generated"] = masters_log
        storage.save_profile(user_id, profile)
    finally:
        _clear_generating(storage, user_id, lens)


@router.post("/api/users/masters/generate")
async def post_generate_master(
    body: GenerateMasterBody,
    background_tasks: BackgroundTasks,
    x_user_id: Optional[str] = Header(default=None),
):
    """Schedule per-lens master generation for the given lens.

    422 if `lens` not in {A,B,C,D,HC} or not in the user's
    `target_lens_default + target_lens_secondary` set.
    404 if the user has no upload yet.
    Returns immediately with `status: "scheduled"`.
    """
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    if not storage.has_master(user_id):
        raise HTTPException(
            404,
            "no master uploaded; POST /api/users/profile/upload-resume first",
        )

    profile = storage.load_profile(user_id) or {}
    targets: set[str] = set()
    primary = profile.get("target_lens_default")
    if isinstance(primary, str):
        targets.add(primary)
    secondary = profile.get("target_lens_secondary") or []
    if isinstance(secondary, list):
        for item in secondary:
            if isinstance(item, str):
                targets.add(item)

    if body.lens not in targets:
        raise HTTPException(
            422,
            f"lens {body.lens!r} not in user's target list "
            f"({sorted(targets)}); set targets via POST /api/users/lens-targets first",
        )

    # Gate 2: block if LLM monitor says circuit is open — no point scheduling
    # a background task that would fail immediately.
    if get_monitor().is_down():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "llm_unreachable",
                "message": "LLM provider is currently unreachable. Please retry in a few minutes.",
                "sub_skill": None,
            },
        )

    # File-marker → status "generating" until background task clears it.
    _mark_generating(storage, user_id, body.lens)

    background_tasks.add_task(
        _generate_master_background, user_id, body.lens
    )

    return {
        "ok": True,
        "lens": body.lens,
        "status": "scheduled",
    }


# ---------------- GET /api/users/masters ----------------


@router.get("/api/users/masters")
async def get_masters(x_user_id: Optional[str] = Header(default=None)):
    """Per-lens master status for every lens the user has picked.

    Returns one entry per lens in `target_lens_default + target_lens_secondary`
    (NOT all 5). Each entry is `{has_master, generated_at, method, status}`
    where `status ∈ {"ready", "generating", "absent"}`.
    """
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    profile = storage.load_profile(user_id) or {}
    targets: list[str] = []
    primary = profile.get("target_lens_default")
    if isinstance(primary, str) and primary in _VALID_LENSES:
        targets.append(primary)
    secondary = profile.get("target_lens_secondary") or []
    if isinstance(secondary, list):
        for item in secondary:
            if (
                isinstance(item, str)
                and item in _VALID_LENSES
                and item not in targets
            ):
                targets.append(item)

    inventory = storage.list_lens_masters(user_id)
    out: dict[str, dict] = {}
    for lens in targets:
        has = lens in inventory
        generating = _is_generating(storage, user_id, lens)
        if has:
            entry = inventory[lens]
            out[lens] = {
                "has_master": True,
                "generated_at": entry.get("generated_at"),
                "method": entry.get("method"),
                "status": "ready",
            }
        elif generating:
            out[lens] = {
                "has_master": False,
                "generated_at": None,
                "method": None,
                "status": "generating",
            }
        else:
            out[lens] = {
                "has_master": False,
                "generated_at": None,
                "method": None,
                "status": "absent",
            }
    return out


# ---------------- DELETE /api/users/masters/<lens> ----------------


@router.delete("/api/users/masters/{lens}")
async def delete_master(
    lens: str,
    x_user_id: Optional[str] = Header(default=None),
):
    """Remove `<user_dir>/masters/<lens>/` and drop the
    profile.masters_generated[lens] key. 404 if the dir is absent."""
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    if lens not in _VALID_LENSES:
        raise HTTPException(
            422,
            f"lens must be one of {sorted(_VALID_LENSES)}; got {lens!r}",
        )

    removed = storage.remove_lens_master(user_id, lens)
    if not removed:
        raise HTTPException(404, f"no per-lens master for lens {lens!r}")

    profile = storage.load_profile(user_id) or {}
    masters_log = profile.get("masters_generated") or {}
    if isinstance(masters_log, dict) and lens in masters_log:
        masters_log = {k: v for k, v in masters_log.items() if k != lens}
        profile["masters_generated"] = masters_log
        storage.save_profile(user_id, profile)

    return {"ok": True, "lens": lens}


# ---------------- GET /api/users/masters/{lens}/tex ----------------


@router.get("/api/users/masters/{lens}/tex", response_class=PlainTextResponse)
async def get_lens_master_tex(
    lens: str,
    x_user_id: Optional[str] = Header(default=None),
):
    """Return the per-lens master.tex content as text/x-tex.

    Powers the /resume per-direction master download. 422 on unknown
    lens id; 404 if the user hasn't generated this lens yet. Lens id
    is validated against _VALID_LENSES before any path resolution so
    arbitrary {lens} values can't escape the per-user masters dir.
    """
    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    if lens not in _VALID_LENSES:
        raise HTTPException(
            422,
            f"lens must be one of {sorted(_VALID_LENSES)}; got {lens!r}",
        )

    path = storage.get_lens_master_path(user_id, lens)
    if path is None:
        raise HTTPException(404, f"no per-lens master for lens {lens!r}")
    try:
        content = path.read_text()
    except OSError as e:
        raise HTTPException(500, f"failed to read per-lens master: {e}")
    return PlainTextResponse(content, media_type="text/x-tex")


# ---------------- GET /api/users/masters/{lens}/pdf ----------------


@router.get("/api/users/masters/{lens}/pdf")
async def get_lens_master_pdf(
    lens: str,
    x_user_id: Optional[str] = Header(default=None),
):
    """Compile the per-lens master.tex to PDF and stream it back.

    Synchronous compile (~3–5s with xelatex). For repeated downloads the
    compiled PDF is cached next to the .tex on disk by compile_tex_to_pdf,
    so subsequent fetches return the cached artifact without recompiling.
    """
    from fastapi.responses import FileResponse
    from harness.pdf.compiler import CompileError, PdfToolchainUnavailable, compile_tex_to_pdf

    user_id = _resolve_user_id(x_user_id)
    storage = _storage()
    try:
        storage.ensure_user_dir(user_id)
    except InvalidUserIdError as e:
        raise HTTPException(400, str(e))

    if lens not in _VALID_LENSES:
        raise HTTPException(
            422,
            f"lens must be one of {sorted(_VALID_LENSES)}; got {lens!r}",
        )

    tex_path = storage.get_lens_master_path(user_id, lens)
    if tex_path is None:
        raise HTTPException(404, f"no per-lens master for lens {lens!r}")
    try:
        pdf_path = await compile_tex_to_pdf(tex_path)
    except PdfToolchainUnavailable as e:
        logger.warning(f"pdf toolchain unavailable for {user_id}/{lens}: {e}")
        raise HTTPException(
            503,
            detail={"code": "pdf_toolchain_unavailable", "message": str(e)},
        )
    except CompileError as e:
        logger.warning(f"pdf compile failed for {user_id}/{lens}: {e}")
        raise HTTPException(
            500,
            detail={"code": "pdf_compile_failed", "message": f"PDF compile failed: {e}"},
        )
    return FileResponse(str(pdf_path), media_type="application/pdf", filename=f"master.{lens}.pdf")
