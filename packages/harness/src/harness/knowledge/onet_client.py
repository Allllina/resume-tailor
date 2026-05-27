"""O*NET Web Services client.

Docs: https://services.onetcenter.org/developer/
Auth: HTTP Basic (username + password issued after free registration).
Rate: no hard public limit; responses are cached in-process with a 24h TTL.

Relevant SOC codes for common resume targets (fast path, no API call needed):
  15-1252.00  Software Developers
  15-1211.00  Computer Systems Analysts
  15-1243.00  Database Architects
  15-1244.00  Network and Computer Systems Administrators
  15-1231.00  Computer Network Support Specialists
  15-2051.00  Data Scientists
  15-2041.00  Statisticians
  15-1299.09  Information Technology Project Managers
  13-1161.00  Market Research Analysts
  11-3031.00  Financial Managers
  13-2051.00  Financial and Investment Analysts
"""
import asyncio
import base64
import time
from typing import Any

import httpx
from loguru import logger

_BASE = "https://services.onetcenter.org/ws"
_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 86_400  # 24 h — O*NET data rarely changes


def _cache_get(key: str) -> Any | None:
    entry = _CACHE.get(key)
    if entry and time.monotonic() - entry[0] < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.monotonic(), value)


class OnetClient:
    """Thin async wrapper around O*NET Web Services REST API."""

    def __init__(self, username: str, password: str, timeout: int = 10):
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
        }
        self._timeout = timeout

    async def _get(self, path: str, params: dict | None = None) -> dict:
        cache_key = f"{path}?{params}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        url = f"{_BASE}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(url, headers=self._headers, params=params or {})
            r.raise_for_status()
            data = r.json()

        _cache_set(cache_key, data)
        return data

    # ── Public methods ────────────────────────────────────────────────

    async def search_occupations(self, keyword: str, top_n: int = 5) -> list[dict]:
        """Return up to top_n occupations matching the keyword."""
        data = await self._get(
            "/online/occupations/",
            params={"keyword": keyword, "start": 1, "end": top_n, "fmt": "json"},
        )
        results = []
        for occ in data.get("occupation", []):
            results.append({
                "code": occ.get("code", ""),
                "title": occ.get("title", ""),
                "bright_outlook": occ.get("tags", {}).get("bright_outlook", False),
            })
        return results

    async def get_summary(self, code: str) -> dict:
        """Return title + description + sample work activities for a SOC code."""
        data = await self._get(f"/online/occupations/{code}/summary")
        return {
            "code": code,
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "sample_activities": [
                a.get("name", "") for a in data.get("sample_of_reported_job_titles", {}).get("title", [])
            ][:6],
        }

    async def get_skills(self, code: str, min_importance: float = 2.5) -> list[dict]:
        """Return skills sorted by importance, filtered to ≥ min_importance."""
        data = await self._get(f"/online/occupations/{code}/details/skills")
        out = []
        for el in data.get("element", []):
            imp = next(
                (s["value"] for s in el.get("scale", []) if s.get("id") == "IM"),
                0.0,
            )
            if imp >= min_importance:
                out.append({"name": el.get("name", ""), "importance": round(imp, 2)})
        return sorted(out, key=lambda x: -x["importance"])

    async def get_knowledge(self, code: str, min_importance: float = 2.5) -> list[dict]:
        """Return knowledge areas sorted by importance."""
        data = await self._get(f"/online/occupations/{code}/details/knowledge")
        out = []
        for el in data.get("element", []):
            imp = next(
                (s["value"] for s in el.get("scale", []) if s.get("id") == "IM"),
                0.0,
            )
            if imp >= min_importance:
                out.append({"name": el.get("name", ""), "importance": round(imp, 2)})
        return sorted(out, key=lambda x: -x["importance"])

    async def get_technology_skills(self, code: str) -> dict:
        """Return hot technologies and full tool list for a SOC code."""
        data = await self._get(f"/online/occupations/{code}/details/technology_skills")
        hot, all_tech = [], []
        for category in data.get("category", []):
            for ex in category.get("example", []):
                name = ex.get("name", "")
                if name:
                    all_tech.append(name)
                    if ex.get("hot_technology"):
                        hot.append(name)
        return {"hot_technologies": hot, "all_technologies": all_tech}

    async def get_full_competency(self, code: str) -> dict:
        """Fetch summary + skills + knowledge + tech in one call.

        The summary request validates that the SOC code exists. Let that
        failure propagate so callers can return 404 / 502 instead of a
        silently-empty competency model. Detail sections are additive: if one
        of them fails, return the available model with warning metadata.
        """
        summary = await self.get_summary(code)
        skills, knowledge, tech = await asyncio.gather(
            self.get_skills(code),
            self.get_knowledge(code),
            self.get_technology_skills(code),
            return_exceptions=True,
        )

        warnings = []

        def _safe(section: str, val, default):
            if isinstance(val, Exception):
                logger.warning(f"O*NET {section} fetch failed for {code}: {val}")
                warnings.append({"section": section, "reason": str(val)})
                return default
            return val

        out = {
            "occupation": summary,
            "skills": _safe("skills", skills, []),
            "knowledge": _safe("knowledge", knowledge, []),
            "technology_skills": _safe(
                "technology_skills",
                tech,
                {"hot_technologies": [], "all_technologies": []},
            ),
        }
        if warnings:
            out["warnings"] = warnings
        return out
