"""Unit tests for harness.knowledge layer.

Tests cover:
- resume_guidance role family detection + keyword tier assembly
- knowledge API endpoints return 503 when O*NET is unconfigured
- knowledge API jobs endpoint returns empty list gracefully when JSearch is unconfigured
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import httpx

from harness.knowledge.resume_guidance import (
    detect_role_family,
    build_keyword_tiers,
    build_resume_guidance,
)


# ── resume_guidance unit tests ────────────────────────────────────────────────

class TestDetectRoleFamily:
    def test_soc_code_backend(self):
        family, subtype = detect_role_family("15-1252.00", [])
        assert family == "Technology & Engineering"
        assert subtype == "backend_systems"

    def test_soc_code_data_science(self):
        family, subtype = detect_role_family("15-2051.00", [])
        assert family == "Data & Analytics"
        assert subtype == "data_science"

    def test_soc_code_finance(self):
        family, subtype = detect_role_family("13-2051.00", [])
        assert family == "Finance & Investment"

    def test_skill_signal_fallback(self):
        # Unknown SOC → fall through to skill signal
        family, subtype = detect_role_family("99-9999.00", ["Programming", "Systems Analysis"])
        assert family == "Technology & Engineering"

    def test_unknown_falls_back_to_general(self):
        family, subtype = detect_role_family("99-9999.00", ["Interpersonal Communication"])
        assert family == "General Management & BD"


class TestBuildKeywordTiers:
    def test_tiers_populated(self):
        result = build_keyword_tiers(
            occ_title="Software Developer",
            top_skills=["Programming", "Systems Analysis", "Critical Thinking",
                        "Complex Problem Solving", "Active Learning"],
            top_knowledge=["Computers and Electronics", "Mathematics"],
            hot_tech=["Python", "Java", "Git"],
            all_tech=["Python", "Java", "Git", "Docker", "AWS"],
        )
        assert "Software Developer" in result["tier1_core_identity"]
        assert "Programming" in result["tier1_core_identity"]
        assert "Python" in result["tier3_tools"]

    def test_hot_tech_preferred_for_tier3(self):
        result = build_keyword_tiers(
            occ_title="Data Scientist",
            top_skills=["Mathematics"],
            top_knowledge=["Statistics"],
            hot_tech=["PyTorch", "scikit-learn"],
            all_tech=["PyTorch", "scikit-learn", "Pandas", "NumPy"],
        )
        assert "PyTorch" in result["tier3_tools"]

    def test_falls_back_to_all_tech_if_no_hot(self):
        result = build_keyword_tiers(
            occ_title="Systems Analyst",
            top_skills=[],
            top_knowledge=[],
            hot_tech=[],
            all_tech=["SQL", "Excel"],
        )
        assert "SQL" in result["tier3_tools"]


class TestBuildResumeGuidance:
    def test_full_output_shape(self):
        guidance = build_resume_guidance(
            soc_code="15-1252.00",
            occ_title="Software Developers",
            top_skills=["Programming", "Systems Analysis", "Critical Thinking"],
            top_knowledge=["Computers and Electronics"],
            hot_tech=["Python", "Java"],
            all_tech=["Python", "Java", "C++"],
        )
        assert guidance["role_family"] == "Technology & Engineering"
        assert guidance["subtype"] == "backend_systems"
        assert len(guidance["primary_verbs"]) > 0
        assert len(guidance["anti_patterns"]) > 0
        assert "keyword_tiers" in guidance
        assert guidance["proof_hierarchy"]

    def test_subtype_note_present(self):
        guidance = build_resume_guidance(
            soc_code="15-1252.00",
            occ_title="Software Developers",
            top_skills=["Programming"],
            top_knowledge=[],
            hot_tech=[],
            all_tech=[],
        )
        assert "backend" in guidance["subtype_note"].lower()


# ── API endpoint tests (no real O*NET/JSearch credentials needed) ─────────────

@pytest.fixture
def client():
    from harness.api.main import app
    return TestClient(app)


class TestKnowledgeEndpointsUnconfigured:
    """When O*NET and JSearch are not configured, endpoints should degrade gracefully."""

    def test_occupation_search_503_when_no_onet(self, client):
        with patch("harness.api.knowledge.config") as mock_cfg:
            mock_cfg.onet_username = ""
            mock_cfg.onet_password = ""
            r = client.get("/api/skill-knowledge/occupation/search?q=software+developer")
        assert r.status_code == 503
        assert "O*NET" in r.json()["detail"]

    def test_occupation_by_code_503_when_no_onet(self, client):
        with patch("harness.api.knowledge.config") as mock_cfg:
            mock_cfg.onet_username = ""
            mock_cfg.onet_password = ""
            r = client.get("/api/skill-knowledge/occupation/15-1252.00")
        assert r.status_code == 503

    def test_occupation_infer_503_when_no_onet(self, client):
        with patch("harness.api.knowledge.config") as mock_cfg:
            mock_cfg.onet_username = ""
            mock_cfg.onet_password = ""
            r = client.get("/api/skill-knowledge/occupation/infer?title=software+engineer")
        assert r.status_code == 503

    def test_jobs_search_returns_empty_list_when_no_jsearch(self, client):
        """JSearch missing → 200 with empty results + hint, not an error."""
        with patch("harness.api.knowledge.config") as mock_cfg:
            mock_cfg.jsearch_api_key = ""
            r = client.get("/api/skill-knowledge/jobs/search?q=senior+swe+google")
        assert r.status_code == 200
        body = r.json()
        assert body["results"] == []
        assert "hint" in body


class TestKnowledgeEndpointRouting:
    def test_occupation_infer_uses_explicit_route_not_soc_catch_all(self, client):
        class FakeOnetClient:
            async def search_occupations(self, title, top_n=3):
                return [
                    {"code": "15-1252.00", "title": "Software Developers"},
                    {"code": "15-1211.00", "title": "Computer Systems Analysts"},
                ]

            async def get_full_competency(self, code):
                return {
                    "occupation": {
                        "code": code,
                        "title": "Software Developers",
                        "description": "Develop software.",
                    },
                    "skills": [{"name": "Programming", "importance": 4.8}],
                    "knowledge": [{"name": "Computers and Electronics", "importance": 4.2}],
                    "technology_skills": {
                        "hot_technologies": ["Python"],
                        "all_technologies": ["Python", "Git"],
                    },
                }

        with (
            patch("harness.api.knowledge.config") as mock_cfg,
            patch("harness.api.knowledge.OnetClient", return_value=FakeOnetClient()),
        ):
            mock_cfg.onet_username = "user"
            mock_cfg.onet_password = "pass"
            r = client.get("/api/skill-knowledge/occupation/infer?title=software+engineer")

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["inferred_from"] == "software engineer"
        assert body["matched_occupation"]["code"] == "15-1252.00"
        assert body["resume_guidance"]["role_family"] == "Technology & Engineering"


class TestOnetClient:
    @pytest.mark.asyncio
    async def test_full_competency_propagates_summary_404(self):
        from harness.knowledge.onet_client import OnetClient

        client = OnetClient("user", "pass")

        async def fake_get(path, params=None):
            if path.endswith("/summary"):
                request = httpx.Request("GET", "https://example.test")
                response = httpx.Response(404, request=request)
                raise httpx.HTTPStatusError("not found", request=request, response=response)
            return {}

        with patch.object(client, "_get", side_effect=fake_get):
            with pytest.raises(httpx.HTTPStatusError) as exc:
                await client.get_full_competency("99-9999.00")

        assert exc.value.response.status_code == 404

    @pytest.mark.asyncio
    async def test_full_competency_warns_on_optional_detail_failure(self):
        from harness.knowledge.onet_client import OnetClient

        client = OnetClient("user", "pass")

        async def fake_get(path, params=None):
            if path.endswith("/summary"):
                return {"title": "Software Developers", "description": "Develop software."}
            if path.endswith("/details/skills"):
                raise httpx.RequestError("skills unavailable")
            if path.endswith("/details/knowledge"):
                return {"element": []}
            if path.endswith("/details/technology_skills"):
                return {"category": []}
            return {}

        with patch.object(client, "_get", side_effect=fake_get):
            result = await client.get_full_competency("15-1252.00")

        assert result["occupation"]["title"] == "Software Developers"
        assert result["skills"] == []
        assert result["warnings"][0]["section"] == "skills"
