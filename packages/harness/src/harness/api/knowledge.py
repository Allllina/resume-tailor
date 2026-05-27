"""GET /api/skill-knowledge/* — external knowledge endpoints for the Skill.

Replaces bundled reference files in the .skill package with on-demand API
calls. The Skill's SKILL.md orchestration layer calls these endpoints at the
relevant steps, retrieving only the data it needs rather than loading
multi-kilobyte reference files into context at startup.

Endpoints
─────────
GET /api/skill-knowledge/occupation/search?q=<keyword>&top=<n>
    Search O*NET for matching occupations. Returns up to `top` candidates
    with SOC code + title. Skill picks the best match from the JD context.

GET /api/skill-knowledge/occupation/<soc_code>
    Full competency model for a SOC code: summary, skills, knowledge areas,
    technology skills, and resume guidance (verb patterns, keyword tiers,
    proof hierarchy, anti-patterns). This replaces role-families.md.

GET /api/skill-knowledge/occupation/infer?title=<job_title>&top=<n>
    Convenience wrapper: runs search on the job title string and returns the
    top match with its full competency model in one call.

GET /api/skill-knowledge/jobs/search?q=<query>&location=<loc>&market=<na|cn|hk>&n=<n>
    Live JD search via JSearch (RapidAPI). Returns job postings with full
    description text so the Skill can work without the user pasting a JD.
    Requires HARNESS_JSEARCH_API_KEY in env. Returns empty list gracefully
    if key is not configured (Skill falls back to asking user for JD text).
"""
from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from harness.config import config
from harness.knowledge.onet_client import OnetClient
from harness.knowledge.resume_guidance import build_resume_guidance

router = APIRouter(prefix="/api/skill-knowledge", tags=["skill-knowledge"])

_ONET_NOT_CONFIGURED = (
    "O*NET credentials not configured. "
    "Set HARNESS_ONET_USERNAME and HARNESS_ONET_PASSWORD in .env "
    "(free registration at https://services.onetcenter.org/developer/)."
)

_JSEARCH_NOT_CONFIGURED = (
    "JSearch API key not configured. "
    "Set HARNESS_JSEARCH_API_KEY in .env "
    "(free tier at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)."
)


def _get_onet_client() -> OnetClient:
    if not config.onet_username or not config.onet_password:
        raise HTTPException(status_code=503, detail=_ONET_NOT_CONFIGURED)
    return OnetClient(config.onet_username, config.onet_password)


# ── Occupation search ─────────────────────────────────────────────────────────

@router.get("/occupation/search")
async def search_occupations(
    q: Annotated[str, Query(description="Job title or keyword to search")],
    top: Annotated[int, Query(ge=1, le=20)] = 5,
):
    """Search O*NET for occupations matching a keyword. Returns SOC codes + titles."""
    client = _get_onet_client()
    try:
        results = await client.search_occupations(q, top_n=top)
    except httpx.HTTPStatusError as e:
        logger.warning(f"O*NET search failed: {e}")
        raise HTTPException(status_code=502, detail=f"O*NET API error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.warning(f"O*NET network error: {e}")
        raise HTTPException(status_code=502, detail="O*NET API unreachable")

    return {"query": q, "results": results}


# ── Infer occupation from job title ──────────────────────────────────────────

@router.get("/occupation/infer")
async def infer_occupation(
    title: Annotated[str, Query(description="Job title string from the JD")],
    top: Annotated[int, Query(ge=1, le=5)] = 1,
):
    """Search O*NET by job title and return the top match with full competency model.

    Combines search + get_occupation into a single call for the Skill to use
    when it has a job title but no SOC code.
    """
    client = _get_onet_client()

    # Step 1: search
    try:
        candidates = await client.search_occupations(title, top_n=max(top, 3))
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning(f"O*NET infer/search failed: {e}")
        raise HTTPException(status_code=502, detail="O*NET API error during occupation search")

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No O*NET occupations found for title: {title!r}",
        )

    # Step 2: fetch full competency for top match (or top N)
    best = candidates[0]
    try:
        raw = await client.get_full_competency(best["code"])
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning(f"O*NET infer/competency failed for {best['code']}: {e}")
        # Return partial result — search candidates + no competency
        return {
            "inferred_from": title,
            "matched_occupation": best,
            "other_candidates": candidates[1:],
            "competency": None,
            "resume_guidance": None,
            "warning": "Competency fetch failed — use matched_occupation.code to retry.",
        }

    top_skills = [s["name"] for s in raw["skills"][:10]]
    top_knowledge = [k["name"] for k in raw["knowledge"][:6]]
    hot_tech = raw["technology_skills"]["hot_technologies"]
    all_tech = raw["technology_skills"]["all_technologies"]

    guidance = build_resume_guidance(
        soc_code=best["code"],
        occ_title=raw["occupation"]["title"],
        top_skills=top_skills,
        top_knowledge=top_knowledge,
        hot_tech=hot_tech,
        all_tech=all_tech,
    )

    return {
        "inferred_from": title,
        "matched_occupation": best,
        "other_candidates": candidates[1:],
        **raw,
        "resume_guidance": guidance,
    }


# ── Full competency model by SOC code ─────────────────────────────────────────

@router.get("/occupation/{soc_code:path}")
async def get_occupation(soc_code: str):
    """Return full competency model + resume guidance for a SOC code.

    soc_code examples: 15-1252.00, 15-2051.00, 13-2051.00

    Registered after /occupation/infer so the catch-all path does not shadow
    the explicit infer endpoint.
    """
    client = _get_onet_client()
    try:
        raw = await client.get_full_competency(soc_code)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"SOC code not found: {soc_code}")
        logger.warning(f"O*NET competency fetch failed: {e}")
        raise HTTPException(status_code=502, detail=f"O*NET API error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.warning(f"O*NET network error: {e}")
        raise HTTPException(status_code=502, detail="O*NET API unreachable")

    # Extract flat lists for guidance layer
    top_skills = [s["name"] for s in raw["skills"][:10]]
    top_knowledge = [k["name"] for k in raw["knowledge"][:6]]
    hot_tech = raw["technology_skills"]["hot_technologies"]
    all_tech = raw["technology_skills"]["all_technologies"]
    occ_title = raw["occupation"]["title"]

    guidance = build_resume_guidance(
        soc_code=soc_code,
        occ_title=occ_title,
        top_skills=top_skills,
        top_knowledge=top_knowledge,
        hot_tech=hot_tech,
        all_tech=all_tech,
    )

    return {**raw, "resume_guidance": guidance}


# ── Live JD search (JSearch / RapidAPI) ──────────────────────────────────────

@router.get("/jobs/search")
async def search_jobs(
    q: Annotated[str, Query(description="Role + company, e.g. 'Senior SWE Google'")],
    location: Annotated[Optional[str], Query()] = None,
    market: Annotated[str, Query(description="na | cn | hk")] = "na",
    n: Annotated[int, Query(ge=1, le=10)] = 5,
):
    """Search live job postings via JSearch (aggregates LinkedIn, Indeed, Glassdoor).

    Returns job titles, companies, locations, and full JD text.
    If HARNESS_JSEARCH_API_KEY is not set, returns an empty list with a hint
    rather than an error — the Skill will fall back to asking the user for JD text.
    """
    if not config.jsearch_api_key:
        logger.debug("JSearch key not configured — returning empty job search result")
        return {
            "query": q,
            "results": [],
            "hint": _JSEARCH_NOT_CONFIGURED,
        }

    query = f"{q} {location}" if location else q
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": config.jsearch_api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    params = {"query": query, "num_pages": "1", "page": "1", "date_posted": "all"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        logger.warning(f"JSearch API error: {e}")
        raise HTTPException(status_code=502, detail=f"JSearch API error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.warning(f"JSearch network error: {e}")
        raise HTTPException(status_code=502, detail="JSearch API unreachable")

    jobs = []
    for job in (data.get("data") or [])[:n]:
        jobs.append({
            "title": job.get("job_title", ""),
            "company": job.get("employer_name", ""),
            "location": job.get("job_city", "") + (f", {job.get('job_country', '')}" if job.get("job_country") else ""),
            "posted": job.get("job_posted_at_datetime_utc", ""),
            "apply_link": job.get("job_apply_link", ""),
            "description": job.get("job_description", ""),  # full JD text
        })

    return {"query": q, "market": market, "results": jobs}
