"""Real-data regression test for bullet_injector against the master tex.

WHY: the unit tests stub `company_zh` per-experience, but the live
index.json previously omitted that field, causing some experiences to
silently skip during Tier 2/3 injection (only one matched because its
English transliteration appeared inside its Chinese name).

D11 update: this test now reads the COMMITTED sample index +
.sample.zh.tex master pair, so it runs in fresh-clone CI without the
private gitignored seed. Local maintainer runs may use the private real
master; both paths still expect each experience with an `\\expheader{}`
block to be locatable.

Sample experiences this test exercises: 01-strategy-consulting (Acme
Strategy Group), 02-data-analytics (BlueWave SaaS), 03-product-ops
(Beta Products).
"""
from __future__ import annotations

import json

import pytest

from harness.tier1.bullet_injector import inject_bullets


def _resolve_index_path(repo_root):
    """D11 — prefer private real index.json when present, sample fallback otherwise."""
    real = repo_root / "assets/experience-bank/index.json"
    sample = repo_root / "assets/experience-bank/index.sample.json"
    return real if real.is_file() else sample


def _resolve_master_path(repo_root, lens_dir: str):
    """D11 — prefer private resume.zh.tex when present, sample fallback otherwise."""
    real = repo_root / f"assets/resume-bank/versions/{lens_dir}/resume.zh.tex"
    sample = repo_root / f"assets/resume-bank/versions/{lens_dir}/resume.sample.zh.tex"
    return real if real.is_file() else sample


@pytest.fixture
def real_index(repo_root):
    path = _resolve_index_path(repo_root)
    return json.loads(path.read_text())


@pytest.fixture
def real_master_tex(repo_root):
    path = _resolve_master_path(repo_root, "C_product_ops")
    return path.read_text()


def test_empty_bullets_no_skips(real_index, real_master_tex):
    """Sanity: empty bullets dict produces no skips and unchanged tex."""
    new_tex, skipped = inject_bullets(
        real_master_tex,
        {},
        real_index["experiences"],
    )
    assert new_tex == real_master_tex
    assert skipped == []


def _sample_experience_ids(index_data):
    """Return the IDs present in the index in sorted order. Lets the test
    parametrize against whichever seed (sample or private real) is present."""
    return sorted(e.get("id") for e in index_data.get("experiences", []) if e.get("id"))


@pytest.mark.parametrize(
    "experience_id",
    [
        # Sample tree IDs
        "01-strategy-consulting",
        "02-data-analytics",
        "03-product-ops",
        # Private real tree IDs (kept so maintainer-local runs still cover them)
        "01-kearney",
        "03-desaysv",
        "05-sdic",
    ],
)
def test_real_experience_locatable_in_C_master(
    real_index, real_master_tex, experience_id
):
    """Each experience that has its own \\expheader{} block in the
    C_product_ops master must be locatable by the matcher.

    Skips experiences not present in the active index (e.g. the private-real
    IDs are skipped on a fresh clone, sample IDs are skipped on the
    maintainer's local repo)."""
    present_ids = _sample_experience_ids(real_index)
    if experience_id not in present_ids:
        pytest.skip(f"{experience_id} not present in active index")

    new_tex, skipped = inject_bullets(
        real_master_tex,
        {experience_id: ["test bullet for regression guard"]},
        real_index["experiences"],
    )
    assert experience_id not in skipped, (
        f"experience {experience_id} should be locatable in master tex; "
        f"this likely means company_zh is missing or the matcher regressed"
    )
    # And the master should have actually changed (an injection happened).
    assert new_tex != real_master_tex


def test_ipsos_locatable_in_C_master(real_index, real_master_tex):
    """02-ipsos has its own block too (private real tree only).

    Skipped on fresh clones where the private real index is absent."""
    present_ids = _sample_experience_ids(real_index)
    if "02-ipsos" not in present_ids:
        pytest.skip("02-ipsos only present in private real index")

    _new_tex, skipped = inject_bullets(
        real_master_tex,
        {"02-ipsos": ["test bullet"]},
        real_index["experiences"],
    )
    assert "02-ipsos" not in skipped


def test_mercer_locatable_in_HC_master(real_index, repo_root):
    """04-mercer has no \\expheader block in C_product_ops (it's only in
    the inline '其他实习经历' line), but it does in HC_human_capital_analytics.
    Use the HC master to verify mercer's company_zh wires up correctly.

    Skipped on fresh clones (sample tree has no mercer experience)."""
    present_ids = _sample_experience_ids(real_index)
    if "04-mercer" not in present_ids:
        pytest.skip("04-mercer only present in private real index")

    hc_path = _resolve_master_path(repo_root, "HC_human_capital_analytics")
    if not hc_path.exists():
        pytest.skip("HC master tex not present")
    hc_tex = hc_path.read_text()
    if "美世" not in hc_tex:
        pytest.skip("HC master tex does not contain Mercer block")
    _new_tex, skipped = inject_bullets(
        hc_tex,
        {"04-mercer": ["test bullet"]},
        real_index["experiences"],
    )
    assert "04-mercer" not in skipped
