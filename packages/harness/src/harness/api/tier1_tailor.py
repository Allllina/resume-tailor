"""POST /api/tier1-tailor endpoint.

Per HARNESS_DESIGN.md §3 (REPL boundary). Validates input against
harness-tailor-input.schema.json, runs Tier 1 REPL loop, returns
harness-tailor-output.schema.json compliant dict.

Wave 2.7: reads X-User-Id header (default default for backward
compat); resolves candidate_names from user profile; persists run under
data/users/{user_id}/runs/.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from loguru import logger
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from harness.config import config
from harness.exceptions import SubSkillUnavailable
from harness.llm.factory import make_llm_provider_for_thread
from harness.llm.health import get_monitor
from harness.policy.gateway import PolicyGateway
from harness.repl.eval import Tier1Tools
from harness.repl.loop import run_tier1
from harness.schemas.loader import SchemaRegistry, SchemaValidationError
from harness.users.storage import InvalidUserIdError, UserStorage


router = APIRouter()


class JDInput(BaseModel):
    source: str
    raw_text: str
    url: Optional[str] = None
    scraper_id: Optional[str] = None
    company_hint: Optional[str] = None
    role_title_hint: Optional[str] = None
    location_hint: Optional[str] = None


class TailorRequest(BaseModel):
    mode: str
    jd: JDInput
    candidate_profile_ref: str
    target_market: str
    lens_hint: Optional[str] = None
    tier_override: Optional[int] = None
    submit_channel_preference: Optional[str] = None


_DEFAULT_USER_ID = "default"


@router.post("/api/tier1-tailor")
async def tier1_tailor(
    req: TailorRequest,
    x_user_id: Optional[str] = Header(default=None),
):
    repo_root = config.repo_root

    # 1. Validate input against the harness-tailor-input contract
    registry = SchemaRegistry(repo_root)
    try:
        registry.validate("harness-tailor-input", req.model_dump(exclude_none=True))
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 2. Resolve user → candidate_names + runs_root
    user_id = x_user_id or _DEFAULT_USER_ID
    storage = UserStorage(repo_root)
    try:
        runs_root = storage.runs_dir(user_id)  # validates user_id
    except InvalidUserIdError as e:
        raise HTTPException(status_code=400, detail=str(e))

    profile = storage.load_profile(user_id)
    if profile and profile.get("candidate_names"):
        candidate_names = profile["candidate_names"]
    else:
        # Legacy fallback for default before migration ran
        candidate_names = ["Alina", "Alina"]

    # Wave 2.7 → Wave 4 D.5 follow-up: per-user master plumbing.
    # - default → always pass user_dir (MasterSelector chains to
    #   legacy assets/ on miss)
    # - any other user without ANY master (neither legacy nor per-lens) → 412
    # - any other user with master(s) → pass user_dir; MasterSelector picks
    #   per-lens master first, then legacy single master, then project sample.
    user_dir = storage.user_dir(user_id)
    has_any_master = storage.has_master(user_id) or bool(
        storage.list_lens_masters(user_id)
    )
    if not has_any_master and user_id != _DEFAULT_USER_ID:
        raise HTTPException(
            status_code=412,
            detail="No resume uploaded. POST /api/users/profile/upload-resume first.",
        )

    # 3. LLM health precheck (Gate 2) — block immediately if circuit is open
    # rather than letting the request burn 60s before hitting a CircuitOpen.
    monitor = get_monitor()
    if monitor.is_down():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "llm_unreachable",
                "message": "LLM provider is currently unreachable. Please retry in a few minutes.",
                "sub_skill": None,
            },
        )

    # 4. Build jd_context snapshot for UI rendering on review page
    jd_context = {
        "raw_text": req.jd.raw_text,
        "target_market": req.target_market,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    for k in ("company_hint", "role_title_hint", "location_hint"):
        v = getattr(req.jd, k, None)
        if v:
            jd_context[k] = v

    # 5. Run Tier 1 REPL loop.
    #
    # The REPL path is long-running and includes legacy synchronous file/LLM
    # boundaries. Run it in a worker thread so the ASGI event loop can keep
    # serving lightweight endpoints such as /api/health during tailoring.
    def _run_tailor_sync() -> dict:
        # Each asyncio.run() call creates and closes its own event loop.
        # Re-using the process-wide singleton (get_llm_provider) would leave
        # async HTTP clients bound to a closed loop on the second request.
        # make_llm_provider_for_thread() builds fresh clients every call while
        # still wiring CircuitBreaker callbacks to the global LLMHealthMonitor.
        llm = make_llm_provider_for_thread()
        policy = PolicyGateway(repo_root, candidate_names=candidate_names)
        tools = Tier1Tools(
            repo_root,
            llm,
            policy,
            user_dir=user_dir,
            candidate_names=candidate_names,
        )
        return asyncio.run(
            run_tier1(
                jd_text=req.jd.raw_text,
                target_market=req.target_market,
                repo_root=repo_root,
                tools=tools,
                candidate_names=candidate_names,
                jd_context=jd_context,
                runs_root=runs_root,
            )
        )

    # Phase 2 (fail-fast): if any critical sub-skill raises
    # SubSkillUnavailable (LLM unreachable / unparseable output / missing
    # ground truth), surface as HTTP 503 with structured detail so the UI
    # can render a precise "X sub-skill unavailable, retry in Ys" message
    # instead of the pre-Phase-2 "0 changes from your master" lie. See
    # docs/plans/2026-05-12-phase2-remove-per-subskill-fallback.md §2.D.
    try:
        output = await run_in_threadpool(_run_tailor_sync)
    except SubSkillUnavailable as e:
        logger.warning(
            f"Sub-skill unavailable: {e.sub_skill} "
            f"({'LLM unreachable' if e.llm_unreachable else 'output unusable'}) — {e.reason}"
        )
        raise HTTPException(status_code=503, detail=e.to_503_detail())

    # 6. Best-effort output schema validation. If we drift, log + return
    # anyway — the run already produced an artifact and trace, refusing to
    # return is worse than surfacing a non-compliant body to the caller.
    try:
        registry.validate("harness-tailor-output", output)
    except SchemaValidationError as e:
        logger.warning(f"Output schema validation failed: {e}")
        output["_schema_validation_warning"] = str(e)

    return output
